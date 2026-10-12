#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  QUANT SCANNER BOT · Binance USDT-M Futures · Paper Trading · Telegram       ║
╚══════════════════════════════════════════════════════════════════════════════╝

── requirements.txt ────────────────────────────────────────────────────────────
aiohttp>=3.9
websockets>=12.0
python-telegram-bot>=20.7
numpy>=1.26
orjson>=3.9                               # opcional, recomendado (JSON ~5x más rápido)
uvloop>=0.19; sys_platform != "win32"     # opcional (Linux/macOS)
────────────────────────────────────────────────────────────────────────────────

EJECUCIÓN
    pip install -r requirements.txt
    python bot.py

ARQUITECTURA (todo en un único event loop de asyncio)
    ┌─ !miniTicker@arr ──► Market (precio + cambio 24h de TODOS los USDT-perps)
    │                          └─► PaperBroker.on_price()  (gestión de TP/SL en tiempo real)
    ├─ kline_1m / kline_5m ─► Series (velas cerradas + vela en formación, 250 ms)
    │   (N conexiones)         └─► SignalEngine ─► handle_signal ─► PaperBroker.open()
    ├─ Universe loop         (re-rankea el universo por volumen + top movers cada 5 min)
    ├─ Health loop           (alertas de feeds caídos, time-stop, RTT, reloj del servidor)
    ├─ Daily loop            (reporte 00:00 UTC + top ganadoras/perdedoras + cobertura)
    └─ Telegram              (python-telegram-bot v20+, comandos + cola de notificaciones)

NOTAS DE DISEÑO
  · Order-flow: se usa el desbalance taker-buy / taker-sell de cada vela (campo "V" del
    kline). Es un proxy real del flujo agresor sin necesidad de suscribirse a aggTrade.
  · Detección anticipada: además de evaluar al cierre de vela, se evalúa la vela en
    formación (intravela) cuando volumen y rango ya superan los umbrales.
  · Reconexión automática con backoff + jitter, watchdog de "feed congelado", respaldo de
    rutas WS (/market/... y legacy), reintentos REST con control de peso y 429/418.
  · Persistencia: posiciones abiertas en bot_state.json, trades cerrados en
    bot_trades.jsonl → un reinicio NO pierde posiciones.

VARIABLES DE ENTORNO (todas opcionales; ver clase Config)
    TG_TOKEN, TG_CHAT_ID, UNIVERSE_SIZE, VOL_SPIKE, SCORE_MIN, MAX_POSITIONS,
    INITIAL_BALANCE, DAILY_LOSS_LIMIT_USD, BINANCE_REST_URL, BINANCE_WS_URL, ...

AVISO: es una SIMULACIÓN (paper trading). No envía órdenes reales ni usa claves de API.
       Binance bloquea IPs de EE.UU. (HTTP 451): ejecútalo desde otra región/VPS si aplica.
REQUISITO: Python 3.10 o superior.
SEGURIDAD: el token de Telegram por defecto está en el código porque así se pidió; lo ideal es
           exportar TG_TOKEN como variable de entorno y no compartir el archivo.
"""
from __future__ import annotations

import asyncio
import contextlib
import html
import json
import logging
import logging.handlers
import os
import random
import re
import signal
import sys
import time
from collections import deque
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

import aiohttp
import numpy as np
import websockets
from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, InvalidToken, NetworkError, RetryAfter, TelegramError, TimedOut
from telegram.ext import Application, CommandHandler, ContextTypes, filters

try:  # JSON rápido para el camino caliente (mensajes WS)
    import orjson

    def jloads(data: Any) -> Any:
        return orjson.loads(data)
except ImportError:  # pragma: no cover
    def jloads(data: Any) -> Any:
        return json.loads(data)

log = logging.getLogger("scanner")
UTC = timezone.utc

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════
DEFAULT_TG_TOKEN = "8907110381:AAE8C1eFBlHUm4UpA25wjU0Eb-Va6sgHCy8"
DEFAULT_TG_CHAT_ID = "8542123837"


def _env(name: str, default: Any, cast: Callable = str) -> Any:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        if cast is bool:
            return raw.strip().lower() in ("1", "true", "yes", "on", "si", "sí")
        return cast(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    # ── Telegram ────────────────────────────────────────────────────────────
    tg_token: str = _env("TG_TOKEN", DEFAULT_TG_TOKEN)
    tg_chat_id: str = _env("TG_CHAT_ID", DEFAULT_TG_CHAT_ID)

    # ── Binance (API pública, sin claves) ───────────────────────────────────
    rest_url: str = _env("BINANCE_REST_URL", "https://fapi.binance.com")
    ws_url: str = _env("BINANCE_WS_URL", "wss://fstream.binance.com")
    rest_concurrency: int = 8
    weight_soft_limit: int = 1800          # peso/min a partir del cual se frena (límite real: 2400)

    # ── Universo monitoreado ────────────────────────────────────────────────
    timeframes: Tuple[str, ...] = ("1m", "5m")
    universe_size: int = _env("UNIVERSE_SIZE", 150, int)            # top N por volumen 24h
    universe_extra_movers: int = _env("UNIVERSE_EXTRA_MOVERS", 30, int)   # + top movers fuera del top N
    min_quote_vol_movers: float = _env("MIN_QUOTE_VOL_MOVERS", 3_000_000.0, float)
    universe_refresh_s: int = _env("UNIVERSE_REFRESH_S", 300, int)
    shard_size: int = 80                   # streams por conexión WS
    history: int = 130                     # velas cerradas en memoria por serie
    min_candles: int = 60                  # mínimo para evaluar señales

    # ── Motor de señales ────────────────────────────────────────────────────
    vol_spike: float = _env("VOL_SPIKE", 3.0, float)        # volumen vela / media(20) ≥ 3x
    vol_lookback: int = 20
    atr_period: int = 14
    atr_explosion: float = _env("ATR_EXPLOSION", 1.6, float)  # TR vela / ATR previo
    body_atr_min: float = 0.6                                # cuerpo mínimo en múltiplos de ATR
    donchian_n: int = 20                                     # ruptura de rango de 20 velas
    compression_ratio: float = 0.80                          # ATR(10)/ATR(50) previo ≤ 0.80
    flow_min: float = 0.15                                   # desbalance taker mínimo (±15 %)
    rsi_period: int = 14
    rsi_confirm: float = 55.0        # RSI actual debe confirmar: LONG ≥ 55 · SHORT ≤ 45 (simétrico)
    rsi_prior_ob: float = 70.0       # RSI ANTES de la vela de disparo: LONG ≤ 70 · SHORT ≥ 30 (sin agotamiento previo)
    score_min: float = _env("SCORE_MIN", 60.0, float)
    intrabar: bool = _env("INTRABAR", True, bool)            # evaluar vela en formación
    intrabar_throttle_s: float = 1.0
    ext_lookback: int = 10                                   # velas previas para filtro anti-persecución
    tf_params: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "1m": {"min_quote": 40_000.0, "max_pre_move": 2.5, "max_bar_move": 3.0},
        "5m": {"min_quote": 150_000.0, "max_pre_move": 4.0, "max_bar_move": 5.0},
    })
    max_24h_move_pct: float = _env("MAX_24H_MOVE_PCT", 25.0, float)  # no entrar si ya se movió > X % en 24h
    signal_cooldown_s: int = 1800
    post_close_cooldown_s: int = 900

    # ── Simulación de trading ───────────────────────────────────────────────
    margin_usd: float = _env("MARGIN_USD", 10.0, float)
    leverage: int = _env("LEVERAGE", 10, int)
    tp1_pct: float = 5.0           # movimiento de PRECIO (×lev = ROE)
    tp2_pct: float = 10.0
    tp3_pct: float = 20.0
    tp1_size: float = 0.50
    tp2_size: float = 0.30
    tp3_size: float = 0.20
    sl_pct: float = 3.5
    sl_to_tp1_after_tp2: bool = _env("SL_TO_TP1_AFTER_TP2", False, bool)
    taker_fee: float = _env("TAKER_FEE", 0.0005, float)      # 0.05 %
    maker_fee: float = _env("MAKER_FEE", 0.0002, float)      # 0.02 % (TPs limit)
    slippage_bps: float = _env("SLIPPAGE_BPS", 2.0, float)
    initial_balance: float = _env("INITIAL_BALANCE", 1000.0, float)
    max_positions: int = _env("MAX_POSITIONS", 10, int)
    daily_loss_limit_usd: float = _env("DAILY_LOSS_LIMIT_USD", 100.0, float)  # 0 = desactivado
    max_hold_min: int = _env("MAX_HOLD_MIN", 720, int)       # time-stop; 0 = desactivado

    # ── Reportes / persistencia ─────────────────────────────────────────────
    top_n: int = 10
    top_min_quote_vol: float = _env("TOP_MIN_QUOTE_VOL", 2_000_000.0, float)
    feed_alert_s: int = 60
    state_file: str = _env("STATE_FILE", "bot_state.json")
    trades_file: str = _env("TRADES_FILE", "bot_trades.jsonl")
    log_file: str = _env("LOG_FILE", "scanner.log")


SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}USDT$")
TF_MS = {"1m": 60_000, "5m": 300_000}


def setup_logging(cfg: Config) -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    try:
        fh = logging.handlers.RotatingFileHandler(cfg.log_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError:
        pass
    # httpx registra la URL completa (incluye el TOKEN del bot) → silenciar siempre.
    for noisy in ("httpx", "httpcore", "websockets", "telegram", "aiohttp", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ══════════════════════════════════════════════════════════════════════════════
#  UTILIDADES DE FORMATO
# ══════════════════════════════════════════════════════════════════════════════
def utc_day(ts: Optional[float] = None) -> str:
    return datetime.fromtimestamp(time.time() if ts is None else ts, UTC).strftime("%Y-%m-%d")


def hhmm(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%H:%M")


def fmt_price(p: float) -> str:
    if p >= 1000:
        return f"{p:,.2f}"
    if p >= 100:
        return f"{p:.3f}"
    if p >= 1:
        return f"{p:.4f}"
    if p >= 0.1:
        return f"{p:.5f}"
    if p >= 0.01:
        return f"{p:.6f}"
    return f"{p:.8f}"


def fmt_usd(x: float, plus: bool = True) -> str:
    if round(x, 2) == 0:
        x = 0.0
    sign = "-" if x < 0 else ("+" if plus else "")
    return f"{sign}${abs(x):,.2f}"


def fmt_pct(x: float, nd: int = 2, plus: bool = True) -> str:
    if round(x, nd) == 0:
        x = 0.0
    sign = "-" if x < 0 else ("+" if plus else "")
    return f"{sign}{abs(x):.{nd}f}%"


def fmt_big(x: float) -> str:
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(x) >= div:
            return f"{x / div:.1f}{unit}"
    return f"{x:.0f}"


def fmt_dur(sec: float) -> str:
    sec = int(max(0, sec))
    d, r = divmod(sec, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def split_message(text: str, limit: int = 3900) -> List[str]:
    if len(text) <= limit:
        return [text]
    parts: List[str] = []
    cur = ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit:
            if cur:
                parts.append(cur)
                cur = ""
            while len(line) > limit:
                parts.append(line[:limit])
                line = line[limit:]
        cur = f"{cur}\n{line}" if cur else line
    if cur:
        parts.append(cur)
    return parts


def strip_tags(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text))


# ══════════════════════════════════════════════════════════════════════════════
#  INDICADORES (numpy)
# ══════════════════════════════════════════════════════════════════════════════
def true_range(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    prev_c = np.concatenate(([c[0]], c[:-1]))
    return np.maximum.reduce([h - l, np.abs(h - prev_c), np.abs(l - prev_c)])


def ema(x: np.ndarray, n: int) -> np.ndarray:
    a = 2.0 / (n + 1.0)
    out = np.empty_like(x, dtype=np.float64)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1.0 - a) * out[i - 1]
    return out


def rsi_wilder(c: np.ndarray, n: int = 14) -> Optional[float]:
    d = np.diff(c)
    if len(d) < n + 1:
        return None
    gain = np.where(d > 0, d, 0.0)
    loss = np.where(d < 0, -d, 0.0)
    ag, al = float(gain[:n].mean()), float(loss[:n].mean())
    for i in range(n, len(d)):
        ag = (ag * (n - 1) + gain[i]) / n
        al = (al * (n - 1) + loss[i]) / n
    if al == 0:
        return 100.0 if ag > 0 else 50.0
    return 100.0 - 100.0 / (1.0 + ag / al)


def macd_hist(c: np.ndarray, fast: int = 12, slow: int = 26, sig: int = 9) -> Optional[Tuple[float, float]]:
    if len(c) < slow + sig + 2:
        return None
    macd = ema(c, fast) - ema(c, slow)
    hist = macd - ema(macd, sig)
    return float(hist[-1]), float(hist[-2])


# ══════════════════════════════════════════════════════════════════════════════
#  SERIES DE VELAS
# ══════════════════════════════════════════════════════════════════════════════
NOINIT, STALE, GAP, FORMING, CLOSED = range(5)


class Series:
    """Velas cerradas (deques) + vela en formación para un (símbolo, timeframe)."""
    __slots__ = ("symbol", "tf", "tf_ms", "t", "o", "h", "l", "c", "v", "tb", "cur",
                 "base_vol", "base_atr", "last_eval", "ready", "backfilling", "min_candles")

    def __init__(self, symbol: str, tf: str, maxlen: int, min_candles: int = 60):
        self.symbol, self.tf, self.tf_ms = symbol, tf, TF_MS[tf]
        self.t: Deque[int] = deque(maxlen=maxlen)
        self.o: Deque[float] = deque(maxlen=maxlen)
        self.h: Deque[float] = deque(maxlen=maxlen)
        self.l: Deque[float] = deque(maxlen=maxlen)
        self.c: Deque[float] = deque(maxlen=maxlen)
        self.v: Deque[float] = deque(maxlen=maxlen)
        self.tb: Deque[float] = deque(maxlen=maxlen)    # volumen taker-buy (base)
        self.cur: Optional[Tuple[float, ...]] = None    # (o, h, l, c, v, tb) en formación
        self.base_vol = 0.0
        self.base_atr = 0.0
        self.last_eval = 0.0
        self.ready = False
        self.backfilling = False
        self.min_candles = min_candles

    # -- carga REST ----------------------------------------------------------
    def load(self, rows: List[list], now_ms: float) -> None:
        for dq in (self.t, self.o, self.h, self.l, self.c, self.v, self.tb):
            dq.clear()
        for r in rows:
            if int(r[0]) + self.tf_ms > now_ms:      # vela aún en formación → la aporta el WS
                continue
            self.t.append(int(r[0]))
            self.o.append(float(r[1]))
            self.h.append(float(r[2]))
            self.l.append(float(r[3]))
            self.c.append(float(r[4]))
            self.v.append(float(r[5]))
            self.tb.append(float(r[9]))
        self.cur = None
        self._rebase()
        self.ready = len(self.t) >= self.min_candles

    # -- eventos WS ----------------------------------------------------------
    def on_kline(self, k: dict) -> int:
        if not self.ready:
            return NOINIT
        t = int(k["t"])
        expected = self.t[-1] + self.tf_ms
        if t < expected:
            return STALE
        if t > expected:
            return GAP
        if k["x"]:
            self.t.append(t)
            self.o.append(float(k["o"]))
            self.h.append(float(k["h"]))
            self.l.append(float(k["l"]))
            self.c.append(float(k["c"]))
            self.v.append(float(k["v"]))
            self.tb.append(float(k["V"]))
            self.cur = None
            self._rebase()
            return CLOSED
        self.cur = (float(k["o"]), float(k["h"]), float(k["l"]), float(k["c"]), float(k["v"]), float(k["V"]))
        return FORMING

    def _rebase(self) -> None:
        """Línea base (media de volumen y ATR) usada para el pre-filtro intravela."""
        if len(self.t) < 22:
            self.base_vol = self.base_atr = 0.0
            return
        v = list(self.v)[-20:]
        self.base_vol = sum(v) / len(v)
        h, l, c = list(self.h)[-15:], list(self.l)[-15:], list(self.c)[-15:]
        trs = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]
        self.base_atr = sum(trs) / len(trs)

    def intrabar_precheck(self, spike: float, atr_mult: float) -> bool:
        """Barato: ¿la vela en formación ya supera volumen y rango? (evita evaluar todo cada 250 ms)."""
        cur = self.cur
        if cur is None or self.base_vol <= 0 or self.base_atr <= 0:
            return False
        if cur[4] < spike * self.base_vol:
            return False
        pc = self.c[-1]
        tr = max(cur[1] - cur[2], abs(cur[1] - pc), abs(cur[2] - pc))
        return tr >= atr_mult * self.base_atr

    def arrays(self, include_forming: bool = False) -> Tuple[np.ndarray, ...]:
        o, h, l, c, v, tb = (list(x) for x in (self.o, self.h, self.l, self.c, self.v, self.tb))
        if include_forming and self.cur is not None:
            co, ch, cl, cc, cv, ctb = self.cur
            o.append(co); h.append(ch); l.append(cl); c.append(cc); v.append(cv); tb.append(ctb)
        f = np.float64
        return (np.asarray(o, f), np.asarray(h, f), np.asarray(l, f),
                np.asarray(c, f), np.asarray(v, f), np.asarray(tb, f))


# ══════════════════════════════════════════════════════════════════════════════
#  MOTOR DE SEÑALES
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class Signal:
    symbol: str
    side: str            # LONG | SHORT
    tf: str
    price: float
    score: float
    vol_ratio: float
    tr_ratio: float
    flow: float
    rsi: float
    macd_hist: float
    breakout: bool
    compressed: bool
    htf_ok: bool
    intrabar: bool
    ts: float = field(default_factory=time.time)


class SignalEngine:
    """
    Compuertas duras (todas obligatorias):
      1. Volumen vela ≥ 3× media(20)                  → spike de volumen
      2. TR vela ≥ 1.6× ATR(14) previo y cuerpo ≥ 0.6 ATR → explosión de volatilidad
      3. Cierre fuera del rango Donchian(20)           → ruptura
      4. Desbalance taker ≥ 15 % a favor               → order-flow agresor
      5. RSI(14) previo sin agotamiento (≤70 LONG / ≥30 SHORT), RSI actual confirmando la dirección
         y MACD-hist alineado y creciente
      6. Filtros anti-persecución (movimiento previo / de la vela no excesivo)
    Luego puntúa 0-100 (volumen, ATR, flow, RSI, compresión previa, confirmación 5m/1m)
    y exige score ≥ score_min.
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def evaluate(self, s: Series, other: Optional[Series], include_forming: bool) -> Optional[Signal]:
        cfg = self.cfg
        tp = cfg.tf_params[s.tf]
        o, h, l, c, v, tb = s.arrays(include_forming)
        n = len(c)
        if n < cfg.min_candles:
            return None

        # 1) spike de volumen
        base_vol = float(v[-1 - cfg.vol_lookback:-1].mean())
        if base_vol <= 0 or v[-1] <= 0:
            return None
        vol_ratio = float(v[-1]) / base_vol
        if vol_ratio < cfg.vol_spike:
            return None
        price = float(c[-1])
        if price * float(v[-1]) < tp["min_quote"]:          # descarta ruido ilíquido
            return None

        # 2) explosión de ATR
        tr = true_range(h, l, c)
        atr = float(tr[-1 - cfg.atr_period:-1].mean())
        if atr <= 0:
            return None
        tr_ratio = float(tr[-1]) / atr
        body = price - float(o[-1])
        if tr_ratio < cfg.atr_explosion or abs(body) / atr < cfg.body_atr_min:
            return None
        side = 1 if body > 0 else -1

        # 4) order-flow (taker buy vs sell)
        flow = (2.0 * float(tb[-1]) - float(v[-1])) / float(v[-1])
        if side * flow < cfg.flow_min:
            return None

        # 3) ruptura de rango
        N = cfg.donchian_n
        hi, lo = float(h[-1 - N:-1].max()), float(l[-1 - N:-1].min())
        breakout = price > hi if side == 1 else price < lo
        if not breakout:
            return None

        # 6) anti-persecución
        k = cfg.ext_lookback
        pre_move = side * (float(c[-2]) / float(c[-2 - k]) - 1.0) * 100.0
        bar_move = side * (price / float(o[-1]) - 1.0) * 100.0
        if pre_move > tp["max_pre_move"] or bar_move > tp["max_bar_move"]:
            return None

        # 5) momentum. El RSI de la propia vela de ruptura se infla (>90 en rupturas fuertes), así que
        #    el "no agotado" se mide ANTES de la vela de disparo y el RSI actual solo debe confirmar.
        rsi = rsi_wilder(c, cfg.rsi_period)
        rsi_prev = rsi_wilder(c[:-1], cfg.rsi_period)
        if rsi is None or rsi_prev is None:
            return None
        if side == 1:
            if rsi < cfg.rsi_confirm or rsi_prev > cfg.rsi_prior_ob:
                return None
            room = cfg.rsi_prior_ob - rsi_prev
        else:
            if rsi > 100.0 - cfg.rsi_confirm or rsi_prev < 100.0 - cfg.rsi_prior_ob:
                return None
            room = rsi_prev - (100.0 - cfg.rsi_prior_ob)
        mh = macd_hist(c)
        if mh is None:
            return None
        hist, hist_prev = mh
        if side * hist <= 0 or side * (hist - hist_prev) <= 0:
            return None

        # contexto: compresión previa y confirmación en el otro timeframe
        atr_s, atr_l = float(tr[-11:-1].mean()), float(tr[-51:-1].mean())
        compressed = atr_l > 0 and (atr_s / atr_l) <= cfg.compression_ratio
        htf_ok = self._aligned(other, side)

        score = (10.0 + 15.0 * clamp((vol_ratio - 3.0) / 5.0, 0, 1)      # volumen (10-25)
                 + 20.0 * clamp((tr_ratio - 1.0) / 2.5, 0, 1)            # explosión ATR (0-20)
                 + 15.0                                                   # ruptura (compuerta)
                 + 20.0 * clamp(abs(flow) / 0.5, 0, 1)                    # order-flow (0-20)
                 + 10.0                                                   # MACD alineado (compuerta)
                 + 10.0 * clamp(room / 20.0, 0, 1)                       # recorrido disponible según RSI previo (0-10)
                 + (10.0 if compressed else 0.0)
                 + (10.0 if htf_ok else 0.0))
        score = min(score, 100.0)
        if score < cfg.score_min:
            return None

        return Signal(symbol=s.symbol, side="LONG" if side == 1 else "SHORT", tf=s.tf, price=price,
                      score=score, vol_ratio=vol_ratio, tr_ratio=tr_ratio, flow=flow, rsi=rsi,
                      macd_hist=hist, breakout=breakout, compressed=compressed, htf_ok=htf_ok,
                      intrabar=include_forming and s.cur is not None)

    @staticmethod
    def _aligned(other: Optional[Series], side: int) -> bool:
        if other is None or not other.ready:
            return False
        _, _, _, c, _, _ = other.arrays(True)
        if len(c) < 40:
            return False
        mh, r = macd_hist(c), rsi_wilder(c, 14)
        if mh is None or r is None:
            return False
        return side * mh[0] > 0 and (r > 50 if side == 1 else r < 50)


# ══════════════════════════════════════════════════════════════════════════════
#  MODELOS DE POSICIÓN Y ESTADO PERSISTENTE
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class Position:
    id: int
    symbol: str
    side: str
    tf: str
    score: float
    entry: float
    qty: float                    # cantidad base total
    notional: float
    margin: float
    leverage: int
    sl: float
    tp1: float
    tp2: float
    tp3: float
    remaining: float              # cantidad base restante
    opened_at: float
    fees: float = 0.0
    realized: float = 0.0         # PnL neto realizado (incluye comisión de entrada)
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    sl_moved_to: str = ""         # "" | "BE" | "TP1"
    fills: List[dict] = field(default_factory=list)

    @property
    def d(self) -> int:
        return 1 if self.side == "LONG" else -1

    @property
    def tps_hit(self) -> int:
        return int(self.tp1_hit) + int(self.tp2_hit) + int(self.tp3_hit)


@dataclass
class ClosedTrade:
    id: int
    symbol: str
    side: str
    tf: str
    entry: float
    exit_avg: float
    notional: float
    margin: float
    opened_at: float
    closed_at: float
    pnl: float
    roe_pct: float
    fees: float
    outcome: str                  # TP3 | BE | SL | SL-TP1 | TIME | MANUAL
    tp_hits: int
    fills: List[dict] = field(default_factory=list)


def _from_dict(cls: Any, d: dict) -> Any:
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in d.items() if k in names})


def calc_stats(trades: List[ClosedTrade]) -> dict:
    n = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gp = sum(t.pnl for t in wins)
    gl = -sum(t.pnl for t in losses)
    return {
        "n": n, "wins": len(wins), "losses": len(losses),
        "wr": (len(wins) / n * 100.0) if n else 0.0,
        "pnl": sum(t.pnl for t in trades),
        "avg_win": gp / len(wins) if wins else 0.0,
        "avg_loss": -gl / len(losses) if losses else 0.0,
        "pf": (gp / gl) if gl > 0 else (float("inf") if gp > 0 else 0.0),
        "best": max(trades, key=lambda t: t.pnl) if trades else None,
        "worst": min(trades, key=lambda t: t.pnl) if trades else None,
        "fees": sum(t.fees for t in trades),
    }


class State:
    """Estado del simulador. Posiciones en JSON (atómico) + trades cerrados en JSONL (append)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.positions: Dict[str, Position] = {}
        self.closed: List[ClosedTrade] = []
        self.next_id = 1
        self.paused = False
        self.day = utc_day()
        self.balance = cfg.initial_balance
        self.day_start_balance = cfg.initial_balance
        self.detections: Dict[str, dict] = {}     # "SYM|SIDE" → primera detección del día
        self.signals_today = 0
        self.breaker_day = ""
        self.last_signal_ts = 0.0
        self.dirty = False
        self.started_at = time.time()

    def load(self) -> None:
        cfg = self.cfg
        tpath, spath = Path(cfg.trades_file), Path(cfg.state_file)
        if tpath.exists():
            for line in tpath.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    self.closed.append(_from_dict(ClosedTrade, json.loads(line)))
                except Exception:
                    log.warning("línea corrupta en %s ignorada", cfg.trades_file)
        if spath.exists():
            try:
                d = json.loads(spath.read_text(encoding="utf-8"))
                for sym, pd in d.get("positions", {}).items():
                    self.positions[sym] = _from_dict(Position, pd)
                self.paused = bool(d.get("paused", False))
                self.day = d.get("day", self.day)
                self.day_start_balance = float(d.get("day_start_balance", cfg.initial_balance))
                self.detections = d.get("detections", {})
                self.signals_today = int(d.get("signals_today", 0))
                self.breaker_day = d.get("breaker_day", "")
                self.next_id = int(d.get("next_id", 1))
            except Exception:
                log.exception("no se pudo leer %s; se inicia con estado limpio", cfg.state_file)
        self.balance = (cfg.initial_balance + sum(t.pnl for t in self.closed)
                        + sum(p.realized for p in self.positions.values()))
        if not spath.exists():
            self.day_start_balance = self.balance
        mx = max([t.id for t in self.closed] + [p.id for p in self.positions.values()] + [0])
        self.next_id = max(self.next_id, mx + 1)
        log.info("estado cargado: %d trades cerrados, %d posiciones abiertas, balance %.2f",
                 len(self.closed), len(self.positions), self.balance)

    def save(self) -> None:
        data = {
            "positions": {s: asdict(p) for s, p in self.positions.items()},
            "paused": self.paused, "day": self.day, "day_start_balance": self.day_start_balance,
            "detections": self.detections, "signals_today": self.signals_today,
            "breaker_day": self.breaker_day, "next_id": self.next_id,
        }
        path = Path(self.cfg.state_file)
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, path)
            self.dirty = False
        except OSError:
            log.exception("no se pudo guardar el estado")

    def append_trade(self, t: ClosedTrade) -> None:
        try:
            with open(self.cfg.trades_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(t), ensure_ascii=False) + "\n")
        except OSError:
            log.exception("no se pudo escribir el trade cerrado")


class Market:
    """Última vista del mercado completo (todos los USDT-perps)."""

    def __init__(self) -> None:
        self.valid: set = set()
        self.last: Dict[str, float] = {}
        self.t24: Dict[str, Tuple[float, float, float]] = {}   # sym → (cambio % 24h, quote vol 24h, ts)
        self.lat: Deque[float] = deque(maxlen=300)             # latencia de eventos WS (ms)
        self.time_offset_ms = 0.0                              # reloj Binance − reloj local
        self.rest_rtt_ms = 0.0
        self.total_symbols = 0


# ══════════════════════════════════════════════════════════════════════════════
#  BROKER SIMULADO (TP escalonado + trailing a Breakeven)
# ══════════════════════════════════════════════════════════════════════════════
class PaperBroker:
    def __init__(self, cfg: Config, state: State, notify: Callable[[str], None],
                 on_closed: Optional[Callable[[ClosedTrade], None]] = None):
        self.cfg, self.state, self.notify, self.on_closed = cfg, state, notify, on_closed

    # -- apertura ------------------------------------------------------------
    def margin_used(self) -> float:
        return sum(p.margin for p in self.state.positions.values())

    def can_open(self, symbol: str) -> Tuple[bool, str]:
        st, cfg = self.state, self.cfg
        if symbol in st.positions:
            return False, "ya hay posición abierta"
        if len(st.positions) >= cfg.max_positions:
            return False, f"máximo de {cfg.max_positions} posiciones"
        if st.balance - self.margin_used() < cfg.margin_usd:
            return False, "sin margen libre"
        return True, ""

    def open(self, sig: Signal, ref_price: float) -> Optional[Position]:
        cfg, st = self.cfg, self.state
        ok, why = self.can_open(sig.symbol)
        if not ok:
            log.info("no se abre %s: %s", sig.symbol, why)
            return None
        d = 1 if sig.side == "LONG" else -1
        entry = ref_price * (1.0 + d * cfg.slippage_bps / 1e4)       # slippage en contra
        notional = cfg.margin_usd * cfg.leverage
        qty = notional / entry
        fee = notional * cfg.taker_fee
        p = Position(
            id=st.next_id, symbol=sig.symbol, side=sig.side, tf=sig.tf, score=sig.score,
            entry=entry, qty=qty, notional=notional, margin=cfg.margin_usd, leverage=cfg.leverage,
            sl=entry * (1 - d * cfg.sl_pct / 100.0),
            tp1=entry * (1 + d * cfg.tp1_pct / 100.0),
            tp2=entry * (1 + d * cfg.tp2_pct / 100.0),
            tp3=entry * (1 + d * cfg.tp3_pct / 100.0),
            remaining=qty, opened_at=time.time(), fees=fee, realized=-fee,
        )
        st.next_id += 1
        st.balance -= fee
        st.positions[sig.symbol] = p
        st.dirty = True
        log.info("ABRE %s %s @ %s (score %.0f)", p.side, p.symbol, fmt_price(entry), sig.score)
        self.notify(self._msg_open(p, sig))
        return p

    # -- gestión por tick ----------------------------------------------------
    def on_price(self, symbol: str, price: float, ts: float) -> None:
        p = self.state.positions.get(symbol)
        if p is None or price <= 0:
            return
        d = p.d
        eps = 1e-12      # tolerancia relativa: 100*1.1 = 110.00000000000001 en coma flotante
        # 1) Stop (se evalúa primero: criterio conservador)
        if d * (price - p.sl) <= p.sl * eps:
            fill = price if d * (price - p.sl) < -p.sl * eps else p.sl    # si hubo gap, se llena al peor precio
            label = "SL" if not p.tp1_hit else ("BE" if p.sl_moved_to == "BE" else "SL-TP1")
            self._exit(p, p.remaining, fill, label, taker=True)
            self._finalize(p, label)
            return
        # 2) Take profits en orden (un tick puede saltar varios niveles)
        if not p.tp1_hit and d * (price - p.tp1) >= -p.tp1 * eps:
            self._take(p, 1)
        if p.tp1_hit and not p.tp2_hit and d * (price - p.tp2) >= -p.tp2 * eps:
            self._take(p, 2)
        if p.tp2_hit and not p.tp3_hit and d * (price - p.tp3) >= -p.tp3 * eps:
            self._take(p, 3)

    def force_close(self, symbol: str, price: float, label: str = "MANUAL") -> None:
        p = self.state.positions.get(symbol)
        if p is None:
            return
        self._exit(p, p.remaining, price, label, taker=True)
        self._finalize(p, label)

    # -- internos ------------------------------------------------------------
    def _exit(self, p: Position, qty: float, price: float, label: str, taker: bool) -> Tuple[float, float]:
        cfg = self.cfg
        qty = min(qty, p.remaining)
        px = price * (1.0 - p.d * cfg.slippage_bps / 1e4) if taker else price
        gross = p.d * (px - p.entry) * qty
        fee = px * qty * (cfg.taker_fee if taker else cfg.maker_fee)
        net = gross - fee
        p.realized += net
        p.fees += fee
        p.remaining = max(0.0, p.remaining - qty)
        if p.remaining < p.qty * 1e-9:
            p.remaining = 0.0
        self.state.balance += net
        p.fills.append({"label": label, "price": px, "qty": qty, "pnl": net})
        self.state.dirty = True
        return net, px

    def _take(self, p: Position, n: int) -> None:
        cfg = self.cfg
        if n == 1:
            qty, price, p.tp1_hit = p.qty * cfg.tp1_size, p.tp1, True
        elif n == 2:
            qty, price, p.tp2_hit = p.qty * cfg.tp2_size, p.tp2, True
        else:
            qty, price, p.tp3_hit = p.remaining, p.tp3, True
        net, px = self._exit(p, qty, price, f"TP{n}", taker=False)
        pct_closed = qty / p.qty * 100.0
        if n == 1:
            p.sl, p.sl_moved_to = p.entry, "BE"                      # SL → precio exacto de entrada
            self.notify(self._msg_tp(p, 1, px, net, pct_closed))
        elif n == 2:
            if cfg.sl_to_tp1_after_tp2:
                p.sl, p.sl_moved_to = p.tp1, "TP1"
            self.notify(self._msg_tp(p, 2, px, net, pct_closed))
        else:
            self.notify(self._msg_tp(p, 3, px, net, pct_closed))
            self._finalize(p, "TP3")

    def _finalize(self, p: Position, outcome: str) -> None:
        st = self.state
        filled = sum(f["qty"] for f in p.fills) or 1.0
        exit_avg = sum(f["price"] * f["qty"] for f in p.fills) / filled
        t = ClosedTrade(
            id=p.id, symbol=p.symbol, side=p.side, tf=p.tf, entry=p.entry, exit_avg=exit_avg,
            notional=p.notional, margin=p.margin, opened_at=p.opened_at, closed_at=time.time(),
            pnl=p.realized, roe_pct=p.realized / p.margin * 100.0, fees=p.fees,
            outcome=outcome, tp_hits=p.tps_hit, fills=p.fills,
        )
        st.positions.pop(p.symbol, None)
        st.closed.append(t)
        st.append_trade(t)
        st.dirty = True
        log.info("CIERRA %s %s %s pnl=%.2f (%s)", p.side, p.symbol, outcome, t.pnl, fmt_pct(t.roe_pct, 1))
        if outcome != "TP3":
            self.notify(self._msg_close(t))
        if self.on_closed:
            self.on_closed(t)

    # -- mensajes ------------------------------------------------------------
    def _msg_open(self, p: Position, sig: Signal) -> str:
        cfg, lev = self.cfg, p.leverage
        head = "🟢 LONG" if p.side == "LONG" else "🔴 SHORT"
        how = "⚡ intravela" if sig.intrabar else "cierre de vela"
        extras = []
        if sig.compressed:
            extras.append("compresión previa")
        if sig.htf_ok:
            extras.append("confirma otro TF")
        return "\n".join([
            f"🚀 <b>NUEVA POSICIÓN · {head}</b>",
            f"<b>{p.symbol}</b> · {p.tf} · score {sig.score:.0f}/100 · {how}",
            f"Entrada: <code>{fmt_price(p.entry)}</code>",
            "",
            f"🎯 TP1: <code>{fmt_price(p.tp1)}</code> (+{cfg.tp1_pct:g}% · +{cfg.tp1_pct * lev:g}% ROE) · cierra {cfg.tp1_size * 100:.0f}% y SL→BE",
            f"🎯 TP2: <code>{fmt_price(p.tp2)}</code> (+{cfg.tp2_pct:g}% · +{cfg.tp2_pct * lev:g}% ROE) · cierra {cfg.tp2_size * 100:.0f}%",
            f"🎯 TP3: <code>{fmt_price(p.tp3)}</code> (+{cfg.tp3_pct:g}% · +{cfg.tp3_pct * lev:g}% ROE) · cierra {cfg.tp3_size * 100:.0f}%",
            f"🛑 SL: <code>{fmt_price(p.sl)}</code> (-{cfg.sl_pct:g}% · -{cfg.sl_pct * lev:g}% ROE)",
            "",
            f"💵 Margen ${p.margin:g} · {lev}x · Nocional ${p.notional:g}",
            f"📊 Vol ×{sig.vol_ratio:.1f} · ATR ×{sig.tr_ratio:.1f} · Flow {sig.flow * 100:+.0f}% · RSI {sig.rsi:.0f}"
            + (f"\n✨ {' · '.join(extras)}" if extras else ""),
        ])

    def _msg_tp(self, p: Position, n: int, px: float, net: float, pct_closed: float) -> str:
        roe = net / p.margin * 100.0
        base = (f"<b>{p.symbol}</b> {p.side} · TP{n} @ <code>{fmt_price(px)}</code>\n"
                f"Cerrado {pct_closed:.0f}% → {fmt_usd(net)} ({fmt_pct(roe, 1)} ROE s/margen)")
        if n == 1:
            return ("🛡️ <b>TP1 Alcanzado. Stop Loss ajustado a Breakeven</b>\n" + base +
                    f"\nSL ahora = entrada <code>{fmt_price(p.entry)}</code> · restante {p.remaining / p.qty * 100:.0f}% libre de riesgo")
        if n == 2:
            extra = (f"\nSL movido a TP1 <code>{fmt_price(p.tp1)}</code>" if p.sl_moved_to == "TP1"
                     else f"\nSL se mantiene en BE <code>{fmt_price(p.entry)}</code>")
            return (f"🎯 <b>TP2 ejecutado</b>\n" + base + extra +
                    f"\nQueda {p.remaining / p.qty * 100:.0f}% buscando TP3")
        return (f"🏆 <b>TP3 ejecutado · trade completo</b>\n" + base +
                f"\n💰 PnL total del trade: <b>{fmt_usd(p.realized)}</b> ({fmt_pct(p.realized / p.margin * 100, 1)} ROE)")

    def _msg_close(self, t: ClosedTrade) -> str:
        brk = " · ".join(f"{f['label']} {fmt_usd(f['pnl'])}" for f in t.fills)
        if t.outcome == "SL":
            head = "🛑 <b>STOP LOSS ejecutado</b>"
        elif t.outcome == "BE":
            head = "⚖️ <b>Breakeven: stop en entrada ejecutado</b> (el trade ya había asegurado TP1)"
        elif t.outcome == "SL-TP1":
            head = "🛑 <b>Stop (trailing en TP1) ejecutado</b>"
        elif t.outcome == "TIME":
            head = "⏱️ <b>Cierre por tiempo máximo</b>"
        else:
            head = f"🔔 <b>Posición cerrada ({t.outcome})</b>"
        icon = "✅" if t.pnl > 0 else "❌"
        return (f"{head}\n<b>{t.symbol}</b> {t.side}\n"
                f"Entrada <code>{fmt_price(t.entry)}</code> → salida media <code>{fmt_price(t.exit_avg)}</code>\n"
                f"{icon} PnL del trade: <b>{fmt_usd(t.pnl)}</b> ({fmt_pct(t.roe_pct, 1)} ROE) · TPs: {t.tp_hits}/3\n"
                f"<i>{brk}</i>")


# ══════════════════════════════════════════════════════════════════════════════
#  CAPA DE RED: REST y WebSocket resilientes
# ══════════════════════════════════════════════════════════════════════════════
class GeoBlockedError(RuntimeError):
    pass


class RestClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.session: Optional[aiohttp.ClientSession] = None
        self.sem: Optional[asyncio.Semaphore] = None
        self.used_weight = 0
        self.ban_until = 0.0

    async def start(self) -> None:
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=20),
            connector=aiohttp.TCPConnector(limit=30, ttl_dns_cache=300),
            headers={"User-Agent": "quant-scanner/1.0"},
        )
        self.sem = asyncio.Semaphore(self.cfg.rest_concurrency)

    async def close(self) -> None:
        if self.session:
            await self.session.close()

    async def get(self, path: str, params: Optional[dict] = None, retries: int = 6) -> Any:
        assert self.session and self.sem
        url = self.cfg.rest_url + path
        last_err: Optional[Exception] = None
        for attempt in range(retries):
            wait = self.ban_until - time.time()
            if wait > 0:
                await asyncio.sleep(wait)
            if self.used_weight >= self.cfg.weight_soft_limit:      # frena antes del 429
                await asyncio.sleep(61.0 - (time.time() % 60.0))
                self.used_weight = 0
            try:
                async with self.sem, self.session.get(url, params=params) as r:
                    w = r.headers.get("X-MBX-USED-WEIGHT-1M")
                    if w and w.isdigit():
                        self.used_weight = int(w)
                    if r.status == 200:
                        return jloads(await r.read())
                    if r.status in (418, 429):
                        ra = float(r.headers.get("Retry-After", "5"))
                        self.ban_until = time.time() + ra
                        log.warning("REST %s → HTTP %s, pausa %.0fs", path, r.status, ra)
                        continue
                    if r.status in (403, 451):
                        raise GeoBlockedError(
                            f"HTTP {r.status} de Binance: tu IP/región está bloqueada. "
                            f"Ejecuta el bot desde un servidor fuera de EE.UU. o cambia BINANCE_REST_URL.")
                    if r.status >= 500:
                        last_err = RuntimeError(f"HTTP {r.status}")
                    else:
                        body = (await r.text())[:200]
                        raise RuntimeError(f"HTTP {r.status} en {path}: {body}")
            except GeoBlockedError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_err = e
            await asyncio.sleep(min(0.5 * 2 ** attempt, 10.0) * (0.7 + 0.6 * random.random()))
        raise RuntimeError(f"REST {path}: reintentos agotados ({last_err})")


class WSStream:
    """Conexión WS con reconexión instantánea, backoff + jitter, watchdog y rutas alternativas."""

    def __init__(self, name: str, urls: List[str], on_message: Callable[[Any], None], stale_after: float = 30.0):
        self.name, self.urls, self.on_message, self.stale_after = name, urls, on_message, stale_after
        self.connected = False
        self.since = time.time()
        self.last_msg = 0.0
        self.msgs = 0
        self.reconnects = 0
        self._url_idx = 0
        self._fail_streak = 0
        self._last_err_log = 0.0

    @property
    def url(self) -> str:
        return self.urls[self._url_idx % len(self.urls)]

    def _set_connected(self, v: bool) -> None:
        if self.connected != v:
            self.connected = v
            self.since = time.time()

    async def _watchdog(self, ws: Any) -> None:
        while True:
            await asyncio.sleep(5)
            if time.time() - self.last_msg > self.stale_after:
                log.warning("[%s] sin datos %.0fs → fuerza reconexión", self.name, self.stale_after)
                with contextlib.suppress(Exception):
                    await ws.close()
                return

    async def run(self) -> None:
        backoff = 0.2
        while True:
            t0 = time.time()
            try:
                async with websockets.connect(self.url, ping_interval=20, ping_timeout=20, close_timeout=3,
                                              max_size=None, max_queue=4096, compression=None) as ws:
                    self._set_connected(True)
                    self.last_msg = time.time()
                    log.info("[%s] conectado: %s", self.name, self.url.split("?")[0])
                    wd = asyncio.create_task(self._watchdog(ws))
                    try:
                        async for raw in ws:
                            self.last_msg = time.time()
                            self.msgs += 1
                            try:
                                self.on_message(raw)
                            except Exception:
                                if time.time() - self._last_err_log > 10:
                                    self._last_err_log = time.time()
                                    log.exception("[%s] error procesando mensaje", self.name)
                    finally:
                        wd.cancel()
                        with contextlib.suppress(asyncio.CancelledError, Exception):
                            await wd
            except asyncio.CancelledError:
                self._set_connected(False)
                raise
            except Exception as e:
                log.warning("[%s] desconectado: %s: %s", self.name, type(e).__name__, str(e)[:160])
            self._set_connected(False)
            self.reconnects += 1
            if time.time() - t0 > 30:
                backoff, self._fail_streak = 0.2, 0
            else:
                self._fail_streak += 1
                backoff = min(backoff * 2, 15.0)
            if self._fail_streak >= 3 and len(self.urls) > 1:
                self._url_idx += 1
                self._fail_streak = 0
                log.warning("[%s] cambiando a ruta alternativa: %s", self.name, self.url.split("?")[0])
            await asyncio.sleep(backoff * (0.7 + 0.6 * random.random()))


class KlineFeed:
    """Gestiona todas las series de velas y las conexiones WS (shards) del universo."""

    def __init__(self, app: "ScannerApp"):
        self.app, self.cfg = app, app.cfg
        self.series: Dict[Tuple[str, str], Series] = {}
        self.symbols: set = set()
        self.shards: List[WSStream] = []
        self._tasks: List[asyncio.Task] = []
        self._bg: set = set()

    def get(self, sym: str, tf: str) -> Optional[Series]:
        return self.series.get((sym, tf))

    # -- universo ------------------------------------------------------------
    async def set_symbols(self, wanted: List[str]) -> None:
        wanted_set = set(wanted)
        added = [s for s in wanted if s not in self.symbols]
        removed = [s for s in self.symbols if s not in wanted_set]
        if not added and not removed:
            return
        if added:
            await self._bootstrap(added)
        for s in removed:
            for tf in self.cfg.timeframes:
                self.series.pop((s, tf), None)
        self.symbols = wanted_set
        log.info("universo: +%d / -%d → %d pares × %d TF", len(added), len(removed),
                 len(self.symbols), len(self.cfg.timeframes))
        await self._restart_shards()

    async def _bootstrap(self, symbols: List[str]) -> None:
        async def one(sym: str, tf: str) -> None:
            s = Series(sym, tf, self.cfg.history, self.cfg.min_candles)
            self.series[(sym, tf)] = s
            await self._load(s)
        await asyncio.gather(*(one(sym, tf) for sym in symbols for tf in self.cfg.timeframes),
                             return_exceptions=True)

    async def _load(self, s: Series) -> None:
        try:
            rows = await self.app.rest.get("/fapi/v1/klines", {"symbol": s.symbol, "interval": s.tf,
                                                               "limit": self.cfg.history + 1})
            s.load(rows, self.app.server_now_ms())
        except GeoBlockedError:
            raise
        except Exception as e:
            log.warning("bootstrap %s %s falló: %s", s.symbol, s.tf, e)

    async def retry_unready(self, limit: int = 40) -> None:
        pend = [s for s in self.series.values() if not s.ready and not s.backfilling][:limit]
        if pend:
            await asyncio.gather(*(self._load(s) for s in pend), return_exceptions=True)

    def _schedule_backfill(self, s: Series) -> None:
        if s.backfilling:
            return
        s.backfilling = True

        async def job() -> None:
            try:
                log.info("backfill %s %s (hueco de velas detectado)", s.symbol, s.tf)
                await self._load(s)
            finally:
                s.backfilling = False
        t = asyncio.get_running_loop().create_task(job())
        self._bg.add(t)
        t.add_done_callback(self._bg.discard)

    # -- conexiones ----------------------------------------------------------
    async def _restart_shards(self) -> None:
        cfg = self.cfg
        streams = [f"{sym.lower()}@kline_{tf}" for sym in sorted(self.symbols) for tf in cfg.timeframes]
        chunks = [streams[i:i + cfg.shard_size] for i in range(0, len(streams), cfg.shard_size)]
        new_shards: List[WSStream] = []
        for idx, ch in enumerate(chunks):
            q = "/".join(ch)
            urls = [f"{cfg.ws_url}/market/stream?streams={q}", f"{cfg.ws_url}/stream?streams={q}"]
            new_shards.append(WSStream(f"kline-{idx}", urls, self.on_message, stale_after=30.0))
        old_tasks = self._tasks
        self.shards = new_shards
        self._tasks = [asyncio.create_task(w.run()) for w in new_shards]      # primero las nuevas…
        if old_tasks:
            await asyncio.sleep(2.0)                                           # …solapamiento sin huecos
            for t in old_tasks:
                t.cancel()
            await asyncio.gather(*old_tasks, return_exceptions=True)

    async def stop(self) -> None:
        for t in self._tasks + list(self._bg):
            t.cancel()
        await asyncio.gather(*self._tasks, *self._bg, return_exceptions=True)

    # -- camino caliente -----------------------------------------------------
    def on_message(self, raw: Any) -> None:
        msg = jloads(raw)
        d = msg.get("data", msg) if isinstance(msg, dict) else None
        if not d or d.get("e") != "kline":
            return
        k = d["k"]
        sym, tf = d["s"], k["i"]
        s = self.series.get((sym, tf))
        if s is None:
            return
        status = s.on_kline(k)
        self.app.on_price(sym, float(k["c"]))
        if status == CLOSED:
            self.app.on_candle(s, closed=True)
        elif status == FORMING:
            if self.cfg.intrabar:
                now = time.monotonic()
                if now - s.last_eval >= self.cfg.intrabar_throttle_s and \
                        s.intrabar_precheck(self.cfg.vol_spike, self.cfg.atr_explosion):
                    s.last_eval = now
                    self.app.on_candle(s, closed=False)
        elif status == GAP:
            self._schedule_backfill(s)


# ══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════
class Notifier:
    """Cola de envío con reintentos, respeto de rate-limits de Telegram y troceo de mensajes."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.q: asyncio.Queue = asyncio.Queue(maxsize=2000)
        self.bot: Any = None
        self.ready = asyncio.Event()
        raw = str(cfg.tg_chat_id).strip()
        self.chat_id: Any = int(raw) if raw.lstrip("-").isdigit() else raw

    def bind(self, bot: Any) -> None:
        self.bot = bot
        self.ready.set()

    def send(self, text: str) -> None:
        try:
            self.q.put_nowait(text)
        except asyncio.QueueFull:
            with contextlib.suppress(asyncio.QueueEmpty):
                self.q.get_nowait()
                self.q.task_done()
            with contextlib.suppress(asyncio.QueueFull):
                self.q.put_nowait(text)

    async def run(self) -> None:
        await self.ready.wait()
        while True:
            text = await self.q.get()
            try:
                for chunk in split_message(text):
                    await self._deliver(chunk)
                    await asyncio.sleep(0.04)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("fallo enviando mensaje a Telegram")
            finally:
                self.q.task_done()

    async def _deliver(self, chunk: str) -> None:
        for attempt in range(8):
            try:
                await self.bot.send_message(chat_id=self.chat_id, text=chunk, parse_mode=ParseMode.HTML)
                return
            except RetryAfter as e:
                ra = e.retry_after
                ra = ra.total_seconds() if hasattr(ra, "total_seconds") else float(ra)
                log.warning("Telegram rate-limit: espera %.0fs", ra)
                await asyncio.sleep(ra + 1.0)
            except BadRequest as e:
                log.warning("Telegram rechazó el HTML (%s); reenviando como texto plano", e)
                with contextlib.suppress(TelegramError):
                    await self.bot.send_message(chat_id=self.chat_id, text=strip_tags(chunk))
                return
            except (TimedOut, NetworkError) as e:
                log.warning("Telegram red/timeout (%s); reintento %d", e, attempt + 1)
                await asyncio.sleep(min(2 ** attempt, 30))
            except TelegramError as e:
                log.error("Telegram error no recuperable: %s", e)
                return


class TelegramFront:
    COMMANDS = [
        ("start", "Menú de bienvenida"), ("status", "Estado del escáner y posiciones"),
        ("balance", "Balance y PnL no realizado"), ("trades", "Últimos 5 trades cerrados"),
        ("summary", "Rendimiento global"), ("top", "Top 10 ganadoras y perdedoras"),
        ("report", "Reporte del día en curso"), ("pause", "Pausar nuevas entradas"),
        ("resume", "Reanudar entradas"), ("help", "Ayuda"),
    ]

    def __init__(self, app: "ScannerApp"):
        self.app = app
        self.application: Optional[Application] = None

    async def start(self) -> None:
        cfg = self.app.cfg
        self.application = (Application.builder().token(cfg.tg_token)
                            .connect_timeout(10).read_timeout(20).write_timeout(20).pool_timeout(10).build())
        raw = str(cfg.tg_chat_id).strip()
        chat_filter = (filters.Chat(chat_id=int(raw)) if raw.lstrip("-").isdigit()
                       else filters.Chat(username=raw.lstrip("@")))
        handlers = {
            "start": self.cmd_start, "help": self.cmd_help, "status": self.cmd_status,
            "balance": self.cmd_balance, "trades": self.cmd_trades, "summary": self.cmd_summary,
            "top": self.cmd_top, "report": self.cmd_report, "pause": self.cmd_pause, "resume": self.cmd_resume,
        }
        for name, fn in handlers.items():
            self.application.add_handler(CommandHandler(name, fn, filters=chat_filter))
        self.application.add_error_handler(self.on_error)
        while True:
            try:
                await self.application.initialize()
                break
            except InvalidToken:
                raise SystemExit("TG_TOKEN inválido: revisa el token del bot en @BotFather.")
            except Exception as e:
                log.warning("Telegram initialize falló (%s); reintento en 5s", e)
                await asyncio.sleep(5)
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True, bootstrap_retries=-1)
        with contextlib.suppress(Exception):
            await self.application.bot.set_my_commands([BotCommand(c, d) for c, d in self.COMMANDS])
        self.app.notifier.bind(self.application.bot)
        log.info("Telegram listo (polling)")

    async def stop(self) -> None:
        a = self.application
        if a is None:
            return
        with contextlib.suppress(Exception):
            if a.updater and a.updater.running:
                await a.updater.stop()
            if a.running:
                await a.stop()
            await a.shutdown()

    async def on_error(self, update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        err = ctx.error
        if isinstance(err, (NetworkError, TimedOut)):
            log.warning("Telegram polling: %s", err)
        else:
            log.error("Error en handler de Telegram: %s", err, exc_info=err)

    async def _reply(self, update: Update, text: str) -> None:
        msg = update.effective_message
        if msg is None:
            return
        for chunk in split_message(text):
            try:
                await msg.reply_text(chunk, parse_mode=ParseMode.HTML)
            except BadRequest:
                await msg.reply_text(strip_tags(chunk))

    async def cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await self._reply(update, self.app.render_welcome())

    async def cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await self._reply(update, self.app.render_help())

    async def cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await self._reply(update, self.app.render_status())

    async def cmd_balance(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await self._reply(update, self.app.render_balance())

    async def cmd_trades(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await self._reply(update, self.app.render_trades())

    async def cmd_summary(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await self._reply(update, self.app.render_summary())

    async def cmd_top(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await self._reply(update, self.app.render_top())

    async def cmd_report(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        a, b = self.app.render_daily(self.app.state.day, partial=True)
        await self._reply(update, a)
        await self._reply(update, b)

    async def cmd_pause(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        self.app.state.paused = True
        self.app.state.dirty = True
        await self._reply(update, "⏸️ <b>Nuevas entradas PAUSADAS.</b> Las posiciones abiertas siguen gestionándose.\n/resume para reanudar.")

    async def cmd_resume(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        self.app.state.paused = False
        self.app.state.dirty = True
        await self._reply(update, "▶️ <b>Entradas REANUDADAS.</b>")


# ══════════════════════════════════════════════════════════════════════════════
#  APLICACIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
class ScannerApp:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.state = State(cfg)
        self.market = Market()
        self.notifier = Notifier(cfg)
        self.broker = PaperBroker(cfg, self.state, self.notifier.send, self._on_trade_closed)
        self.engine = SignalEngine(cfg)
        self.rest = RestClient(cfg)
        self.feed = KlineFeed(self)
        self.telegram = TelegramFront(self)
        self.ticker_stream = WSStream(
            "ticker", [f"{cfg.ws_url}/market/ws/!miniTicker@arr", f"{cfg.ws_url}/ws/!miniTicker@arr"],
            self.on_ticker, stale_after=15.0)
        self.cooldowns: Dict[str, float] = {}
        self.msg_rate = 0.0
        self.stop: asyncio.Event = asyncio.Event()
        self.universe_ready: asyncio.Event = asyncio.Event()
        self._down_alerted: set = set()
        self._geo_alerted = False
        self._prev_msgs = 0

    # ── reloj ────────────────────────────────────────────────────────────────
    def server_now_ms(self) -> float:
        return time.time() * 1000.0 + self.market.time_offset_ms

    async def sync_time(self) -> None:
        t0 = time.time()
        r = await self.rest.get("/fapi/v1/time")
        t1 = time.time()
        self.market.rest_rtt_ms = (t1 - t0) * 1000.0
        self.market.time_offset_ms = float(r["serverTime"]) - (t0 + t1) / 2.0 * 1000.0

    # ── callbacks de datos ───────────────────────────────────────────────────
    def on_price(self, sym: str, price: float) -> None:
        self.market.last[sym] = price
        if sym in self.state.positions:
            self.broker.on_price(sym, price, time.time())

    def on_ticker(self, raw: Any) -> None:
        arr = jloads(raw)
        if isinstance(arr, dict):
            arr = arr.get("data", [])
        if not arr:
            return
        m, now = self.market, time.time()
        ev = arr[0].get("E")
        if ev:
            m.lat.append(max(0.0, now * 1000.0 + m.time_offset_ms - float(ev)))
        valid = m.valid
        for t in arr:
            sym = t.get("s")
            if sym not in valid:
                continue
            c, o = float(t["c"]), float(t["o"])
            m.t24[sym] = (((c / o) - 1.0) * 100.0 if o > 0 else 0.0, float(t["q"]), now)
            self.on_price(sym, c)

    def on_candle(self, s: Series, closed: bool) -> None:
        sym, now = s.symbol, time.time()
        if sym in self.state.positions or self.cooldowns.get(sym, 0.0) > now:
            return
        other = self.feed.get(sym, "5m" if s.tf == "1m" else "1m")
        sig = self.engine.evaluate(s, other, include_forming=not closed)
        if sig:
            self.handle_signal(sig)

    # ── señal → filtros de portafolio → apertura ─────────────────────────────
    def handle_signal(self, sig: Signal) -> None:
        cfg, st, now = self.cfg, self.state, time.time()
        sym = sig.symbol
        self.cooldowns[sym] = now + cfg.signal_cooldown_s
        st.signals_today += 1
        st.last_signal_ts = now
        reason = self._reject_reason(sig)
        key = f"{sym}|{sig.side}"
        det = st.detections.get(key)
        status = "opened" if not reason else f"skip:{reason}"
        if det is None:
            st.detections[key] = {"symbol": sym, "side": sig.side, "price": sig.price, "ts": now,
                                  "tf": sig.tf, "score": round(sig.score, 1), "status": status}
        elif status == "opened" and det["status"] != "opened":
            det["status"] = "opened"
        st.dirty = True
        log.info("SEÑAL %s %s %s score=%.0f vol×%.1f atr×%.1f flow=%+.2f rsi=%.0f%s",
                 sig.side, sym, sig.tf, sig.score, sig.vol_ratio, sig.tr_ratio, sig.flow, sig.rsi,
                 f" → descartada ({reason})" if reason else "")
        if reason:
            return
        self.broker.open(sig, sig.price)

    def _reject_reason(self, sig: Signal) -> str:
        st, cfg = self.state, self.cfg
        if st.paused:
            return "bot en pausa"
        if st.breaker_day == st.day:
            return "límite de pérdida diaria"
        t24 = self.market.t24.get(sig.symbol)
        if t24 and abs(t24[0]) > cfg.max_24h_move_pct:
            return f"ya se movió {t24[0]:+.0f}% en 24h"
        ok, why = self.broker.can_open(sig.symbol)
        return "" if ok else why

    def _on_trade_closed(self, t: ClosedTrade) -> None:
        cfg, st = self.cfg, self.state
        self.cooldowns[t.symbol] = time.time() + cfg.post_close_cooldown_s
        if cfg.daily_loss_limit_usd > 0 and st.breaker_day != st.day:
            day_pnl = st.balance - st.day_start_balance
            if day_pnl <= -cfg.daily_loss_limit_usd:
                st.breaker_day = st.day
                self.notifier.send(
                    f"⛔ <b>Límite de pérdida diaria alcanzado</b> ({fmt_usd(day_pnl)}).\n"
                    f"No se abrirán nuevas posiciones hasta las 00:00 UTC. Las abiertas siguen gestionándose.")

    # ── tareas de fondo ──────────────────────────────────────────────────────
    async def supervise(self, name: str, fn: Callable[[], Any], delay: float = 3.0) -> None:
        while not self.stop.is_set():
            try:
                await fn()
                return
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("[%s] tarea caída; se reinicia en %.0fs", name, delay)
                await asyncio.sleep(delay)

    async def fetch_universe(self) -> List[str]:
        cfg = self.cfg
        info, tick = await asyncio.gather(self.rest.get("/fapi/v1/exchangeInfo"),
                                          self.rest.get("/fapi/v1/ticker/24hr"))
        valid = {s["symbol"] for s in info.get("symbols", [])
                 if s.get("status") == "TRADING" and s.get("contractType") == "PERPETUAL"
                 and s.get("quoteAsset") == "USDT" and SYMBOL_RE.match(s.get("symbol", ""))}
        rows: List[Tuple[str, float, float, float]] = []
        for t in tick:
            sym = t.get("symbol")
            if sym in valid:
                try:
                    rows.append((sym, float(t["quoteVolume"]), float(t["priceChangePercent"]), float(t["lastPrice"])))
                except (KeyError, ValueError):
                    continue
        if not rows:
            raise RuntimeError("universo vacío (exchangeInfo/ticker sin datos)")
        m, now = self.market, time.time()
        m.valid, m.total_symbols = valid, len(valid)
        for sym in list(m.t24):
            if sym not in valid:
                m.t24.pop(sym, None)
        for sym, q, chg, last in rows:
            m.t24[sym] = (chg, q, now)
            m.last.setdefault(sym, last)
        by_vol = sorted(rows, key=lambda r: -r[1])
        base = [r[0] for r in by_vol[:cfg.universe_size]]
        base_set = set(base)
        movers = sorted((r for r in rows if r[0] not in base_set and r[1] >= cfg.min_quote_vol_movers),
                        key=lambda r: -abs(r[2]))[:cfg.universe_extra_movers]
        wanted: List[str] = []
        for sym in base + [r[0] for r in movers] + list(self.state.positions):
            if sym not in wanted and sym in valid:
                wanted.append(sym)
        self.universe_ready.set()
        return wanted

    async def universe_loop(self) -> None:
        while True:
            delay = self.cfg.universe_refresh_s
            try:
                wanted = await self.fetch_universe()
                await self.feed.set_symbols(wanted)
                await self.feed.retry_unready()
            except GeoBlockedError as e:
                log.error("%s", e)
                if not self._geo_alerted:
                    self._geo_alerted = True
                    self.notifier.send(f"🚫 <b>Binance bloqueó la conexión</b>\n{html.escape(str(e))}")
                delay = 60
            except Exception as e:
                log.warning("refresco de universo falló: %s", e)
                delay = 10 if not self.universe_ready.is_set() else 30
            await asyncio.sleep(delay)

    async def ticker_task(self) -> None:
        await self.universe_ready.wait()
        await self.ticker_stream.run()

    async def health_loop(self) -> None:
        last_rtt = 0.0
        while True:
            await asyncio.sleep(5)
            now = time.time()
            # velocidad de mensajes
            total = self.ticker_stream.msgs + sum(s.msgs for s in self.feed.shards)
            self.msg_rate = (total - self._prev_msgs) / 5.0
            self._prev_msgs = total
            # feeds caídos
            for s in [self.ticker_stream] + list(self.feed.shards):
                down = (not s.connected) and (now - s.since > self.cfg.feed_alert_s)
                if down and s.name not in self._down_alerted:
                    self._down_alerted.add(s.name)
                    self.notifier.send(f"⚠️ <b>Feed caído:</b> {s.name} lleva {fmt_dur(now - s.since)} sin conexión. Reintentando automáticamente.")
                elif s.connected and s.name in self._down_alerted:
                    self._down_alerted.discard(s.name)
                    self.notifier.send(f"✅ <b>Feed restablecido:</b> {s.name}")
            # time-stop
            if self.cfg.max_hold_min > 0:
                for sym, p in list(self.state.positions.items()):
                    if now - p.opened_at > self.cfg.max_hold_min * 60:
                        self.broker.force_close(sym, self.market.last.get(sym, p.entry), "TIME")
            # RTT REST + sincronía de reloj
            if now - last_rtt > 60:
                last_rtt = now
                with contextlib.suppress(Exception):
                    await self.sync_time()

    async def saver_loop(self) -> None:
        while True:
            await asyncio.sleep(2)
            if self.state.dirty:
                self.state.save()

    async def daily_loop(self) -> None:
        while True:
            today = utc_day()
            if self.state.day != today:
                a, b = self.render_daily(self.state.day)
                self.notifier.send(a)
                self.notifier.send(b)
                self.rollover(today)
            now = datetime.now(UTC)
            nxt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            await asyncio.sleep(max(0.5, min(30.0, (nxt - now).total_seconds() + 0.2)))

    def rollover(self, today: str) -> None:
        st = self.state
        st.day, st.day_start_balance = today, st.balance
        st.detections, st.signals_today, st.breaker_day = {}, 0, ""
        st.dirty = True
        log.info("nuevo día UTC %s (balance %.2f)", today, st.balance)

    # ── ciclo de vida ────────────────────────────────────────────────────────
    async def run(self) -> None:
        self.stop = asyncio.Event()
        self.universe_ready = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sg in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError, RuntimeError, ValueError):
                loop.add_signal_handler(sg, self.stop.set)
        self.state.load()
        await self.rest.start()
        notifier_task = asyncio.create_task(self.notifier.run())
        tasks: List[asyncio.Task] = []
        try:
            with contextlib.suppress(Exception):
                await self.sync_time()
            self.notifier.send(self.render_startup())
            # Telegram arranca en segundo plano: el escaneo NO depende de que Telegram responda
            # (los mensajes se encolan y salen en cuanto haya conexión).
            tasks = [asyncio.create_task(self.supervise(n, f)) for n, f in (
                ("telegram", self.telegram.start), ("universo", self.universe_loop),
                ("ticker", self.ticker_task), ("salud", self.health_loop),
                ("guardado", self.saver_loop), ("diario", self.daily_loop))]
            await self.stop.wait()
        finally:
            log.info("apagando…")
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await self.feed.stop()
            self.state.save()
            if self.notifier.ready.is_set():
                self.notifier.send("🔌 <b>Bot detenido.</b> Las posiciones abiertas quedaron guardadas y se retomarán al reiniciar.")
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(self.notifier.q.join(), timeout=6)
            notifier_task.cancel()
            await asyncio.gather(notifier_task, return_exceptions=True)
            await self.telegram.stop()
            await self.rest.close()

    # ══════════════════════════════════════════════════════════════════════════
    #  RENDERERS (texto HTML de Telegram)
    # ══════════════════════════════════════════════════════════════════════════
    def unrealized(self, p: Position) -> float:
        last = self.market.last.get(p.symbol, p.entry)
        return p.d * (last - p.entry) * p.remaining

    def render_help(self) -> str:
        return ("📖 <b>Comandos</b>\n"
                "/start — menú de bienvenida\n"
                "/status — estado del escáner, latencia y posiciones abiertas (TPs y SL actual)\n"
                "/balance — balance ficticio y PnL no realizado\n"
                "/trades — últimos 5 trades cerrados con desglose\n"
                "/summary — aciertos, pérdidas y win-rate global\n"
                "/top — top 10 ganadoras y 10 perdedoras (24h) + si el bot las detectó\n"
                "/report — reporte del día en curso\n"
                "/pause · /resume — pausar / reanudar nuevas entradas\n"
                "/help — esta ayuda\n\n"
                "<i>Simulación: no se envían órdenes reales.</i>")

    def render_welcome(self) -> str:
        c = self.cfg
        return (f"🤖 <b>Quant Scanner Bot</b> — Binance USDT-M Futures (paper trading)\n\n"
                f"Escaneo continuo del mercado en velas de 1m y 5m buscando spikes de volumen (≥{c.vol_spike:g}×), "
                f"explosión de ATR, rupturas de rango y desbalance de order-flow, antes de que el precio se dispare.\n\n"
                f"💵 ${c.margin_usd:g} por entrada · {c.leverage}x · nocional ${c.margin_usd * c.leverage:g}\n"
                f"🎯 TP1 +{c.tp1_pct:g}% ({c.tp1_size * 100:.0f}%) → SL a BE · TP2 +{c.tp2_pct:g}% ({c.tp2_size * 100:.0f}%) · "
                f"TP3 +{c.tp3_pct:g}% ({c.tp3_size * 100:.0f}%) · SL -{c.sl_pct:g}%\n\n"
                + self.render_help())

    def render_startup(self) -> str:
        st = self.state
        return (f"🟢 <b>Bot iniciado</b> · balance simulado {fmt_usd(st.balance, plus=False)} · "
                f"{len(st.positions)} posiciones recuperadas · {'⏸️ PAUSADO' if st.paused else 'escaneando'}\n"
                f"Escribe /status para ver el estado.")

    def render_status(self) -> str:
        st, m, cfg = self.state, self.market, self.cfg
        now = time.time()
        lat = list(m.lat)
        p50 = float(np.percentile(lat, 50)) if lat else 0.0
        p95 = float(np.percentile(lat, 95)) if lat else 0.0
        kl_ok = sum(1 for s in self.feed.shards if s.connected)
        tk = self.ticker_stream
        ready = sum(1 for s in self.feed.series.values() if s.ready)
        recon = tk.reconnects + sum(s.reconnects for s in self.feed.shards)
        head = "⏸️ <b>PAUSADO</b> (sin nuevas entradas)" if st.paused else "🟢 <b>ESCÁNER ACTIVO</b>"
        lines = [
            head,
            f"⏱ Uptime {fmt_dur(now - st.started_at)} · reconexiones WS: {recon}",
            f"📡 Ticker global: {'✅' if tk.connected else '❌'} · klines: {kl_ok}/{len(self.feed.shards)} conexiones {'✅' if kl_ok == len(self.feed.shards) and kl_ok else '⚠️'}",
            f"🔭 Pares con velas listas: {len(self.feed.symbols)} (de {m.total_symbols} USDT-perps) · series OK {ready}/{len(self.feed.series)}",
            f"⚡ {self.msg_rate:,.0f} msg/s · latencia WS p50 {p50:.0f} ms / p95 {p95:.0f} ms · REST {m.rest_rtt_ms:.0f} ms",
            f"🔎 Señales hoy: {st.signals_today}" + (f" · última {hhmm(st.last_signal_ts)} UTC" if st.last_signal_ts else ""),
            "",
            f"📂 <b>Posiciones abiertas ({len(st.positions)}/{cfg.max_positions})</b>",
        ]
        if not st.positions:
            lines.append("— ninguna —")
        for p in sorted(st.positions.values(), key=lambda x: x.opened_at):
            last = m.last.get(p.symbol, p.entry)
            mv = p.d * (last / p.entry - 1.0) * 100.0
            pnl = p.realized + self.unrealized(p)
            sl_txt = {"BE": "BE", "TP1": "TP1"}.get(p.sl_moved_to, "inicial")
            ic = "🟢" if p.side == "LONG" else "🔴"
            lines.append(
                f"{ic} <b>{p.symbol}</b> {p.side} · {p.tf} · hace {fmt_dur(now - p.opened_at)}\n"
                f"   entrada <code>{fmt_price(p.entry)}</code> → ahora <code>{fmt_price(last)}</code> ({fmt_pct(mv)} precio)\n"
                f"   PnL {fmt_usd(pnl)} ({fmt_pct(pnl / p.margin * 100, 1)} ROE) · restante {p.remaining / p.qty * 100:.0f}%\n"
                f"   TP1 {'✅' if p.tp1_hit else '⏳'} TP2 {'✅' if p.tp2_hit else '⏳'} TP3 {'✅' if p.tp3_hit else '⏳'} · "
                f"SL {sl_txt}: <code>{fmt_price(p.sl)}</code>")
        return "\n".join(lines)

    def render_balance(self) -> str:
        st, cfg = self.state, self.cfg
        unreal = sum(self.unrealized(p) for p in st.positions.values())
        used = self.broker.margin_used()
        equity = st.balance + unreal
        total = st.balance - cfg.initial_balance
        day = st.balance - st.day_start_balance
        return "\n".join([
            "💼 <b>BALANCE (simulado)</b>",
            f"Capital inicial: {fmt_usd(cfg.initial_balance, plus=False)}",
            f"Balance realizado: <b>{fmt_usd(st.balance, plus=False)}</b>",
            f"PnL no realizado: {fmt_usd(unreal)} ({len(st.positions)} posiciones)",
            f"Equity: <b>{fmt_usd(equity, plus=False)}</b>",
            f"Margen en uso: {fmt_usd(used, plus=False)} · libre: {fmt_usd(st.balance - used, plus=False)}",
            "",
            f"📈 PnL acumulado: <b>{fmt_usd(total)}</b> ({fmt_pct(total / cfg.initial_balance * 100)})",
            f"📅 PnL de hoy (UTC): {fmt_usd(day)} ({fmt_pct(day / st.day_start_balance * 100 if st.day_start_balance else 0)})",
        ])

    def render_trades(self) -> str:
        st = self.state
        if not st.closed:
            return "🧾 Aún no hay trades cerrados."
        now = time.time()
        out = ["🧾 <b>Últimos trades cerrados</b>"]
        for i, t in enumerate(reversed(st.closed[-5:]), 1):
            ic = "✅" if t.pnl > 0 else "❌"
            side = "🟢" if t.side == "LONG" else "🔴"
            brk = " · ".join(f"{f['label']} {fmt_usd(f['pnl'])}" for f in t.fills)
            out.append(
                f"\n{i}. {side} <b>{t.symbol}</b> {t.side} · {t.outcome} · {ic} <b>{fmt_usd(t.pnl)}</b> ({fmt_pct(t.roe_pct, 1)} ROE)\n"
                f"   <code>{fmt_price(t.entry)}</code> → <code>{fmt_price(t.exit_avg)}</code> · "
                f"duró {fmt_dur(t.closed_at - t.opened_at)} · hace {fmt_dur(now - t.closed_at)}\n"
                f"   <i>{brk}</i>")
        return "\n".join(out)

    def render_summary(self) -> str:
        st, cfg = self.state, self.cfg
        s = calc_stats(st.closed)
        if not s["n"]:
            return "📊 Aún no hay trades cerrados para resumir."
        pf = "∞" if s["pf"] == float("inf") else f"{s['pf']:.2f}"
        outcomes: Dict[str, int] = {}
        for t in st.closed:
            outcomes[t.outcome] = outcomes.get(t.outcome, 0) + 1
        hit1 = sum(1 for t in st.closed if t.tp_hits >= 1) / s["n"] * 100
        hit2 = sum(1 for t in st.closed if t.tp_hits >= 2) / s["n"] * 100
        hit3 = sum(1 for t in st.closed if t.tp_hits >= 3) / s["n"] * 100
        total = st.balance - cfg.initial_balance
        return "\n".join([
            "📊 <b>RESUMEN GLOBAL</b>",
            f"Trades cerrados: {s['n']}",
            f"✅ Aciertos: {s['wins']}   ❌ Pérdidas: {s['losses']}",
            f"🎯 Win-rate: <b>{s['wr']:.1f}%</b>",
            f"💰 PnL neto: <b>{fmt_usd(s['pnl'])}</b> · comisiones {fmt_usd(s['fees'], plus=False)}",
            f"📈 Balance: {fmt_usd(st.balance, plus=False)} ({fmt_pct(total / cfg.initial_balance * 100)})",
            f"Profit factor: {pf} · ganancia media {fmt_usd(s['avg_win'])} · pérdida media {fmt_usd(s['avg_loss'])}",
            f"Mejor: {s['best'].symbol} {fmt_usd(s['best'].pnl)} · Peor: {s['worst'].symbol} {fmt_usd(s['worst'].pnl)}",
            f"Llegaron a TP1 {hit1:.0f}% · TP2 {hit2:.0f}% · TP3 {hit3:.0f}%",
            "Salidas: " + " · ".join(f"{k} {v}" for k, v in sorted(outcomes.items(), key=lambda kv: -kv[1])),
        ])

    # -- top ganadoras / perdedoras ------------------------------------------
    def top_lists(self, n: int) -> Tuple[List[tuple], List[tuple]]:
        m, cfg = self.market, self.cfg
        rows = [(sym, chg, q) for sym, (chg, q, _) in m.t24.items()
                if sym in m.valid and q >= cfg.top_min_quote_vol]
        rows.sort(key=lambda r: r[1], reverse=True)
        return rows[:n], rows[::-1][:n]

    def _flag(self, sym: str, side: str) -> str:
        det = self.state.detections.get(f"{sym}|{side}")
        if not det:
            return "❌ sin detectar"
        last = self.market.last.get(sym)
        mv = ""
        if last and det.get("price"):
            d = 1 if side == "LONG" else -1
            mv = f" · {fmt_pct(d * (last / det['price'] - 1) * 100, 1)} desde {hhmm(det['ts'])}"
        return ("✅ detectada" if det["status"] == "opened" else "👀 detectada (no operada)") + mv

    def render_top(self, prefix: str = "") -> str:
        n = self.cfg.top_n
        gainers, losers = self.top_lists(n)
        if not gainers:
            return "🏆 Aún no hay datos de mercado."
        cov_g = sum(1 for r in gainers if f"{r[0]}|LONG" in self.state.detections)
        cov_l = sum(1 for r in losers if f"{r[0]}|SHORT" in self.state.detections)
        out = [f"🏆 <b>{prefix}TOP {n} GANADORAS (24h)</b>"]
        for i, (sym, chg, q) in enumerate(gainers, 1):
            out.append(f"{i}. <b>{sym}</b> {fmt_pct(chg, 1)} · vol {fmt_big(q)} · {self._flag(sym, 'LONG')}")
        out.append(f"\n📉 <b>{prefix}TOP {n} PERDEDORAS (24h)</b>")
        for i, (sym, chg, q) in enumerate(losers, 1):
            out.append(f"{i}. <b>{sym}</b> {fmt_pct(chg, 1)} · vol {fmt_big(q)} · {self._flag(sym, 'SHORT')}")
        out.append(f"\n🎯 Cobertura del escáner hoy: {cov_g}/{len(gainers)} ganadoras · {cov_l}/{len(losers)} perdedoras detectadas")
        out.append("<i>✅ operada · 👀 señal descartada por filtros · ❌ no detectada</i>")
        return "\n".join(out)

    def render_daily(self, day: str, partial: bool = False) -> Tuple[str, str]:
        st, cfg = self.state, self.cfg
        trades = [t for t in st.closed if utc_day(t.closed_at) == day]
        s = calc_stats(trades)
        day_pnl = (st.balance - st.day_start_balance) if day == st.day else s["pnl"]
        base = st.day_start_balance if day == st.day and st.day_start_balance else cfg.initial_balance
        total = st.balance - cfg.initial_balance
        unreal = sum(self.unrealized(p) for p in st.positions.values())
        title = f"📅 <b>REPORTE {'PARCIAL' if partial else 'DIARIO'} — {day} (UTC)</b>"
        a = "\n".join([
            title, "━━━━━━━━━━━━━━━━━━━━",
            f"📊 Trades cerrados: {s['n']}",
            f"✅ Aciertos: {s['wins']}",
            f"❌ Pérdidas: {s['losses']}",
            f"🎯 Win-rate: <b>{s['wr']:.1f}%</b>",
            f"💰 PnL del día: <b>{fmt_usd(day_pnl)}</b>",
            f"📈 Rendimiento del día: <b>{fmt_pct(day_pnl / base * 100)}</b> sobre {fmt_usd(base, plus=False)}",
            f"🏦 PnL acumulado ficticio: <b>{fmt_usd(total)}</b> (balance {fmt_usd(st.balance, plus=False)})",
            f"🔎 Señales del día: {st.signals_today if day == st.day else '—'} · abiertas ahora: {len(st.positions)} "
            f"(no realizado {fmt_usd(unreal)})",
        ])
        return a, self.render_top(prefix=f"{'PARCIAL · ' if partial else 'CIERRE · '}")


# ══════════════════════════════════════════════════════════════════════════════
#  ARRANQUE
# ══════════════════════════════════════════════════════════════════════════════
def validate_config(cfg: Config) -> List[str]:
    problems = []
    if abs(cfg.tp1_size + cfg.tp2_size + cfg.tp3_size - 1.0) > 1e-9:
        problems.append("tp1_size + tp2_size + tp3_size debe sumar 1.0")
    if not (cfg.tp1_pct < cfg.tp2_pct < cfg.tp3_pct):
        problems.append("los TP deben ser crecientes (tp1 < tp2 < tp3)")
    if cfg.sl_pct <= 0 or cfg.leverage < 1 or cfg.margin_usd <= 0:
        problems.append("sl_pct, leverage y margin_usd deben ser positivos")
    if cfg.sl_pct * cfg.leverage >= 100:
        problems.append("el SL implicaría liquidación (sl_pct × leverage ≥ 100 %)")
    return problems


def main() -> None:
    cfg = Config()
    setup_logging(cfg)
    problems = validate_config(cfg)
    if problems:
        for p in problems:
            log.error("configuración inválida: %s", p)
        raise SystemExit(2)
    if sys.platform == "win32" and sys.version_info < (3, 14) and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    app = ScannerApp(cfg)
    runner: Callable = asyncio.run
    try:
        import uvloop  # type: ignore
        runner = uvloop.run
    except ImportError:
        pass
    try:
        runner(app.run())
    except KeyboardInterrupt:
        log.info("Interrumpido por el usuario")


if __name__ == "__main__":
    main()

"""A. DATA ENGINE - extraccion de historicos y especificaciones desde MetaTrader 5 (solo lectura).

No genera ni rellena datos faltantes. No usa credenciales. No envia ordenes.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import DATA_DIR, LOGS_DIR

log = logging.getLogger("remix.data")

TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}


def _mt5():
    import MetaTrader5 as mt5  # import perezoso: los tests no requieren terminal
    return mt5


def connect() -> bool:
    mt5 = _mt5()
    if not mt5.initialize():
        log.error("mt5.initialize() fallo: %s", mt5.last_error())
        return False
    return True


def resolve_symbol(base: str) -> str | None:
    """Verifica el nombre real del simbolo con symbols_get()."""
    mt5 = _mt5()
    names = [s.name for s in (mt5.symbols_get() or [])]
    if base in names:
        return base
    cands = [n for n in names if n.upper() == base.upper()]
    return cands[0] if cands else None


def symbol_spec(symbol: str) -> dict:
    mt5 = _mt5()
    mt5.symbol_select(symbol, True)
    i = mt5.symbol_info(symbol)
    if i is None:
        raise RuntimeError(f"symbol_info({symbol}) -> {mt5.last_error()}")
    return {
        "symbol": symbol, "digits": i.digits, "point": i.point,
        "contract_size": i.trade_contract_size,
        "tick_size": i.trade_tick_size, "tick_value": i.trade_tick_value,
        "value_per_price_unit_per_lot": i.trade_tick_value / i.trade_tick_size,
        "volume_min": i.volume_min, "volume_step": i.volume_step, "volume_max": i.volume_max,
        "stops_level": i.trade_stops_level, "spread_now_points": i.spread,
        "swap_mode": i.swap_mode, "swap_long": i.swap_long, "swap_short": i.swap_short,
        "swap_rollover3days": i.swap_rollover3days,
        "currency_profit": i.currency_profit, "currency_base": i.currency_base,
    }


def _tf_const(tf: str):
    return getattr(_mt5(), f"TIMEFRAME_{tf}")


def fetch_rates(symbol: str, tf: str, start: datetime, end: datetime, chunk_days: int = 20) -> pd.DataFrame:
    """Descarga por bloques (copy_rates_range falla con rangos muy largos en M5)."""
    mt5 = _mt5()
    mt5.symbol_select(symbol, True)
    parts = []
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=chunk_days), end)
        r = mt5.copy_rates_range(symbol, _tf_const(tf), cur, nxt)
        if r is None:
            log.warning("copy_rates_range %s %s %s..%s -> %s", symbol, tf, cur, nxt, mt5.last_error())
        elif len(r):
            parts.append(pd.DataFrame(r))
        cur = nxt
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], unit="s")  # hora de servidor (naive)
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    return df[["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]]


def cache_path(symbol: str, tf: str):
    return DATA_DIR / "raw" / f"{symbol}_{tf}.csv"


def save_rates(df: pd.DataFrame, symbol: str, tf: str):
    p = cache_path(symbol, tf)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    return p


def load_rates(symbol: str, tf: str, start=None, end=None) -> pd.DataFrame:
    p = cache_path(symbol, tf)
    if not p.exists():
        raise FileNotFoundError(f"Sin datos en cache: {p}. Ejecute scripts/01_download_data.py")
    df = pd.read_csv(p, parse_dates=["time"])
    if start is not None:
        df = df[df["time"] >= pd.Timestamp(start)]
    if end is not None:
        df = df[df["time"] < pd.Timestamp(end) + pd.Timedelta(days=1)]
    return df.reset_index(drop=True)


def verify_data(df: pd.DataFrame, tf: str) -> dict:
    """Controles de integridad. No corrige nada: solo informa."""
    if df.empty:
        return {"ok": False, "reason": "vacio"}
    step = pd.Timedelta(minutes=TF_MINUTES[tf])
    dt = df["time"].diff().dropna()
    gaps = dt[dt > step]
    # huecos > 4 dias = anomalia (fines de semana ~2 dias; festivos ~3)
    big = gaps[gaps > pd.Timedelta(days=4)]
    bad_ohlc = ((df.high < df[["open", "close"]].max(axis=1)) | (df.low > df[["open", "close"]].min(axis=1))).sum()
    return {
        "ok": bool(len(big) == 0 and bad_ohlc == 0 and df["time"].is_monotonic_increasing),
        "bars": int(len(df)),
        "first": str(df["time"].iloc[0]), "last": str(df["time"].iloc[-1]),
        "duplicates": int(df["time"].duplicated().sum()),
        "monotonic": bool(df["time"].is_monotonic_increasing),
        "gaps_over_1_bar": int(len(gaps)),
        "gaps_over_4_days": [str(x) for x in big.index.map(lambda i: df["time"].iloc[i - 1])][:10],
        "bad_ohlc_rows": int(bad_ohlc),
        "nan_rows": int(df.isna().any(axis=1).sum()),
        "median_spread_points": float(df["spread"].median()),
        "p95_spread_points": float(df["spread"].quantile(0.95)),
        "max_spread_points": int(df["spread"].max()),
    }


def save_json(obj, name: str):
    p = DATA_DIR / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
    return p

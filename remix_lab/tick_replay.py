"""Repeticion de salidas con TICKS REALES (Bid/Ask) sobre entradas fijas. Mismas definiciones de Variant que exit_variants.py.
Convenciones: long entra a Ask (precio oficial) y sale a Bid; short entra a Bid y sale a Ask. Orden de eventos = orden de ticks.
Gestion (BE/trailing/parcial) se decide tick a tick y entra en vigor tras `lat_ms` (0 = inmediato; estres = 1000).
Salida por stop: al nivel del stop si el tick lo cruza sin salto; si el tick ya esta mas alla (salto), al precio del tick (pesimista).
Solo lectura de datos (copy_ticks_range); sin operaciones.
"""
from datetime import timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .exit_variants import PT, Variant

CACHE = Path(__file__).resolve().parent.parent / "data" / "raw" / "ticks_S01"


def load_ticks(symbol, t_open: pd.Timestamp, t_end: pd.Timestamp):
    """Devuelve dict(t_ms, bid, ask) con cache npz. t_* son hora servidor (tratada como UTC naive, igual que MT5)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{symbol}_{t_open:%Y%m%d_%H%M%S}_{t_end:%Y%m%d_%H%M%S}.npz"
    if f.exists():
        z = np.load(f)
        return {k: z[k] for k in ("t_ms", "bid", "ask")}
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError("MT5 no inicializa")
    try:
        assert mt5.account_info().trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
        tk = mt5.copy_ticks_range(symbol, t_open.to_pydatetime().replace(tzinfo=timezone.utc),
                                  t_end.to_pydatetime().replace(tzinfo=timezone.utc), mt5.COPY_TICKS_ALL)
    finally:
        mt5.shutdown()
    if tk is None or len(tk) == 0:
        return None
    d = {"t_ms": tk["time_msc"].astype(np.int64), "bid": tk["bid"].astype(float), "ask": tk["ask"].astype(float)}
    np.savez_compressed(f, **d)
    return d


def _ms(ts: pd.Timestamp) -> int:
    return int(ts.value // 1_000_000)


def simulate_ticks(tr, tk, bars: pd.DataFrame, v: Variant, lat_ms: int = 0) -> dict:
    d, e, risk = int(tr.dir), float(tr.entry), float(tr.sl_dist)
    lots = float(tr.lots)
    t0 = _ms(tr.open_time)
    t, bid, ask = tk["t_ms"], tk["bid"], tk["ask"]
    # indice de barra para cada tick (para ATR / estructura confirmada)
    bt = bars.time.values.astype("datetime64[ms]").astype(np.int64)
    bi = np.searchsorted(bt, t, side="right") - 1
    atr_a = bars.atr.values
    day0 = tr.open_time.normalize()
    exit_ms = _ms(day0 + pd.Timedelta(hours=v.exit_hour))
    maxdur_ms = t0 + int(v.max_dur_h * 3600_000) if v.max_dur_h > 0 else None
    noc_ms = t0 + v.nocont_bars * 900_000 if v.nocont_bars else None
    i_start = int(np.searchsorted(t, t0))
    sl = e - d * risk
    tp = e + d * 1.5 * risk
    slip = v.slip_pts * PT
    mfe = 0.0
    hh = -1e9
    ll = 1e9
    pend = []              # (ms efectivo, nuevo sl)
    parts, rem = [], 1.0
    partial_done = be_done = False
    last_bar_struct = -1
    struct_sl = None
    moved = False
    reason = "FIN_DATOS"
    for k in range(i_start, len(t)):
        tm = t[k]
        b_, a_ = bid[k], ask[k]
        if pend and tm >= pend[0][0]:
            ns = pend.pop(0)[1]
            if (d == 1 and ns > sl) or (d == -1 and ns < sl):
                sl = ns; moved = True
        # tiempo
        time_exit = tm >= exit_ms or bool(maxdur_ms and tm >= maxdur_ms)
        if noc_ms and tm >= noc_ms:
            if mfe < v.nocont_R * risk:
                time_exit = True
            noc_ms = None                         # comprobacion unica
        if time_exit:
            px = b_ if d == 1 else a_
            parts.append((rem, d * (px - e))); rem = 0; reason = "TIME"; break
        # stops / objetivo
        if d == 1:
            if b_ <= sl:
                px = min(sl, b_) - slip
                parts.append((rem, px - e)); rem = 0; reason = "SL_MOVED" if moved else "SL"; break
            if b_ >= tp:
                parts.append((rem, max(tp, b_) - e)); rem = 0; reason = "TP"; break   # salto: se rellena al tick (como el Tester)
            fav = b_ - e
        else:
            if a_ >= sl:
                px = max(sl, a_) + slip
                parts.append((rem, e - px)); rem = 0; reason = "SL_MOVED" if moved else "SL"; break
            if a_ <= tp:
                parts.append((rem, e - min(tp, a_))); rem = 0; reason = "TP"; break
            fav = e - a_
        if fav > mfe:
            mfe = fav
        if v.partial_R and not partial_done and lots >= 0.02 and mfe >= v.partial_R * risk:
            frac = 0.5
            parts.append((frac, v.partial_R * risk)); rem -= frac; partial_done = True
        if v.be_trigger_R and not be_done and mfe >= v.be_trigger_R * risk:
            new = e + d * v.be_buffer_px
            pend.append((tm + lat_ms, new)); be_done = True
        if v.trail_mode and mfe >= v.trail_act_R * risk:
            if v.trail_mode == "atr":
                a14 = atr_a[bi[k]]
                if not np.isnan(a14):
                    if d == 1:
                        hh = max(hh, b_); cand = hh - v.trail_atr_mult * a14
                    else:
                        ll = min(ll, a_); cand = ll + v.trail_atr_mult * a14
                    if (d == 1 and cand > sl) or (d == -1 and cand < sl):
                        pend.append((tm + lat_ms, cand))
            elif v.trail_mode == "struct":
                j = bi[k]
                if j != last_bar_struct and j - v.struct_n >= 0:     # solo barras CONFIRMADAS (anteriores a la actual)
                    w = bars.iloc[j - v.struct_n:j]
                    cand = w.low.min() if d == 1 else (w.high + w.spread * PT).max()
                    if (d == 1 and cand > sl) or (d == -1 and cand < sl):
                        pend.append((tm + lat_ms, cand))
                    last_bar_struct = j
    if rem > 1e-9:
        parts.append((rem, 0.0))
    R = sum(f * mv for f, mv in parts) / risk
    return {"R": R, "reason": reason, "exit_ms": int(tm) if reason != "FIN_DATOS" else None, "mfe_R_tick": mfe / risk}


def run_variant_ticks(trades: pd.DataFrame, bars: pd.DataFrame, v: Variant, symbol="EURUSDm", lat_ms=0):
    out = []
    for tr in trades.itertuples():
        end = tr.open_time.normalize() + pd.Timedelta(hours=17, minutes=1)
        tk = load_ticks(symbol, tr.open_time.floor("15min"), end)
        if tk is None:
            out.append({"R": np.nan, "reason": "SIN_TICKS", "exit_ms": None, "mfe_R_tick": np.nan}); continue
        out.append(simulate_ticks(tr, tk, bars, v, lat_ms))
    o = pd.DataFrame(out); o["vid"] = v.vid; o["open_time"] = trades.open_time.values; o["dir"] = trades.dir.values
    return o

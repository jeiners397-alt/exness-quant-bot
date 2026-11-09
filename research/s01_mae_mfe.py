"""MAE/MFE por operacion de S01 (335 oficiales).
- Operaciones con ticks reales (desde 2026-01-02): secuencia de ticks Bid/Ask exacta (long: sale a Bid; short: sale a Ask).
- Operaciones 2025 (sin ticks en el terminal): COTA por barras M15 (bid OHLC + spread de barra para shorts). El orden intrabarra
  NO se infiere: solo se informa MFE/MAE como extremos de barras, marcados metodo=BAR_BOUND, sin tiempos finos.
Solo lectura de datos. Salida: research/S01_MAE_MFE_ANALYSIS.csv
"""
from datetime import timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
T = pd.read_csv(ROOT / "research/S01_TRADES_RECONSTRUCTED.csv", parse_dates=["open_time", "close_time"])
M = pd.read_csv(ROOT / "data/raw/EURUSDm_M15.csv", parse_dates=["time"])
PT = 1e-5
assert mt5.initialize()
assert mt5.account_info().trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
FIRST_TICK = pd.Timestamp("2026-01-02")
rows = []
for r in T.itertuples():
    d, e, risk_px = r.dir, r.entry, r.sl_dist
    o = r.open_time
    c = r.close_time
    if o >= FIRST_TICK:
        a = o.to_pydatetime().replace(tzinfo=timezone.utc)
        b = (c + pd.Timedelta(seconds=1)).to_pydatetime().replace(tzinfo=timezone.utc)
        tk = mt5.copy_ticks_range("EURUSDm", a, b, mt5.COPY_TICKS_ALL)
        ok = tk is not None and len(tk) > 10
        if ok:
            ts = pd.to_datetime(tk["time_msc"], unit="ms")
            bid, ask = tk["bid"], tk["ask"]
            fav = (bid - e) if d == 1 else (e - ask)      # PnL de precio si se cerrara en ese tick
            i_mfe, i_mae = int(np.argmax(fav)), int(np.argmin(fav))
            mfe, mae = max(fav.max(), 0.0), max(-fav.min(), 0.0)
            t_mfe = (ts[i_mfe] - o).total_seconds() / 60
            t_mae = (ts[i_mae] - o).total_seconds() / 60
            method, n_ticks, spr_med = "TICKS_REAL", len(tk), float(np.median((ask - bid) / PT))
        else:
            method = "SIN_TICKS"; mfe = mae = t_mfe = t_mae = np.nan; n_ticks = 0; spr_med = np.nan
    else:
        w = M[(M.time >= o) & (M.time < c.floor("15min"))]          # excluye la barra de salida (extremos posteriores a la salida)
        if len(w):
            if d == 1:
                mfe, mae = max(w.high.max() - e, 0.0), max(e - w.low.min(), 0.0)
            else:
                mfe = max(e - (w.low + w.spread * PT).min(), 0.0)
                mae = max((w.high + w.spread * PT).max() - e, 0.0)
        else:
            mfe = mae = 0.0
        # la salida real fija un minimo observado (SL/TP alcanzado)
        real_move = (r.exit - e) * d
        mfe, mae = max(mfe, real_move, 0.0), max(mae, -real_move, 0.0)
        method, n_ticks, spr_med, t_mfe, t_mae = "BAR_BOUND", 0, float(w.spread.median()) if len(w) else np.nan, np.nan, np.nan
    real_move = (r.exit - e) * d
    rows.append({"idx": r.Index, "open_time": o, "close_time": c, "dir": d, "exit_reason": r.exit_reason, "method": method, "n_ticks": n_ticks,
                 "risk_px": risk_px, "mfe_px": mfe, "mae_px": mae, "mfe_R": mfe / risk_px, "mae_R": mae / risk_px,
                 "realized_R_price": real_move / risk_px, "R_pnl": r.R,
                 "captured_frac_of_mfe": (real_move / mfe) if mfe > 0 else np.nan,
                 "min_to_mfe": t_mfe, "min_to_mae": t_mae, "min_to_close": (c - o).total_seconds() / 60, "median_spread_pts": spr_med})
mt5.shutdown()
O = pd.DataFrame(rows)
O.to_csv(ROOT / "research/S01_MAE_MFE_ANALYSIS.csv", index=False)
print(O.method.value_counts().to_dict())
print(O.groupby(["method", "exit_reason"])[["mfe_R", "mae_R"]].median().round(2))
sl = O[O.exit_reason == "SL"]
for k in (0.25, 0.5, 0.75, 1.0):
    print(f"SL con MFE>={k}R: {(sl.mfe_R >= k).sum()}/{len(sl)} ({(sl.mfe_R >= k).mean()*100:.0f}%)  [ticks: {(sl[sl.method=='TICKS_REAL'].mfe_R >= k).sum()}/{(sl.method=='TICKS_REAL').sum()}]")
tm = O[O.exit_reason == "TIME"]
print("TIME: MFE mediana", round(tm.mfe_R.median(), 2), "MAE mediana", round(tm.mae_R.median(), 2), "capturado medio", round(tm.captured_frac_of_mfe.mean(), 2))
print("Spread mediano barras 2025 vs ticks 2026 (pts):", O.groupby("method").median_spread_pts.median().to_dict())

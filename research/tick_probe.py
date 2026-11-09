"""Sonda de disponibilidad de ticks (solo lectura, copy_ticks_range). Resume ticks/dia y calidad por mes."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
assert mt5.initialize()
ai = mt5.account_info()
assert ai.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO, "no es demo"
sym = "EURUSDm"
mt5.symbol_select(sym, True)
days = pd.date_range("2025-01-06", "2026-10-28", freq="14D")  # 1 dia por quincena (lunes)
rows = []
for d in days:
    a = d.to_pydatetime().replace(tzinfo=timezone.utc)
    t = mt5.copy_ticks_range(sym, a, a + timedelta(hours=24), mt5.COPY_TICKS_ALL)
    if t is None or len(t) == 0:
        rows.append({"day": str(d.date()), "n": 0}); continue
    df = pd.DataFrame(t)
    gaps = np.diff(df.time_msc.values) / 1000
    rows.append({"day": str(d.date()), "n": len(df), "first": str(pd.to_datetime(df.time_msc.iloc[0], unit="ms")), "last": str(pd.to_datetime(df.time_msc.iloc[-1], unit="ms")),
                 "max_gap_s": round(float(gaps.max()), 1), "pct_gap_gt60s": round(float((gaps > 60).mean() * 100), 3),
                 "spread_pts_med": round(float(((df.ask - df.bid) / 1e-5).median()), 1), "spread_pts_p95": round(float(((df.ask - df.bid) / 1e-5).quantile(.95)), 1),
                 "crossed": int((df.ask < df.bid).sum()), "has_volume_flag": bool((df.volume > 0).any())})
mt5.shutdown()
out = pd.DataFrame(rows)
out.to_csv(ROOT / "research/TICK_PROBE.csv", index=False)
print(out.to_string(index=False))

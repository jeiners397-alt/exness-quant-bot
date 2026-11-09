"""Diferencias restantes Python-MT5 de V2/L2: operaciones exclusivas y spread de barra (rates) vs spread del tick en el EA (log)."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research")); sys.path.insert(0, str(ROOT))
import parity_v2_l2 as P  # noqa: E402

off, sigs = P.load_official()
full = pd.read_csv(ROOT / "data/raw/hist/EURUSDm_H4_native_2022_2026.csv", parse_dates=["time"])
full.loc[full.spread <= 0, "spread"] = full.spread[full.spread > 0].median()
tr, info = P.python_run(full, warmup=True, gates=True, adx="mt5", reenter=True, calendar=True, session=True)
a, b = set(tr.entry_time), set(off.entry_time)
pd.set_option("display.width", 220)
print("SOLO PYTHON:"); print(tr[tr.entry_time.isin(a - b)][["entry_time", "dir", "lots", "entry", "exit_time", "exit_reason", "entry_spread_pts", "net_money"]].to_string(index=False))
print("SOLO MT5:"); print(off[off.entry_time.isin(b - a)][["entry_time", "dir", "lots", "entry", "exit_time", "reason", "spread_pts_log", "net"]].to_string(index=False))
s = sigs[sigs.event.isin(["OPEN", "SKIP_SPREAD"])].copy()
s["bar"] = s.time.dt.floor("4h")
m = s.merge(full[["time", "spread"]], left_on="bar", right_on="time", how="left", suffixes=("", "_rate"))
m["diff"] = m.spread_pts - m.spread
print(m[(m["diff"] != 0) | (m.event == "SKIP_SPREAD")][["time", "event", "spread_pts", "spread", "diff"]].to_string(index=False))
print("eventos", len(m), "spread igual", int((m["diff"] == 0).sum()))
m.to_csv(ROOT / "research/PARITY_V2_L2_SPREAD_LOG_VS_RATES.csv", index=False)


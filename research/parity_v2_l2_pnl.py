"""Descomposicion de la diferencia monetaria restante Python-MT5 (30/30 entradas coinciden): por motivo de salida, precio de salida, swap."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research")); sys.path.insert(0, str(ROOT))
import parity_v2_l2 as P  # noqa: E402

off, sigs = P.load_official()
full = pd.read_csv(ROOT / "data/raw/hist/EURUSDm_H4_native_2022_2026.csv", parse_dates=["time"])
full.loc[full.spread <= 0, "spread"] = full.spread[full.spread > 0].median()
tr, info = P.python_run(full, warmup=True, gates=True, adx="mt5", reenter=True, calendar=True, session=True)
J = off.merge(tr, on="entry_time", suffixes=("_mt5", "_py"))
J["d_exit_pts"] = (J.exit_mt5 - J.exit_py) * J.dir_mt5 / 1e-5               # >0 = MT5 sale mejor
J["d_exit_min"] = (pd.to_datetime(J.exit_time_mt5) - pd.to_datetime(J.exit_time_py)).dt.total_seconds() / 60
J["d_gross"] = J.profit - J.gross_money
J["d_swap"] = J.swap_mt5 - J.swap_py
J["d_net"] = J.net - J.net_money
J["nights_py"] = J.nights
cols = ["entry_time", "dir_mt5", "lots_mt5", "reason", "exit_time_mt5", "exit_time_py", "d_exit_min", "exit_mt5", "exit_py", "d_exit_pts", "profit", "gross_money", "d_gross", "swap_mt5", "swap_py", "d_swap", "d_net"]
pd.set_option("display.width", 250)
print(J[J.d_net.abs() > 0.5][cols].round(3).to_string(index=False))
g = J.groupby("reason").agg(n=("d_net", "size"), d_gross=("d_gross", "sum"), d_swap=("d_swap", "sum"), d_net=("d_net", "sum"), med_d_exit_pts=("d_exit_pts", "median")).round(2)
print(g)
print("TOTAL d_net", round(J.d_net.sum(), 2), " d_gross", round(J.d_gross.sum(), 2), " d_swap", round(J.d_swap.sum(), 2))
J.to_csv(ROOT / "research/PARITY_V2_L2_TRADES_MATCHED.csv", index=False)
# swap: noches y puntos por noche (MT5 vs modelo)
sw = J[J.swap_mt5 != 0][["entry_time", "dir_mt5", "lots_mt5", "swap_mt5", "swap_py", "nights_py"]]
sw = sw.assign(mt5_per_lot_night=lambda d: d.swap_mt5 / d.lots_mt5 / d.nights_py.replace(0, np.nan))
print(sw.round(3).to_string(index=False))


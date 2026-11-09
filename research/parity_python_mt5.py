"""FASE 2: paridad Python-MT5 para S01 (3000 USD, 0.5 %, estricto). Oficial = deals del Tester; Python = remix_lab (barras M15).
Nota: genera senales para todo el historico con parametros CANONICOS (no es seleccion de parametros; el holdout ya esta contaminado por la corrida oficial).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab.backtest import BacktestConfig, compute_lots, run_backtest  # noqa: E402
from remix_lab.experiments import load_spec  # noqa: E402
from remix_lab.strategies import generate  # noqa: E402

spec = load_spec("EURUSDm")
df = pd.read_csv(ROOT / "data/raw/EURUSDm_M15.csv", parse_dates=["time"])
df = df[(df.time >= "2025-01-01") & (df.time < "2026-11-01")].reset_index(drop=True)
sig = generate("S01", df, spec)
py, info = run_backtest(df, sig, spec, BacktestConfig(initial_capital=3000, risk_pct=0.5, sizing_policy="strict"))
O = pd.read_csv(ROOT / "research/S01_TRADES_RECONSTRUCTED.csv", parse_dates=["open_time", "close_time"])
O["bar"] = O.open_time.dt.floor("15min")
O["bal_before"] = 3000 + O.pnl.cumsum().shift(fill_value=0)
py["bar"] = pd.to_datetime(py.entry_time)
py["pyR"] = py.net_r
M = O.merge(py, on="bar", how="outer", suffixes=("_mt5", "_py"), indicator=True)
rep = {"n_mt5": len(O), "n_py": len(py), "both": int((M._merge == "both").sum()), "only_mt5": int((M._merge == "left_only").sum()), "only_py": int((M._merge == "right_only").sum())}
B = M[M._merge == "both"].copy()
rep["dir_agree"] = int((B.dir_mt5 == B.dir_py).sum())
# precio de entrada: Python ask=open+spread (long) / bid=open (short) vs oficial
rep["entry_px_diff_pts_median"] = round(float(((B.entry_mt5 - B.entry_py) / 1e-5).median()), 2)
rep["entry_px_diff_pts_abs_p95"] = round(float(((B.entry_mt5 - B.entry_py).abs() / 1e-5).quantile(.95)), 2)
rep["entry_px_exact"] = int(((B.entry_mt5 - B.entry_py).abs() < 1e-9).sum())
# SL/TP efectivos desde salidas SL/TP oficiales
sl_m = B[B.exit_reason_mt5 == "SL"]; tp_m = B[B.exit_reason_mt5 == "TP"]
rep["sl_dist_mt5_vs_py_pts_median"] = round(float((((sl_m.entry_mt5 - sl_m.exit_mt5).abs()) - sl_m.sl_dist_py).abs().median() / 1e-5), 2)
rep["tp_dist_mt5_vs_py_pts_median"] = round(float((((tp_m.exit_mt5 - tp_m.entry_mt5).abs()) - tp_m.tp_dist_py).abs().median() / 1e-5), 2)
# volumen: cadena propia de Python y formula con el balance oficial
lots_off = []
for r in B.itertuples():
    l, *_ = compute_lots(r.bal_before, 0.5, r.sl_dist_mt5, spec, "strict"); lots_off.append(l)
B["lots_py_with_mt5_balance"] = lots_off
rep["lots_equal_python_chain"] = int((B.lots_mt5 == B.lots_py).sum())
rep["lots_equal_formula_with_mt5_balance"] = int((B.lots_mt5 == B.lots_py_with_mt5_balance).sum())
rep["lots_diff_formula_max_abs"] = round(float((B.lots_mt5 - B.lots_py_with_mt5_balance).abs().max()), 3)
# motivos
mp = {"sl": "SL", "sl_gap": "SL", "tp": "TP", "time": "TIME", "end_of_data": "FIN"}
B["reason_py"] = B.exit_reason_py.map(mp)
rep["reason_agree"] = int((B.exit_reason_mt5 == B.reason_py).sum())
rep["reason_crosstab"] = pd.crosstab(B.exit_reason_mt5, B.reason_py).to_dict()
B["exit_diff_min"] = (pd.to_datetime(B.exit_time) - B.close_time).dt.total_seconds() / 60
rep["exit_time_diff_min_median"] = round(float(B.exit_diff_min.median()), 2)
rep["exit_time_diff_min_abs_p95"] = round(float(B.exit_diff_min.abs().quantile(.95)), 2)
rep["R_mt5_sum"] = round(float(B.R.sum()), 2); rep["R_py_sum"] = round(float(B.pyR.sum()), 2)
rep["R_diff_abs_median"] = round(float((B.R - B.pyR).abs().median()), 4); rep["R_diff_abs_p95"] = round(float((B.R - B.pyR).abs().quantile(.95)), 3)
rep["pnl_mt5"] = round(float(O.pnl.sum()), 2); rep["pnl_py_chain"] = round(float(py.net_money.sum()), 2)
rep["exp_R_mt5_all"] = round(float(O.R.mean()), 4); rep["exp_R_py_all"] = round(float(py.pyR.mean()), 4)
rep["py_skipped"] = info["skipped"]
# discrepancias no cubiertas por el emparejamiento
rep["mt5_not_in_py_dates"] = [str(x) for x in M[M._merge == "left_only"].bar.head(10)]
rep["py_not_in_mt5_dates"] = [str(x) for x in M[M._merge == "right_only"].bar.head(10)]
bad = B[(B.exit_reason_mt5 != B.reason_py) | ((B.R - B.pyR).abs() > 0.25)]
rep["n_R_diff_gt_0.25_or_reason_diff"] = len(bad)
out = B[["bar", "dir_mt5", "entry_mt5", "entry_py", "lots_mt5", "lots_py", "lots_py_with_mt5_balance", "exit_reason_mt5", "reason_py", "exit_mt5", "exit_py", "exit_diff_min", "R", "pyR", "pnl", "net_money"]]
out.to_csv(ROOT / "research/PARITY_S01_TRADES.csv", index=False)
(ROOT / "research/PARITY_S01_PYTHON_MT5.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
print(json.dumps(rep, indent=1, default=str))
print(bad[["bar", "dir_mt5", "exit_reason_mt5", "reason_py", "R", "pyR"]].head(15).to_string())

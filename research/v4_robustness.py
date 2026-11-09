"""Robustez basica de los informes oficiales: sin la mejor / sin las 5 mejores operaciones, por trimestre, y paridad Python-MT5 si existe."""
import csv
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
rows = []
for d in sorted((ROOT / "results" / "v4_runs").glob("RUN_*")):
    if not (d / "trades.csv").exists():
        continue
    t = pd.read_csv(d / "trades.csv", parse_dates=["open_time", "close_time"])
    t["net"] = t.profit + t.commission.fillna(0) + t.swap.fillna(0)
    s = t.sort_values("net", ascending=False)
    q = t.groupby(t.close_time.dt.to_period("Q")).net.sum()
    par = json.loads((d / "python_vs_mt5.json").read_text()) if (d / "python_vs_mt5.json").exists() else {}
    rows.append(dict(run_id=d.name, trades=len(t), net=round(t.net.sum(), 2), net_without_best=round(s.net.iloc[1:].sum(), 2), net_without_top5=round(s.net.iloc[5:].sum(), 2),
                     best_trade_share_of_gross_profit=round(float(s.net.iloc[0] / t.net[t.net > 0].sum()), 4), quarters_positive=int((q > 0).sum()), quarters_total=int(len(q)),
                     py_matched_entries=par.get("matched_entries"), py_trades=par.get("trades_py"), py_net=par.get("net_py"), py_same_lots=par.get("same_lots")))
with open(ROOT / "research" / "ROBUSTNESS_RESULTS.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for r in rows:
    print(r)

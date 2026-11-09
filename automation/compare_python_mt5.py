"""Compara las operaciones de un informe oficial MT5 (trades.csv del parser) con las esperadas por Python. Uso: <run_dir> <expected.csv>"""
import json
import sys
from pathlib import Path

import pandas as pd


def compare(run_dir: Path, expected: Path) -> dict:
    t = pd.read_csv(run_dir / "trades.csv", parse_dates=["open_time", "close_time"])
    e = pd.read_csv(expected, parse_dates=["entry_time", "exit_time"])
    t["dir"] = t["type"].map({"buy": 1, "sell": -1})
    t["net"] = t.profit + t.commission.fillna(0) + t.swap.fillna(0)
    m = t.merge(e, left_on=["open_time", "dir"], right_on=["entry_time", "dir"], how="outer", suffixes=("_mt5", "_py"), indicator=True)
    both = m[m._merge == "both"]
    res = dict(trades_mt5=len(t), trades_py=len(e), matched_entries=len(both), only_mt5=int((m._merge == "left_only").sum()), only_py=int((m._merge == "right_only").sum()),
               same_lots=int((both.lots_mt5 == both.lots_py).sum()), same_exit_time=int((both.close_time == both.exit_time).sum()),
               entry_price_maxdiff=float((both.price_open - both.entry).abs().max()) if len(both) else None,
               net_mt5=round(float(t.net.sum()), 2), net_py=round(float(e.net_money.sum()), 2),
               net_diff_matched=round(float(both.net.sum() - both.net_money.sum()), 2))
    m.to_csv(run_dir / "python_vs_mt5.csv", index=False)
    (run_dir / "python_vs_mt5.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    print(json.dumps(compare(Path(sys.argv[1]), Path(sys.argv[2])), indent=1))

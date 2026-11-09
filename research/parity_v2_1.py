"""Paridad de la corrida OFICIAL de V2.1 (Tester del usuario) con las operaciones esperadas de Python (results/v2_1_expected)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research")); sys.path.insert(0, str(ROOT))
import parity_v2_l2 as P  # noqa: E402

P.DEALS = ROOT / "results/v2_1_official/REMIX_V21_deals_M05_EURUSDm_PERIOD_H4.csv"
P.SIGS = ROOT / "results/v2_1_official/REMIX_V21_signals_M05_EURUSDm_PERIOD_H4.csv"
def load_deals_only():
    d = pd.read_csv(P.DEALS); d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S")
    ins, outs = d[d.entry == 0].reset_index(drop=True), d[d.entry == 1].reset_index(drop=True)
    t = pd.DataFrame({"entry_time": ins.time, "dir": np.where(ins.type == 0, 1, -1), "lots": ins.volume, "entry": ins.price, "exit_time": outs.time, "exit": outs.price, "profit": outs.profit, "swap": outs.swap, "comment": outs.comment.fillna("")})
    t["reason"] = np.where(t.comment.str.startswith("sl"), "sl", np.where(t.comment.str.startswith("tp"), "tp", "max_bars")); t["net"] = t.profit + t.swap
    return t


off = load_deals_only()   # el log de senales es acumulativo entre corridas (modo append): no se usa para emparejar
exp = pd.read_csv(ROOT / "results/v2_1_expected/V2_1_S05_L2_H4_expected_trades.csv", parse_dates=["entry_time", "exit_time"])
J = off.merge(exp, on="entry_time", how="outer", suffixes=("_mt5", "_py"), indicator=True)
b = J[J._merge == "both"]
res = dict(n_mt5=len(off), n_py=len(exp), matched=len(b), only_mt5=int((J._merge == "left_only").sum()), only_py=int((J._merge == "right_only").sum()),
           dir_equal=int((b.dir_mt5 == b.dir_py).sum()), lots_equal=int((b.lots_mt5 == b.lots_py).sum()), entry_exact=int(((b.entry_mt5 - b.entry_py).abs() < 1e-9).sum()),
           reason_equal=int((b.reason == b.exit_reason.map({"sl": "sl", "sl_gap": "sl", "tp": "tp", "max_bars": "max_bars"})).sum()),
           exit_bucket_equal=int((pd.to_datetime(b.exit_time_mt5).dt.floor("4h") == pd.to_datetime(b.exit_time_py).dt.floor("4h")).sum()),
           net_mt5=round(float(off.net.sum()), 2), net_py=round(float(exp.net_money.sum()), 2), swap_mt5=round(float(off.swap.sum()), 2), swap_py=round(float(exp.swap.sum()), 2))
# concentracion del beneficio
pos = off.net[off.net > 0].sort_values(ascending=False)
res["best_trade_share_of_net_pct"] = round(float(pos.iloc[0] / off.net.sum() * 100), 1) if off.net.sum() > 0 else None
res["best_trade"] = {"entry": str(off.loc[off.net.idxmax(), "entry_time"]), "net": round(float(off.net.max()), 2)}
res["net_without_best"] = round(float(off.net.sum() - off.net.max()), 2)
res["net_without_best5"] = round(float(off.net.sum() - off.net.sort_values().iloc[-5:].sum()), 2)
res["by_year_net"] = off.groupby(off.entry_time.dt.year).net.agg(["count", "sum"]).round(2).to_dict()
(ROOT / "research/PARITY_V2_1_OFFICIAL.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
J.to_csv(ROOT / "research/PARITY_V2_1_TRADES.csv", index=False)
print(json.dumps(res, indent=1, default=str))
print(J[J._merge != "both"][["entry_time", "dir_mt5", "dir_py", "_merge"]])


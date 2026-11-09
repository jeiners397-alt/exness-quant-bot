"""Auditoria de las 335 operaciones oficiales de S01 (T-OFICIAL, 3000 USD).
Fuentes: export de deals del EA (comentarios sl/tp reales) + barras M15 locales.
No inventa valores: R se calcula con SL = rango asiatico x1 (regla del EA), verificado contra las perdidas SL.
Salida: research/S01_TRADES_RECONSTRUCTED.csv y research/S01_AUDIT_STATS.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = pd.read_csv(ROOT / "results/s01_official/REMIX_deals_S01_EURUSDm_PERIOD_M15.csv")
D["time"] = pd.to_datetime(D["time"], format="%Y.%m.%d %H:%M:%S")
ins = D[D.entry == 0].reset_index(drop=True)
outs = D[D.entry == 1].reset_index(drop=True)
assert len(ins) == len(outs) == 335
T = pd.DataFrame({
    "open_time": ins.time, "close_time": outs.time, "dir": np.where(ins.type == 0, 1, -1),
    "lots": ins.volume, "entry": ins.price, "exit": outs.price, "pnl": outs.profit + outs.commission + outs.swap,
    "exit_comment": outs.comment.fillna(""),
})
assert (T.close_time > T.open_time).all() and (T.open_time.iloc[1:].values >= T.close_time.iloc[:-1].values).all()  # sin solape
T["exit_reason"] = np.where(T.exit_comment.str.startswith("sl"), "SL", np.where(T.exit_comment.str.startswith("tp"), "TP", "TIME"))
T["exit_hour_ok_time"] = T.close_time.dt.hour >= 17
# SL/TP de la comision de comentario
T["exit_level_comment"] = pd.to_numeric(T.exit_comment.str.extract(r"([0-9.]+)")[0], errors="coerce")

# Rango asiatico del dia (hora servidor 00-07) desde M15 local
M = pd.read_csv(ROOT / "data/raw/EURUSDm_M15.csv", parse_dates=["time"])
M["date"] = M.time.dt.normalize()
asia = M[(M.time.dt.hour >= 0) & (M.time.dt.hour < 7)].groupby("date").agg(rh=("high", "max"), rl=("low", "min"))
T["date"] = T.open_time.dt.normalize()
T = T.join(asia, on="date")
T["width"] = T.rh - T.rl
T["sl_dist"] = T.width            # SL = rango x 1
T["tp_dist"] = T.width * 1.5
T["risk_usd"] = T.lots * 100000 * T.sl_dist
T["R"] = T.pnl / T.risk_usd
T["balance_before"] = 3000 + T.pnl.cumsum().shift(fill_value=0)
T["risk_pct_real"] = 100 * T.risk_usd / T.balance_before
T["dur_h"] = (T.close_time - T.open_time).dt.total_seconds() / 3600
T["quarter"] = T.open_time.dt.to_period("Q").astype(str)
T["entry_hour"] = T.open_time.dt.hour
T["width_pips"] = T.width * 1e4

# Verificaciones
sl = T[T.exit_reason == "SL"]
tp = T[T.exit_reason == "TP"]
tm = T[T.exit_reason == "TIME"]
chk = {
    "n_trades": int(len(T)),
    "pnl_total": round(float(T.pnl.sum()), 2),
    "time_exits_all_after_17h": bool(tm.exit_hour_ok_time.all()),
    "time_exit_close_clock_min_max": [str(tm.close_time.dt.time.min()), str(tm.close_time.dt.time.max())],
    "sl_exits_with_close_time_ge_17h": int((sl.close_time.dt.hour >= 17).sum()),
    "tp_exits_with_close_time_ge_17h": int((tp.close_time.dt.hour >= 17).sum()),
    "sl_R_median": round(float(sl.R.median()), 3), "sl_R_p5_p95": [round(float(sl.R.quantile(.05)), 3), round(float(sl.R.quantile(.95)), 3)],
    "tp_R_median": round(float(tp.R.median()), 3), "tp_R_p5_p95": [round(float(tp.R.quantile(.05)), 3), round(float(tp.R.quantile(.95)), 3)],
    "risk_pct_real_median": round(float(T.risk_pct_real.median()), 3),
    "risk_pct_real_min_max": [round(float(T.risk_pct_real.min()), 3), round(float(T.risk_pct_real.max()), 3)],
    "n_lot_min_0.01": int((T.lots == 0.01).sum()),
    "n_risk_over_0.6pct": int((T.risk_pct_real > 0.6).sum()),
    "commission_swap_nonzero": int(((outs.commission != 0) | (outs.swap != 0)).sum()),
}


def agg(g):
    n = len(g)
    r = g.R
    gp, gl = g.pnl[g.pnl > 0].sum(), -g.pnl[g.pnl < 0].sum()
    return pd.Series({"n": n, "wins": int((g.pnl > 0).sum()), "wr": round((g.pnl > 0).mean() * 100, 1), "pnl": round(g.pnl.sum(), 2),
                      "pf": round(gp / gl, 3) if gl > 0 else np.nan, "exp_R": round(r.mean(), 4), "avg_R": round(r.mean(), 4),
                      "sum_R": round(r.sum(), 2), "avg_dur_h": round(g.dur_h.mean(), 2)})


def table(by):
    return T.groupby(by).apply(agg, include_groups=False).reset_index().to_dict("records")


stats = {"checks": chk,
         "by_exit": table("exit_reason"), "by_dir": table("dir"), "by_quarter": table("quarter"),
         "by_dir_exit": table(["dir", "exit_reason"]), "by_entry_hour": table("entry_hour")}
T["width_bucket"] = pd.qcut(T.width_pips, 4, labels=["Q1 estrecho", "Q2", "Q3", "Q4 ancho"])
stats["by_width_quartile"] = table("width_bucket")
stats["width_pips_quartile_edges"] = [round(x, 1) for x in T.width_pips.quantile([0, .25, .5, .75, 1])]
T["loss_window"] = np.where(T.quarter.isin(["2025Q4", "2026Q1"]), "2025Q4+2026Q1", "resto")
stats["by_loss_window"] = table("loss_window")
stats["by_loss_window_exit"] = table(["loss_window", "exit_reason"])
stats["by_loss_window_dir"] = table(["loss_window", "dir"])

# Descomposicion matematica
tpsl = T[T.exit_reason != "SL"]
n_tp, n_sl, n_tm = len(tp), len(sl), len(tm)
stats["decomp"] = {
    "p_tp_among_tp_sl": round(n_tp / (n_tp + n_sl), 4), "breakeven_p_for_RR1.5": 0.4,
    "R_tp_mean": round(float(tp.R.mean()), 3), "R_sl_mean": round(float(sl.R.mean()), 3), "R_time_mean": round(float(tm.R.mean()), 3),
    "time_share": round(n_tm / len(T), 3), "time_wins": int((tm.pnl > 0).sum()), "time_pnl": round(float(tm.pnl.sum()), 2),
    "tp_sl_pnl": round(float(tp.pnl.sum() + sl.pnl.sum()), 2),
}

# Significancia: expectativa en R (bootstrap por bloques de 10) y t
rng = np.random.default_rng(12345)
R = T.R.values
boots = []
for _ in range(5000):
    idx = rng.integers(0, len(R) - 9, size=len(R) // 10 + 1)
    s = np.concatenate([R[i:i + 10] for i in idx])[:len(R)]
    boots.append(s.mean())
se = R.std(ddof=1) / np.sqrt(len(R))
stats["significance"] = {"exp_R": round(float(R.mean()), 4), "std_R": round(float(R.std(ddof=1)), 3), "t_stat": round(float(R.mean() / se), 3),
                         "boot_block10_ci95_exp_R": [round(float(np.percentile(boots, 2.5)), 4), round(float(np.percentile(boots, 97.5)), 4)],
                         "top1_trade_share_of_gross_profit": round(float(T.pnl.max() / T.pnl[T.pnl > 0].sum()), 4),
                         "pnl_without_best_5": round(float(T.pnl.sort_values().iloc[:-5].sum()), 2),
                         "n_trials_note": "1 hipotesis predefinida (S01 canonico); no hay seleccion de parametros"}
(ROOT / "research/S01_AUDIT_STATS.json").write_text(json.dumps(stats, indent=1, default=str), encoding="utf-8")
T.drop(columns=["exit_hour_ok_time", "balance_before"]).to_csv(ROOT / "research/S01_TRADES_RECONSTRUCTED.csv", index=False)
print(json.dumps({k: stats[k] for k in ("checks", "decomp", "significance")}, indent=1, default=str))
for k in ("by_exit", "by_dir", "by_quarter", "by_width_quartile", "by_loss_window_exit", "by_loss_window_dir"):
    print(k); print(pd.DataFrame(stats[k]).to_string(index=False))

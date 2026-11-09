"""Compara las ejecuciones oficiales de la matriz multimercado: robustez por operaciones (R proxy = neto / |perdida media|), control de inversion de signos,
bootstrap por bloques, dependencia de operaciones extremas, estabilidad trimestral y corte temporal. Escribe STRATEGY_RANKING.csv y ROBUSTNESS_RESULTS.csv.
Correccion por multiples pruebas: umbral t* = sqrt(2 ln N) con N = numero de ejecuciones de la matriz (+ pruebas de eventos)."""
from __future__ import annotations

import csv
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
rng = np.random.default_rng(20261109)
M = pd.read_csv(ROOT / "research" / "MULTI_MARKET_STRATEGY_MATRIX.csv")
N = len(M)
tstar = float(np.sqrt(2 * np.log(max(N, 2))))
rows = []
for _, r in M.iterrows():
    tp = ROOT / r.report_path.replace("report.htm", "trades.csv")
    base = dict(run_id=r.run_id, strategy=r.strategy, symbol=r.symbol, category=r.category, timeframe=r.timeframe, trades=r.trades, net_profit=r.net_profit,
                profit_factor=r.profit_factor, expectancy_R_proxy=r.expectancy_R_proxy, max_dd_pct=r.max_dd_equity_pct)
    if r.trades < 30 or not tp.exists():
        rows.append(dict(base, note="n<30 o sin trades.csv: no se evalua robustez")); continue
    t = pd.read_csv(tp, parse_dates=["close_time"])
    net = (t.profit + t.commission.fillna(0) + t.swap.fillna(0)).values
    loss = net[net < 0]
    if len(loss) == 0:
        rows.append(dict(base, note="sin perdidas")); continue
    R = net / abs(loss.mean())
    n = len(R)
    tval = R.mean() / (R.std(ddof=1) / np.sqrt(n))
    flips = np.array([(R * rng.choice([-1, 1], size=n)).mean() for _ in range(5000)])
    p_flip = float((flips >= R.mean()).mean())
    blk = 20
    nb = int(np.ceil(n / blk))
    bs = []
    for _ in range(2000):
        st = rng.integers(0, max(1, n - blk), size=nb)
        bs.append(np.concatenate([R[s:s + blk] for s in st])[:n].mean())
    lo, hi = np.percentile(bs, [2.5, 97.5])
    s = np.sort(net)[::-1]
    q = pd.Series(net, index=t.close_time).groupby(pd.Series(net, index=t.close_time).index.to_period("Q")).sum()
    mid = t.close_time.sort_values().iloc[n // 2]
    h1, h2 = net[(t.close_time <= mid).values].sum(), net[(t.close_time > mid).values].sum()
    rows.append(dict(base, R_mean=round(float(R.mean()), 4), t_stat=round(float(tval), 2), p_signflip=round(p_flip, 4), boot_ci_lo=round(float(lo), 4), boot_ci_hi=round(float(hi), 4),
                     net_without_best=round(float(s[1:].sum()), 2), net_without_top5=round(float(s[5:].sum()), 2), best_share_gross_profit=round(float(s[0] / net[net > 0].sum()), 4),
                     quarters_positive=int((q > 0).sum()), quarters_total=int(len(q)), first_half_net=round(float(h1), 2), second_half_net=round(float(h2), 2),
                     passes_multiplicity=bool(tval > tstar and p_flip < 0.01), note=""))
ro = pd.DataFrame(rows)
old = ROOT / "research" / "ROBUSTNESS_RESULTS.csv"
if old.exists() and not (ROOT / "research" / "ROBUSTNESS_RESULTS_V4.csv").exists():
    shutil.copy(old, ROOT / "research" / "ROBUSTNESS_RESULTS_V4.csv")
oldr = ROOT / "research" / "STRATEGY_RANKING.csv"
if oldr.exists() and not (ROOT / "research" / "STRATEGY_RANKING_V4.csv").exists():
    shutil.copy(oldr, ROOT / "research" / "STRATEGY_RANKING_V4.csv")
ro.to_csv(ROOT / "research" / "ROBUSTNESS_RESULTS.csv", index=False)
rk = ro.copy()
rk["rank_key"] = rk.R_mean.fillna(-9)
rk = rk.sort_values("rank_key", ascending=False).reset_index(drop=True)
rk["rank"] = rk.index + 1
rk["verdict"] = np.where(rk.passes_multiplicity == True, "CANDIDATO (requiere validacion fuera de muestra)",
                 np.where(rk.R_mean.fillna(-9) > 0, "positivo sin significacion tras multiples pruebas", "sin ventaja"))
rk[["rank", "run_id", "strategy", "symbol", "category", "timeframe", "trades", "net_profit", "profit_factor", "R_mean", "t_stat", "p_signflip", "boot_ci_lo", "boot_ci_hi", "verdict"]].to_csv(
    ROOT / "research" / "STRATEGY_RANKING.csv", index=False)
print(f"{N} ejecuciones; t* Bonferroni = {tstar:.2f}; positivas (R>0): {(ro.R_mean > 0).sum()}; pasan multiplicidad: {int((ro.passes_multiplicity == True).sum())}")
print(rk.head(8)[["rank", "strategy", "symbol", "timeframe", "trades", "net_profit", "R_mean", "t_stat", "p_signflip", "verdict"]].to_string())

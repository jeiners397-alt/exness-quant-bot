"""Tablas auxiliares V7: MT5 oficial (recuperado de V5, sin repetir pruebas), forward temporal (IS->OOS) y correlaciones de cartera."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "research"
M = pd.read_csv(R / "MULTI_MARKET_STRATEGY_MATRIX.csv")
keep = [c for c in ["run_id", "strategy", "symbol", "timeframe", "from_date", "to_date", "capital", "model", "trades", "net_profit", "return_pct", "profit_factor", "win_rate_pct", "expectancy_R_proxy",
                    "max_dd_equity_pct", "max_margin_pct_symbol", "sharpe", "class", "status", "report_html"] if c in M.columns]
O = M[keep].copy()
O.insert(0, "origen", "RECUPERADO_V5 (informe oficial MT5 local; no se repite). V7 lote 1 no genero estrategia candidata => 0 backtests nuevos")
O.to_csv(R / "V7_MT5_OFFICIAL_RESULTS.csv", index=False)

parts = []
for suf in ("", "_H1"):
    f = R / f"V7_ROBUSTNESS_RESULTS{suf}.csv"
    if f.exists():
        t = pd.read_csv(f); t.insert(0, "timeframe", "M15" if not suf else "H1"); parts.append(t)
if parts:
    T = pd.concat(parts)
    cols = ["timeframe", "symbol", "event", "variant", "rr", "n_is", "expR_is", "t_is", "n_oos", "expR_oos", "t_oos", "ci_oos_lo", "ci_oos_hi", "expR_oos_cost1p5", "expR_oos_cost2", "class"]
    top = T.sort_values("t_oos", ascending=False).head(60)[cols].copy()
    top.insert(0, "nota", "forward temporal IS(<2025-07)->OOS(>=2025-07) con reglas fijas; OOS ya visto en V4/V5 => no independiente; top 60 por t_oos (seleccion post-hoc, NO validacion)")
    top.to_csv(R / "V7_FORWARD_RESULTS.csv", index=False)

S = ["EURUSDm", "GBPUSDm", "USDJPYm", "XAUUSDm", "XAGUSDm", "US30m", "US500m", "USTECm", "BTCUSDm", "ETHUSDm"]
ret = {}
for s in S:
    d = pd.read_csv(ROOT / "data" / "raw" / "v7" / f"{s}_M15.csv", parse_dates=["time"])
    ret[s] = np.log(d.set_index("time").close.resample("1D").last().dropna()).diff()
Rt = pd.DataFrame(ret).dropna(how="all")
C = Rt.corr(min_periods=100)
rows = []
for i, a in enumerate(S):
    for b in S[i + 1:]:
        x = Rt[[a, b]].dropna()
        neg = (x[a] < -x[a].std()) & (x[b] < -x[b].std())
        rows.append(dict(a=a, b=b, corr_daily=round(C.loc[a, b], 3), n_days=len(x), p_joint_big_loss=round(float(neg.mean()), 4), p_joint_if_indep=round(float((x[a] < -x[a].std()).mean() * (x[b] < -x[b].std()).mean()), 4)))
P = pd.DataFrame(rows)
P.insert(0, "nota", "correlacion de retornos diarios de los MERCADOS (no de estrategias: no hay estrategia candidata para combinar). Perdida conjunta = ambos < -1 sigma")
P.to_csv(R / "V7_PORTFOLIO_ANALYSIS.csv", index=False)
print(P.sort_values("corr_daily", ascending=False).head(6)[["a", "b", "corr_daily"]].to_string())
print(P.sort_values("corr_daily").head(3)[["a", "b", "corr_daily"]].to_string())

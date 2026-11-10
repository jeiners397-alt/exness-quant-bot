"""Seleccion pre-declarada de candidatos V7 lote 1 a partir de V7_ENTRY_ANALYSIS.csv (IS -> OOS) + registro de TODAS las pruebas + robustez de costes."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "research"
import os
SUF = "" if os.environ.get("V7_TF", "M15") == "M15" else "_" + os.environ["V7_TF"]
E = pd.read_csv(R / f"V7_ENTRY_ANALYSIS{SUF}.csv")
RRS = [0.5, 1.0, 1.5, 2.0, 3.0]
rows = []
for (s, ev, var), g in E.groupby(["symbol", "event", "variant"]):
    IS, OOS = g[g.split == "IS"], g[g.split == "OOS"]
    if IS.empty or OOS.empty: continue
    IS, OOS = IS.iloc[0], OOS.iloc[0]
    for k in RRS:
        rows.append(dict(symbol=s, event=ev, variant=var, rr=k, n_is=int(IS.n), n_oos=int(OOS.n), expR_is=IS[f"expR_net_{k}R"], t_is=IS[f"t_{k}R"], expR_oos=OOS[f"expR_net_{k}R"], t_oos=OOS[f"t_{k}R"],
                         hit_is=IS[f"p_hit_{k}R"], hit_oos=OOS[f"p_hit_{k}R"], cost_ATR=IS.mean_cost_ATR, expR_gross_is=IS[f"expR_net_{k}R"] + IS.mean_cost_ATR,
                         p_ctrl_is=IS.get("p_vs_control"), p_ctrl_oos=OOS.get("p_vs_control"),
                         expR_oos_cost1p5=OOS[f"expR_net_{k}R"] - 0.5 * OOS.mean_cost_ATR, expR_oos_cost2=OOS[f"expR_net_{k}R"] - 1.0 * OOS.mean_cost_ATR,
                         expR_oos_cost3=OOS[f"expR_net_{k}R"] - 2.0 * OOS.mean_cost_ATR, ci_oos_lo=OOS[f"ci95_lo_{k}R"], ci_oos_hi=OOS[f"ci95_hi_{k}R"]))
T = pd.DataFrame(rows)
N = len(T); tstar = math.sqrt(2 * math.log(N))
T["N_tests"] = N; T["t_star_multiplicity"] = round(tstar, 2)
T["is_candidate"] = (T.expR_is > 0) & (T.t_is >= 2.0) & (T.n_is >= 100)
T["oos_confirms"] = T.is_candidate & (T.expR_oos > 0) & (T.t_oos >= 1.65) & (T.n_oos >= 50)
T["passes_multiplicity_is"] = T.t_is >= tstar
T["robust_cost1p5"] = T.expR_oos_cost1p5 > 0
T["oos_ci_excludes_0"] = T.ci_oos_lo > 0


def cls(r):
    if r.n_is < 100 or r.n_oos < 50: return "F"
    if r.oos_confirms and r.passes_multiplicity_is and r.robust_cost1p5 and r.oos_ci_excludes_0: return "B"      # A requiere datos independientes (no existen)
    if r.oos_confirms: return "C"
    if r.expR_is <= 0 and r.expR_oos <= 0: return "D"
    if r.is_candidate and r.expR_oos <= 0: return "G"                       # positivo en IS, no sobrevive a OOS => sobreajuste/azar
    return "C"


T["class"] = T.apply(cls, axis=1)
T.to_csv(R / f"V7_ROBUSTNESS_RESULTS{SUF}.csv", index=False)
cand = T[T.is_candidate | (T["class"] == "B")].sort_values(["oos_confirms", "t_oos"], ascending=False)
cand.to_csv(R / f"V7_STRATEGY_CANDIDATES{SUF}.csv", index=False)
reg = T[["symbol", "event", "variant", "rr"]].copy()
reg.insert(0, "exp_id", [f"V7B{1 if not SUF else 2}-{i:04d}" for i in range(1, len(reg) + 1)])
reg["family"] = reg.event; reg["timeframe"] = os.environ.get("V7_TF", "M15"); reg["data_window"] = "2024-01..2026-10 (IS<2025-07, OOS>=2025-07; ya visto en V4/V5)"
reg["status"] = "DONE"; reg["decision"] = T["class"].values; reg["justification"] = "lote 1 V7: estudio de eventos pre-declarado (12 familias x 2 sentidos x 5 RR x 10 mercados)"
reg.to_csv(R / f"V7_EXPERIMENT_REGISTER{SUF}.csv", index=False)
print("N tests", N, "t*", round(tstar, 2))
print(T["class"].value_counts().to_string())
print("candidatos IS:", int(T.is_candidate.sum()), "confirmados OOS:", int(T.oos_confirms.sum()), "pasan multiplicidad IS:", int(T.passes_multiplicity_is.sum()))
print(cand.head(15)[["symbol", "event", "variant", "rr", "n_is", "expR_is", "t_is", "n_oos", "expR_oos", "t_oos", "class"]].to_string())
print("mejor t_is global:", T.t_is.max(), "| mejor t_oos entre cand:", cand.t_oos.max() if len(cand) else None)
print("fraccion expR_is>0:", round((T.expR_is > 0).mean(), 3), "| fraccion expR_oos>0:", round((T.expR_oos > 0).mean(), 3), "| gross_is>0:", round((T.expR_gross_is > 0).mean(), 3))


"""FASE 4: matriz comparativa S01-S04 (canonica) con descomposicion bruto/costes y clasificacion (FASE 5). Exploratorio."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
Mx = pd.read_csv(ROOT / "research/PHASE3_MATRIX.csv")
Rn = pd.read_csv(ROOT / "research/PHASE3_RUNS.csv")
meta = json.loads((ROOT / "research/PHASE3_META.json").read_text())
rows = []
for r in Mx.itertuples():
    tr = pd.read_csv(ROOT / f"results/phase3_trades_{r.strategy}_{r.tf}.csv")
    cost_R = ((tr.spread_cost - tr.swap) / (tr.lots * 100000 * tr.sl_dist))
    gross = tr.net_r + cost_R
    neigh = Rn[(Rn.strategy == r.strategy) & (Rn.tf == r.tf) & (Rn.variant != "canonica")]
    rows.append({"strategy": r.strategy, "tf": r.tf, "n": r.n, "wr": r.wr, "pf": r.pf, "exp_R_net": r.exp_R, "exp_R_gross_before_costs": round(float(gross.mean()), 4),
                 "cost_R_per_trade": round(float(cost_R.mean()), 4), "ci95_expR": r.ci95_expR, "t": r.t, "net_usd": r.net_usd, "ret_pct": r.ret_pct,
                 "maxdd_pct": r.maxdd_pct, "recovery": r.recovery, "q_pos_of": f"{r.q_pos}/{r.q_total}", "expR_2025": r.exp_R_2025, "expR_2026": r.exp_R_2026,
                 "neigh_expR_min": neigh.exp_R.min() if len(neigh) else np.nan, "neigh_expR_max": neigh.exp_R.max() if len(neigh) else np.nan,
                 "neigh_positive": int((neigh.exp_R > 0).sum()) if len(neigh) else 0, "neigh_n": len(neigh),
                 "ctrl_mean": r.ctrl_expR_mean, "ctrl_p95": r.ctrl_expR_p95, "ctrl_p": r.ctrl_pvalue_expR})
D = pd.DataFrame(rows)


def classify(x):
    if x.strategy == "S01":
        return "Sin ventaja demostrada (referencia)"
    if x.exp_R_gross_before_costs <= 0.02 and x.exp_R_net < 0:
        return "Sin ventaja demostrada (bruto ~0, costes lo vuelven negativo)"
    return "Requiere investigacion"


D["clasificacion"] = D.apply(classify, axis=1)
D.to_csv(ROOT / "research/PHASE4_COMPARISON_MATRIX.csv", index=False)
print(D.drop(columns=["clasificacion"]).to_string(index=False))
print(meta)
print(D[["strategy", "tf", "clasificacion"]].to_string(index=False))

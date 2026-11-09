"""Seleccion PRE-REGISTRADA (solo TRAIN) y evaluacion en VALID y EXPL. No se mira VALID/EXPL para elegir.
Regla: por (hyp, tf, regime) se elige el k con mayor E_cons en TRAIN (n_TRAIN>=100). Supera si: E_cons>0 en TRAIN, VALID y EXPL (cota conservadora)
y el IC95 por bloques de VALID tiene limite inferior >0. 'Prometedora' ademas exige t_VALID >= t* (multiplicidad)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = pd.read_csv(ROOT / "research/PHASE_E_EVENT_STUDY.csv")
meta = json.loads((ROOT / "research/PHASE_E_META.json").read_text())
ncell = meta["n_cells"]; tstar = float(np.sqrt(2 * np.log(ncell)))
key = ["hyp", "tf", "regime"]
tr = R[(R.period == "TRAIN") & (R.n >= 100)]
pick = tr.loc[tr.groupby(key).E_cons.idxmax(), key + ["k"]]
rows = []
for r in pick.itertuples():
    row = dict(hyp=r.hyp, tf=r.tf, regime=r.regime, k=r.k)
    for per in ("TRAIN", "VALID", "EXPL"):
        s = R[(R.hyp == r.hyp) & (R.tf == r.tf) & (R.regime == r.regime) & (R.k == r.k) & (R.period == per)]
        if len(s):
            s = s.iloc[0]
            row.update({f"n_{per}": s.n, f"p_{per}": s.p_win_cons, f"pbe": s.p_breakeven_nocost, f"E_{per}": s.E_cons, f"Eopt_{per}": s.E_opt, f"lo_{per}": s.E_cons_ci_lo, f"hi_{per}": s.E_cons_ci_hi, f"t_{per}": s.t_cons, f"cost_{per}": s.cost_R})
    rows.append(row)
S = pd.DataFrame(rows)
S["pass_basic"] = (S.E_TRAIN > 0) & (S.E_VALID > 0) & (S.E_EXPL > 0) & (S.lo_VALID > 0)
S["promising"] = S.pass_basic & (S.t_VALID >= tstar)
S.to_csv(ROOT / "research/PHASE_E_SELECTION.csv", index=False)
print(f"celdas={ncell} t*={tstar:.2f}; grupos evaluados={len(S)}")
print("E_TRAIN>0:", int((S.E_TRAIN > 0).sum()), "| E_VALID>0 (de esos):", int(((S.E_TRAIN > 0) & (S.E_VALID > 0)).sum()), "| + E_EXPL>0:", int(((S.E_TRAIN > 0) & (S.E_VALID > 0) & (S.E_EXPL > 0)).sum()),
      "| pass_basic:", int(S.pass_basic.sum()), "| promising:", int(S.promising.sum()))
pd.set_option("display.width", 250)
print("mejores E_TRAIN y su destino fuera de muestra:")
print(S.sort_values("E_TRAIN", ascending=False)[["hyp", "tf", "regime", "k", "n_TRAIN", "E_TRAIN", "n_VALID", "E_VALID", "lo_VALID", "t_VALID", "n_EXPL", "E_EXPL"]].head(12).round(3).to_string(index=False))
print("correlacion E_TRAIN vs E_VALID:", round(float(S[["E_TRAIN", "E_VALID"]].corr().iloc[0, 1]), 3), " vs E_EXPL:", round(float(S[["E_TRAIN", "E_EXPL"]].corr().iloc[0, 1]), 3))
print("pass_basic:"); print(S[S.pass_basic][["hyp", "tf", "regime", "k", "n_TRAIN", "E_TRAIN", "n_VALID", "E_VALID", "lo_VALID", "t_VALID", "n_EXPL", "E_EXPL"]].round(3).to_string(index=False))
# probabilidades marginales de la hipotesis ejemplo (reversion tras |z|>=2) en todos los periodos y k
ex = R[(R.hyp == "A1_zrev_2.0") & (R.regime == "ALL")][["tf", "period", "k", "n", "p_win_cons", "p_ci_lo", "p_ci_hi", "p_win_opt", "p_breakeven_nocost", "E_cons", "E_opt", "cost_R", "mfe_med", "mae_med", "bars_med"]]
print(ex[ex.tf == "H1"].round(3).to_string(index=False)); print(ex[ex.tf == "H4"].round(3).to_string(index=False))
# promedio de E_cons por familia (marginal) en cada periodo
fam = R[(R.regime == "ALL") & (R.k == 1.0)].assign(fam=lambda d: d.hyp.str[:2]).groupby(["fam", "tf", "period"]).E_cons.mean().unstack().round(3)
print(fam.to_string())

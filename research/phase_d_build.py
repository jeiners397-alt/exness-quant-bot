"""FASE D: construye INVERSE / NEW / ROBUSTNESS y aplica reglas de decision PRE-REGISTRADAS (fijadas antes de ver resultados):
 Prometedora  : n>=100 en EXPL y RETRO; expR>0 en ambos; PF>=1.15 en ambos; expR sin 5 mejores >0 en ambos; ctrl_p<=0.10 en EXPL;
                >=50 % de las variantes del grupo (estrategia, tf) con expR>0 en ambos periodos; >=50 % de trimestres positivos en EXPL.
 No demostrada: expR>0 en EXPL pero incumple alguna condicion anterior.
 Descartada   : expR<=0 en EXPL.
 Pendiente de datos: n<30 en EXPL o RETRO.
Multiplicidad: N = configuraciones distintas probadas; t* = sqrt(2 ln N) (maximo esperable bajo azar)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = pd.read_csv(ROOT / "research/PHASE_D_ALL_RUNS.csv")
C = pd.read_csv(ROOT / "research/PHASE_D_COST_ANALYSIS.csv")
key = ["part", "strategy", "tf", "variant"]
E = R[R.period == "EXPL"].set_index(key)
T = R[R.period == "RETRO"].set_index(key)
j = E.join(T, rsuffix="_R", how="left")
N = len(E)
tstar = float(np.sqrt(2 * np.log(N)))
j["both_pos"] = (j.exp_R > 0) & (j.exp_R_R > 0)
grp = j.groupby(level=["part", "strategy", "tf"]).both_pos.mean().rename("group_stab")
j = j.join(grp, on=["part", "strategy", "tf"])


def decide(x):
    if not (x.n >= 30) or not (x.n_R >= 30):
        return "Pendiente de datos"
    if x.exp_R <= 0:
        return "Descartada"
    ok = (x.n >= 100 and x.n_R >= 100 and x.exp_R_R > 0 and x.pf >= 1.15 and x.pf_R >= 1.15 and x.exp_R_ex5 > 0 and x.exp_R_ex5_R > 0
          and x.ctrl_p <= 0.10 and x.group_stab >= 0.5 and x.q_pos / max(x.q_total, 1) >= 0.5)
    return "Prometedora" if ok else "No demostrada"


j["decision"] = j.apply(decide, axis=1)
j["t_vs_tstar"] = np.where(j.t >= tstar, "supera t*", "no supera t*")
j = j.reset_index()
j.to_csv(ROOT / "research/PHASE_D_JOINED.csv", index=False)
cols = ["part", "strategy", "tf", "variant", "n", "wr", "pf", "exp_R", "maxdd_pct", "ci_block", "t", "ctrl_p", "exp_R_R", "pf_R", "n_R", "t_R", "decision"]
inv = j[j.part == "INV"]; new = j[j.part == "NEW"]
inv[cols].to_csv(ROOT / "research/PHASE_D_INVERSE_STRATEGIES.csv", index=False)
new[cols].to_csv(ROOT / "research/PHASE_D_NEW_STRATEGIES.csv", index=False)
rb_cols = ["part", "strategy", "tf", "variant", "n", "exp_R", "exp_R_ex1", "exp_R_ex5", "pf", "pf_ex5", "top1_share", "payoff", "avg_win_R", "avg_loss_R", "max_consec_loss", "ci_block", "ci_boot",
           "q_pos", "q_total", "exp_R_h1", "exp_R_h2", "n_long", "exp_R_long", "n_short", "exp_R_short", "cost_R", "gross_R", "decision"]
rb = j[rb_cols].copy()
cc = C[C.period == "EXPL"][["strategy", "tf", "variant", "origin", "expR_stress", "expR_f05", "n_f05", "expR_f10", "n_f10"]]
rb = rb.merge(cc.drop(columns="origin"), on=["strategy", "tf", "variant"], how="left")
rb.to_csv(ROOT / "research/PHASE_D_ROBUSTNESS.csv", index=False)
print(f"configs distintas N={N}  t*={tstar:.2f}  ejecuciones totales={len(R)}")
print(j.groupby(["part", "decision"]).size())
print("-- mejores EXPL por exp_R (todas, para vigilar sesgo de seleccion):")
print(j.sort_values("exp_R", ascending=False)[["part", "strategy", "tf", "variant", "n", "pf", "exp_R", "t", "ctrl_p", "exp_R_R", "pf_R", "n_R", "exp_R_ex5", "decision"]].head(14).to_string(index=False))
print("-- exp_R positivo en ambos periodos:")
print(j[j.both_pos][["part", "strategy", "tf", "variant", "n", "pf", "exp_R", "t", "ctrl_p", "exp_R_R", "pf_R", "n_R", "decision"]].to_string(index=False))

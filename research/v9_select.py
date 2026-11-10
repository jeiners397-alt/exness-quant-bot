"""V9 - seleccion con multiplicidad (DEV/SEL/VAL), clases, registro de experimentos y tablas descriptivas.
Regla de candidato (fijada ANTES de ver resultados): expR_DEV>0, t_DEV>=2, n_DEV>=200 ; confirmacion SEL: expR>0, t>=1.65, n>=200.
Clase B: ademas t_DEV >= sqrt(2 ln N), expR_SEL a coste x1.5 > 0 y IC95 SEL excluye 0. Clase A: B + VAL (evaluada UNA vez, despues de congelar la seleccion): expR>0, t>=2, n>=100.
C: evidencia insuficiente/parcial; D: expectativa negativa; F: datos insuficientes (n_DEV<200 o n_SEL<200 en la regla); G: signo inestable DEV->SEL."""
from __future__ import annotations

import glob
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "research"
RRS = [0.5, 1.0, 1.5, 2.0, 3.0]


def table() -> pd.DataFrame:
    E = pd.concat([pd.read_csv(f) for f in glob.glob(str(ROOT / "results" / "v9" / "events_*_M*.csv"))])
    keys = ["symbol", "tf", "family", "variant"]
    out = []
    for k, g in E.groupby(keys):
        S = {r["split"]: r for r in g.to_dict("records")}
        for rr in RRS:
            row = dict(zip(keys, k), rr=rr)
            for sp in ("DEV", "SEL", "VAL", "ALL"):
                r = S.get(sp, {})
                row.update({f"n_{sp}": r.get("n", 0), f"expR_{sp}": r.get(f"expR_net_{rr}R", np.nan), f"t_{sp}": r.get(f"t_{rr}R", np.nan), f"ci_lo_{sp}": r.get(f"ci95_lo_{rr}R", np.nan), f"ci_hi_{sp}": r.get(f"ci95_hi_{rr}R", np.nan)})
            a = S.get("ALL", {})
            row["cost_ATR"] = a.get("mean_cost_ATR", np.nan); row["expR_gross_ALL_1p5"] = a.get("expR_gross_1.5R", np.nan)
            row["control_R1p5_ALL"] = a.get("control_mean_R1.5", np.nan); row["t_vs_control_ALL"] = a.get("t_vs_control", np.nan); row["events_per_day"] = a.get("events_per_day", np.nan)
            out.append(row)
    R = pd.DataFrame(out)
    N = len(R); ts = math.sqrt(2 * math.log(N))
    R["N_tests"] = N; R["t_star"] = round(ts, 2)
    for c, m in (("1p5", 0.5), ("2", 1.0), ("3", 2.0)):
        R[f"expR_SEL_cost{c}"] = R.expR_SEL - m * R.cost_ATR
        R[f"expR_ALL_cost{c}"] = R.expR_ALL - m * R.cost_ATR

    def cls(r):
        if r.n_DEV < 200 or r.n_SEL < 200:
            return "F"
        cand = r.expR_DEV > 0 and r.t_DEV >= 2
        if not cand:
            return "D" if (r.expR_ALL <= 0 or r.expR_DEV <= 0) else "C"
        if not (r.expR_SEL > 0 and r.t_SEL >= 1.65):
            return "G" if r.expR_SEL <= 0 else "C"
        if r.t_DEV >= ts and r.expR_SEL_cost1p5 > 0 and r.ci_lo_SEL > 0:
            if r.n_VAL >= 100 and r.expR_VAL > 0 and r.t_VAL >= 2:
                return "A"
            return "B"
        return "C"
    R["class"] = R.apply(cls, axis=1)
    return R


def main():
    R = table()
    R.to_csv(RES / "V9_ROBUSTNESS_RESULTS.csv", index=False)
    cand = R[R["class"].isin(["A", "B", "C", "G"]) & (R.n_DEV >= 200)].sort_values("t_DEV", ascending=False)
    cand.head(200).to_csv(RES / "V9_STRATEGY_CANDIDATES.csv", index=False)
    reg = R[["symbol", "tf", "family", "variant", "rr", "n_ALL", "expR_ALL", "t_ALL", "class", "N_tests", "t_star"]].copy()
    reg.insert(0, "exp_id", [f"V9S_{i:05d}" for i in range(len(reg))])
    reg.insert(1, "tipo", "event_study_scalping")
    reg.to_csv(RES / "V9_EXPERIMENT_REGISTER.csv", index=False)
    print("N", len(R), "t*", R.t_star.iloc[0]); print(R.groupby(["tf", "symbol"])["class"].value_counts().unstack(fill_value=0).to_string())
    print("expR_ALL medio por familia/tf/RR1.5 (neto) y bruto:")
    x = R[R.rr == 1.5].groupby(["tf", "family"]).agg(net=("expR_ALL", "mean"), gross=("expR_gross_ALL_1p5", "mean"), cost=("cost_ATR", "mean"), n=("n_ALL", "mean")).round(3)
    print(x.to_string())
    print(R.sort_values("t_DEV", ascending=False).head(10)[["symbol", "tf", "family", "variant", "rr", "n_DEV", "expR_DEV", "t_DEV", "n_SEL", "expR_SEL", "t_SEL", "n_VAL", "expR_VAL", "class"]].to_string())


if __name__ == "__main__":
    main()

"""Comprobacion de las 4 pistas debiles (positivas en EXPL y RETRO) — NO es seleccion de parametros: configuraciones fijas, sin variaciones nuevas.
Entrega: control aleatorio tambien en RETRO, estabilidad por ano, estres de costes. Resultado -> PHASE_D_LEAD_CHECK.csv"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab import harness as H  # noqa: E402
from remix_lab.backtest import BacktestConfig, run_backtest  # noqa: E402
from remix_lab.strategies import generate  # noqa: E402
from remix_lab.strategies_d import GEN, transform  # noqa: E402

F = H.load_frames()
LEADS = {
    "L1 S03 H1 LONG-invertidas": ("H1", lambda df: transform(generate("S03", df, H.SPEC, {}), "long_inv", "mirror")),
    "L2 S05 H4 z2.0 filtro ADX": ("H4", lambda df: GEN["S05"](df, dict(z_th=2.0, trend_filter=True, max_bars=18))),
    "L3 S06 H4 RSI2 5/95": ("H4", lambda df: GEN["S06"](df, dict(rsi_lo=5, rsi_hi=95))),
    "L4 S08 H4 Keltner regimen": ("H4", lambda df: GEN["S08"](df, dict(confirm=False, regime=True, max_bars=12))),
}
rows, peryear = [], []
for name, (tf, fn) in LEADS.items():
    for per in ("EXPL", "RETRO"):
        df = F[per][tf]; sig = fn(df)
        r, tr = H.run(df, sig, dict(lead=name, period=per, tf=tf), n_ctrl=300)
        d2 = df.copy(); d2["spread"] *= 1.5
        t2, i2 = run_backtest(d2, sig, H.SPEC, BacktestConfig(H.CAP, H.RISK, "strict", 0.0, 10.0))
        r["expR_stress"] = round(float(t2.net_r.mean()), 4) if len(t2) else np.nan
        rows.append(r)
        if len(tr):
            y = tr.groupby(pd.to_datetime(tr.entry_time).dt.year).net_r.agg(["count", "mean"]).round(3)
            for yr, v in y.iterrows():
                peryear.append(dict(lead=name, period=per, year=int(yr), n=int(v["count"]), exp_R=float(v["mean"])))
        print(name, per, r["n"], r["exp_R"], r["pf"], r["t"], r.get("ctrl_p"), r["ci_block"], r["expR_stress"], flush=True)
R = pd.DataFrame(rows)
for c in ("ci_block", "ci_boot"):
    R[c] = R[c].astype(str)
R.to_csv(ROOT / "research/PHASE_D_LEAD_CHECK.csv", index=False)
Y = pd.DataFrame(peryear); Y.to_csv(ROOT / "research/PHASE_D_LEAD_CHECK_BY_YEAR.csv", index=False)
print(Y.pivot_table(index=["lead"], columns="year", values="exp_R").round(2).to_string())
print(Y.pivot_table(index=["lead"], columns="year", values="n").to_string())

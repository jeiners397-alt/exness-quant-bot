"""Fase 5 (optimizacion controlada, pequena): region de parametros de la reversion Z-score H4 (S05) en TRAIN/VALID/EXPL con el motor completo
(capital 3000, 0.5 %, estricto, Bid/Ask, swap). 2 filtros x 3 SL x 3 duraciones = 18 configuraciones; se reporta la REGION, no el maximo."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab import harness as H  # noqa: E402
from remix_lab.strategies_d import GEN, resample  # noqa: E402

F = H.load_frames()
H1 = pd.concat([F["RETRO"]["H1"], F["EXPL"]["H1"]]).reset_index(drop=True)
H4 = resample(H1, "H4")
PER = {"TRAIN": ("2018-01-01", "2022-01-01"), "VALID": ("2022-01-01", "2025-01-01"), "EXPL": ("2025-01-01", "2026-11-01")}
rows = []
for flt in (False, True):
    for sl in (1.5, 2.0, 3.0):
        for mb in (12, 18, 30):
            sig_all = GEN["S05"](H4, dict(z_th=2.0, trend_filter=flt, sl_atr=sl, max_bars=mb))
            for per, (a, b) in PER.items():
                m = ((H4.time >= a) & (H4.time < b)).to_numpy()
                df = H4[m].reset_index(drop=True)
                sub = type(sig_all)(sig_all.direction[m], sig_all.sl_dist[m], sig_all.tp_dist[m], None, mb)
                r, tr = H.run(df, sub, dict(adx_filter=flt, sl_atr=sl, max_bars=mb, period=per), with_control=False)
                rows.append({k: r.get(k) for k in ("adx_filter", "sl_atr", "max_bars", "period", "n", "wr", "pf", "exp_R", "t", "exp_R_ex5", "maxdd_pct", "cost_R", "gross_R")})
R = pd.DataFrame(rows)
R.to_csv(ROOT / "research/PHASE_E_PARAM_REGION.csv", index=False)
pd.set_option("display.width", 200)
print(R.pivot_table(index=["adx_filter", "sl_atr", "max_bars"], columns="period", values="exp_R")[["TRAIN", "VALID", "EXPL"]].round(3).to_string())
print(R.pivot_table(index=["adx_filter", "sl_atr", "max_bars"], columns="period", values="n")[["TRAIN", "VALID", "EXPL"]].to_string())
print("configs con exp_R>0 en los 3 periodos:", int((R.pivot_table(index=["adx_filter", "sl_atr", "max_bars"], columns="period", values="exp_R") > 0).all(axis=1).sum()), "de 18")

"""FASE D: senales inversas S02-S04 + S05-S12 + costes. EXPL (2025-01..2026-10, ya inspeccionado) y RETRO (anterior a 2025, no inspeccionado antes).
Reglas de decision fijadas ANTES de ver resultados (ver docs). Semilla 12345. Registro de TODAS las ejecuciones en PHASE_D_ALL_RUNS.csv."""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab import harness as H  # noqa: E402
from remix_lab.strategies import generate  # noqa: E402
from remix_lab.strategies_d import GEN, transform  # noqa: E402

PART = sys.argv[1] if len(sys.argv) > 1 else "all"
F = H.load_frames()
print("datos:", json.dumps(H.DATA_NOTES), {p: {k: len(v) for k, v in d.items()} for p, d in F.items()}, flush=True)
t0 = time.time()
rows, cost_rows = [], []
NC = 100


def log(r):
    print(f"[{time.time()-t0:5.0f}s] {r.get('part')} {r.get('strategy')} {r.get('period')} {r.get('tf')} {r.get('variant')}: n={r.get('n')} expR={r.get('exp_R')} pf={r.get('pf')} t={r.get('t')} ctrl_p={r.get('ctrl_p')}", flush=True)


# ---------------------------------------------------------------- I. inversion S02-S04
if PART in ("all", "inv"):
    VARS = [("A_orig", "orig", "mirror"), ("B_inv", "inv", "mirror"), ("B_inv_swap", "inv", "swap"), ("C_long", "long", "mirror"), ("D_short", "short", "mirror"),
            ("E_long_inv", "long_inv", "mirror"), ("E_long_inv_swap", "long_inv", "swap"), ("F_short_inv", "short_inv", "mirror"), ("F_short_inv_swap", "short_inv", "swap")]
    for per in ("EXPL", "RETRO"):
        for sid in ("S02", "S03", "S04"):
            for tf in ("M15", "H1"):
                df = F[per][tf]
                base = generate(sid, df, H.SPEC, {})              # parametros canonicos con su filtro de spread original (0.15 SL)
                for name, mode, geo in VARS:
                    sig = transform(base, mode, geo)
                    r, tr = H.run(df, sig, dict(part="INV", strategy=sid, period=per, tf=tf, variant=name), n_ctrl=NC)
                    rows.append(r); log(r)

# ---------------------------------------------------------------- II. nuevas estrategias
GRID = {
    "S05": [(tf, dict(z_th=z, trend_filter=f, max_bars=(48 if tf == "H1" else 18))) for tf in ("H1", "H4") for z in (2.0, 2.5) for f in (False, True)],
    "S06": [(tf, dict(rsi_lo=lo, rsi_hi=hi)) for tf in ("H1", "H4") for lo, hi in ((10, 90), (5, 95))],
    "S07": [(tf, dict(mode=m, retest_lb=(12 if tf == "M15" else 4))) for tf in ("M15", "H1") for m in ("breakout", "sweep", "retest")],
    "S08": [(tf, dict(confirm=c, regime=g, max_bars=(24 if tf == "H1" else 12))) for tf in ("H1", "H4") for c in (False, True) for g in (False, True)],
    "S09": [(tf, dict(mom_n=m, exit_mode=e)) for tf in ("H4", "D1") for m in (20, 60) for e in ("atr", "trend")],
    "S10": [(tf, dict(confirm=c, htf=h)) for tf in ("H1", "H4") for c in ("cross", "structure") for h in ((False, True) if tf == "H1" else (False,))],
    "S11": [(tf, dict(filt=f, max_bars=(24 if tf == "H1" else 12))) for tf in ("H1", "H4") for f in (False, True)],
    "S12": [("M15", dict(vwap_start=s)) for s in (0, 7)],
}
if PART in ("all", "new"):
    for per in ("EXPL", "RETRO"):
        for sid, grid in GRID.items():
            for tf, p in grid:
                df = F[per][tf]
                q = dict(p); use_htf = q.pop("htf", False)
                if sid == "S10":
                    sig = GEN[sid](df, q, F[per]["H4"] if use_htf else None, base_minutes=60)
                else:
                    sig = GEN[sid](df, q)
                lab = dict(part="NEW", strategy=sid, period=per, tf=tf, variant=json.dumps({**p}, sort_keys=True))
                r, tr = H.run(df, sig, lab, n_ctrl=NC, hours_from_signals=(sid in ("S07", "S12")))
                rows.append(r); log(r)
                if per == "EXPL":
                    cost_rows.append(H.cost_scenarios(df, sig, dict(strategy=sid, tf=tf, variant=lab["variant"], period=per, origin="NEW")))

# ---------------------------------------------------------------- III. costes de S02-S04 originales (sin filtro de spread propio)
if PART in ("all", "cost"):
    for per in ("EXPL", "RETRO"):
        for sid in ("S02", "S03", "S04"):
            for tf in ("M15", "H1"):
                df = F[per][tf]
                sig = generate(sid, df, H.SPEC, {"max_spread_frac": 10.0})
                cost_rows.append(H.cost_scenarios(df, sig, dict(strategy=sid, tf=tf, variant="canonica(sin filtro spread)", period=per, origin="ORIG")))
                print("cost", sid, per, tf, cost_rows[-1].get("expR_base"), cost_rows[-1].get("expR_f05"), cost_rows[-1].get("expR_f10"), flush=True)

R = pd.DataFrame(rows)
for c in ("ci_block", "ci_boot"):
    if c in R:
        R[c] = R[c].astype(str)
out = ROOT / "research"
tag = "" if PART == "all" else f"_{PART}"
R.to_csv(out / f"PHASE_D_ALL_RUNS{tag}.csv", index=False)
pd.DataFrame(cost_rows).to_csv(out / f"PHASE_D_COST_ANALYSIS{tag}.csv", index=False)
(out / f"PHASE_D_META{tag}.json").write_text(json.dumps({"n_runs": len(R), "data_notes": H.DATA_NOTES, "controls_per_run": NC, "capital": H.CAP, "risk_pct": H.RISK,
                                                          "policy": "strict", "seed": 12345, "elapsed_s": round(time.time() - t0)}, indent=1), encoding="utf-8")
print("FIN", len(R), "ejecuciones", round(time.time() - t0), "s")

"""Fase A (paridad V0 vs oficial) y Fase B (variantes de salida vs V0). Entradas fijas = 335 oficiales. Resolucion: barras M15 (conservador)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab.exit_variants import VARIANTS, Variant, prep_bars, run_variant  # noqa: E402

T = pd.read_csv(ROOT / "research/S01_TRADES_RECONSTRUCTED.csv", parse_dates=["open_time", "close_time"])
bars = prep_bars(pd.read_csv(ROOT / "data/raw/EURUSDm_M15.csv", parse_dates=["time"]))
rng = np.random.default_rng(12345)


def maxdd_R(r):
    c = np.cumsum(r); return float((np.maximum.accumulate(np.r_[0, c])[1:] - c).max())


def stats(R):
    R = np.asarray(R); w = R[R > 0].sum(); l = -R[R < 0].sum()
    return {"n": len(R), "wr": round(float((R > 0).mean() * 100), 1), "exp_R": round(float(R.mean()), 4), "sum_R": round(float(R.sum()), 2),
            "pf_R": round(float(w / l), 3) if l > 0 else np.nan, "maxdd_R": round(maxdd_R(R), 2), "std_R": round(float(R.std(ddof=1)), 3)}


def paired_ci(d, block=10, B=4000):
    d = np.asarray(d); m = len(d); bs = []
    for _ in range(B):
        ix = rng.integers(0, m - block + 1, size=m // block + 1)
        bs.append(np.concatenate([d[i:i + block] for i in ix])[:m].mean())
    se = d.std(ddof=1) / np.sqrt(m)
    return [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)], round(float(d.mean() / se), 2) if se > 0 else np.nan


res = {v.vid: run_variant(T, bars, v) for v in VARIANTS}
# ---------- Fase A: paridad V0 vs oficial
v0 = res["V0"]
agree = (v0.reason.values == T.exit_reason.values)
dR = v0.R.values - T.R.values
parity = {"reason_agreement": int(agree.sum()), "of": len(T), "pct": round(agree.mean() * 100, 1),
          "confusion(official->sim)": pd.crosstab(T.exit_reason, v0.reason).to_dict(),
          "R_diff_mean": round(float(dR.mean()), 4), "R_diff_abs_median": round(float(np.median(np.abs(dR))), 4),
          "sumR_official": round(float(T.R.sum()), 2), "sumR_sim": round(float(v0.R.sum()), 2),
          "exp_R_official": round(float(T.R.mean()), 4), "exp_R_sim": round(float(v0.R.mean()), 4)}
print("PARIDAD V0 (barras M15) vs oficial MT5:"); print(json.dumps(parity, indent=1, default=str))
# ---------- Fase B
rows, N = [], len(VARIANTS) - 1
base = v0.R.values
per2026 = (T.open_time >= "2026-01-01").values
for v in VARIANTS:
    r = res[v.vid].R.values
    s = stats(r)
    d = r - base
    if v.vid != "V0":
        ci, t = paired_ci(d)
        s.update({"delta_exp_R_vs_V0": round(float(d.mean()), 4), "delta_ci95_block": ci, "delta_t": t, "bonferroni_alpha": round(0.05 / N, 4),
                  "delta_2025": round(float(d[~per2026].mean()), 4), "delta_2026": round(float(d[per2026].mean()), 4),
                  "delta_long": round(float(d[T.dir.values == 1].mean()), 4), "delta_short": round(float(d[T.dir.values == -1].mean()), 4),
                  "improved_n": int((d > 1e-9).sum()), "worsened_n": int((d < -1e-9).sum())})
    s.update({"vid": v.vid, "desc": v.desc, "reasons": res[v.vid].reason.value_counts().to_dict()})
    rows.append(s)
out = pd.DataFrame(rows)
cols = ["vid", "n", "wr", "exp_R", "sum_R", "pf_R", "maxdd_R", "delta_exp_R_vs_V0", "delta_ci95_block", "delta_t", "delta_2025", "delta_2026", "delta_long", "delta_short", "improved_n", "worsened_n"]
print(out[cols].to_string(index=False))
print(out[["vid", "reasons"]].to_string(index=False))
# sensibilidad a slippage de 10 puntos en stops (V0 y mejores nominales)
sl_rows = []
for v in VARIANTS:
    vv = Variant(**{**v.__dict__, "slip_pts": 10.0}); r = run_variant(T, bars, vv).R.values
    sl_rows.append({"vid": v.vid, "exp_R_slip10pts": round(float(r.mean()), 4)})
print(pd.DataFrame(sl_rows).T.to_string(header=False))
out.to_csv(ROOT / "research/S01_EXIT_VARIANTS_RESULTS.csv", index=False)
pd.concat([res[k].assign(R_official=T.R.values) for k in res]).to_csv(ROOT / "research/S01_EXIT_VARIANTS_TRADES.csv", index=False)
(ROOT / "research/S01_EXIT_VARIANTS_PARITY.json").write_text(json.dumps({"parity": parity, "n_variants_tested": N, "resolution": "M15 bars conservative", "slip10": sl_rows}, indent=1, default=str), encoding="utf-8")

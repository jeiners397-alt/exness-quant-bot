"""FASE 1: variantes de salida con TICKS REALES (153 operaciones oficiales de 2026) + paridad de salidas V0 a nivel tick."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab.exit_variants import VARIANTS, Variant, prep_bars, run_variant  # noqa: E402
from remix_lab.tick_replay import run_variant_ticks  # noqa: E402

T = pd.read_csv(ROOT / "research/S01_TRADES_RECONSTRUCTED.csv", parse_dates=["open_time", "close_time"])
T = T[T.open_time >= "2026-01-02"].reset_index(drop=True)
bars = prep_bars(pd.read_csv(ROOT / "data/raw/EURUSDm_M15.csv", parse_dates=["time"]))
rng = np.random.default_rng(12345)


def ci_paired(d, block=10, B=4000):
    d = np.asarray(d); m = len(d); bs = []
    for _ in range(B):
        ix = rng.integers(0, m - block + 1, size=m // block + 1)
        bs.append(np.concatenate([d[i:i + block] for i in ix])[:m].mean())
    se = d.std(ddof=1) / np.sqrt(m)
    return [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)], round(float(d.mean() / se), 2) if se > 0 else np.nan


res = {v.vid: run_variant_ticks(T, bars, v) for v in VARIANTS}
bar = {v.vid: run_variant(T, bars, v) for v in VARIANTS}
v0 = res["V0"]
# paridad de salida V0 tick vs oficial
exit_t = pd.to_datetime(v0.exit_ms, unit="ms")
dt_s = (exit_t - T.close_time).dt.total_seconds()
par = {"n": len(T), "reason_agree": int((v0.reason.values == T.exit_reason.values).sum()),
       "exit_time_diff_s_median": float(dt_s.median()), "exit_time_diff_s_p95_abs": float(dt_s.abs().quantile(.95)), "exit_time_exact_pm2s": int((dt_s.abs() <= 2).sum()),
       "R_diff_mean": round(float((v0.R.values - T.R.values).mean()), 4), "R_diff_abs_median": round(float(np.median(np.abs(v0.R.values - T.R.values))), 4),
       "R_diff_abs_max": round(float(np.max(np.abs(v0.R.values - T.R.values))), 3),
       "sumR_official": round(float(T.R.sum()), 2), "sumR_tick_V0": round(float(v0.R.sum()), 2), "sumR_bar_V0": round(float(bar["V0"].R.sum()), 2)}
print("PARIDAD V0 ticks vs oficial (2026):", json.dumps(par, indent=1))
print(pd.crosstab(T.exit_reason, v0.reason))
rows, N = [], len(VARIANTS) - 1
base = v0.R.values
for v in VARIANTS:
    r = res[v.vid].R.values; rb = bar[v.vid].R.values
    s = {"vid": v.vid, "desc": v.desc, "n": len(r), "wr": round(float((r > 0).mean() * 100), 1), "exp_R_tick": round(float(r.mean()), 4), "sum_R_tick": round(float(r.sum()), 2),
         "exp_R_bar_same_subset": round(float(rb.mean()), 4)}
    if v.vid != "V0":
        d = r - base; ci, t = ci_paired(d)
        s.update({"delta_vs_V0": round(float(d.mean()), 4), "ci95": ci, "t": t, "improved": int((d > 1e-9).sum()), "worsened": int((d < -1e-9).sum()),
                  "delta_long": round(float(d[T.dir.values == 1].mean()), 4), "delta_short": round(float(d[T.dir.values == -1].mean()), 4)})
    # estres: latencia 1 s en gestion y slippage 10 pts en stops
    if v.vid != "V0":
        s["exp_R_lat1s"] = round(float(run_variant_ticks(T, bars, v, lat_ms=1000).R.mean()), 4)
    s["exp_R_slip10"] = round(float(run_variant_ticks(T, bars, Variant(**{**v.__dict__, "slip_pts": 10.0})).R.mean()), 4)
    s["reasons"] = res[v.vid].reason.value_counts().to_dict()
    rows.append(s)
out = pd.DataFrame(rows)
print(out.drop(columns=["reasons", "desc"]).to_string(index=False))
out.to_csv(ROOT / "research/S01_EXIT_VARIANTS_TICKS_RESULTS.csv", index=False)
pd.concat([res[k].assign(R_official=T.R.values) for k in res]).to_csv(ROOT / "research/S01_EXIT_VARIANTS_TICKS_TRADES.csv", index=False)
(ROOT / "research/S01_EXIT_VARIANTS_TICKS_PARITY.json").write_text(json.dumps({"parity_V0_tick": par, "n_variants": N}, indent=1), encoding="utf-8")

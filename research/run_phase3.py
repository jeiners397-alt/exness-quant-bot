"""FASES 3-4: S01..S04 sobre EURUSDm (M15 y H1), 3000 USD, 0.5 %, politica estricta. Todo EXPLORATORIO (ene-2025..oct-2026 ya observado).
Cada estrategia: configuracion canonica (fijada a priori) + vecindad predefinida de 4 variantes (sensibilidad, NO seleccion).
Control aleatorio: 200 sorteos con la misma densidad de senales brutas, direccion aleatoria y pares SL/TP muestreados de la propia estrategia.
Registro: research/PHASE3_RUNS.csv (todas las ejecuciones) y research/PHASE3_MATRIX.csv (matriz canonica).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab.backtest import BacktestConfig, run_backtest  # noqa: E402
from remix_lab.experiments import load_spec  # noqa: E402
from remix_lab.strategies import REGISTRY, Signals, generate  # noqa: E402

CAP, RISK = 3000.0, 0.5
SPEC = load_spec("EURUSDm")
M15 = pd.read_csv(ROOT / "data/raw/EURUSDm_M15.csv", parse_dates=["time"])
H1 = pd.read_csv(ROOT / "data/raw/EURUSDm_H1.csv", parse_dates=["time"])
rng = np.random.default_rng(12345)
CFG = BacktestConfig(initial_capital=CAP, risk_pct=RISK, sizing_policy="strict")
NEIGH = {"S01": [], "S02": [{"donchian_n": 10}, {"donchian_n": 40}, {"sl_atr": 1.5}, {"sl_atr": 3.0}],
         "S03": [{"adx_min": 20.0}, {"adx_min": 30.0}, {"sl_atr": 1.0}, {"sl_atr": 2.0}],
         "S04": [{"sq_ratio": 0.6}, {"sq_ratio": 0.9}, {"mom_n": 5}, {"mom_n": 20}]}


def window(df):
    return df[(df.time >= "2025-01-01") & (df.time < "2026-11-01")].reset_index(drop=True)


def block_ci(x, block=5, B=3000):
    x = np.asarray(x, float); n = len(x)
    if n < 3 * block:
        return [np.nan, np.nan]
    bs = []
    for _ in range(B):
        ix = rng.integers(0, n - block + 1, size=n // block + 1)
        bs.append(np.concatenate([x[i:i + block] for i in ix])[:n].mean())
    return [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]


def summarize(tr, info, extra):
    if tr is None or len(tr) == 0:
        return {**extra, "n": 0, "skipped": json.dumps(info.get("skipped", {}))}
    r = tr.net_r.to_numpy(); m = tr.net_money.to_numpy()
    bal = np.r_[CAP, CAP + np.cumsum(m)]
    peak = np.maximum.accumulate(bal); ddm = float((peak - bal).max()); ddp = float(((peak - bal) / peak).max() * 100)
    gp, gl = m[m > 0].sum(), -m[m < 0].sum()
    q = tr.groupby(pd.to_datetime(tr.entry_time).dt.to_period("Q")).net_r.mean()
    first = pd.to_datetime(tr.entry_time) < "2026-01-01"
    se = r.std(ddof=1) / np.sqrt(len(r)) if len(r) > 1 else np.nan
    return {**extra, "n": len(r), "wr": round(float((m > 0).mean() * 100), 1), "pf": round(float(gp / gl), 3) if gl > 0 else np.nan,
            "exp_R": round(float(r.mean()), 4), "ci95_expR": block_ci(r), "t": round(float(r.mean() / se), 2) if se and se > 0 else np.nan,
            "net_usd": round(float(m.sum()), 2), "ret_pct": round(float(m.sum() / CAP * 100), 2), "maxdd_pct": round(ddp, 2),
            "recovery": round(float(m.sum() / ddm), 3) if ddm > 0 else np.nan,
            "spread_cost_usd": round(float(tr.spread_cost.sum()), 2), "swap_usd": round(float(tr.swap.sum()), 2),
            "exp_R_2025": round(float(r[first].mean()), 4) if first.any() else np.nan, "n_2025": int(first.sum()),
            "exp_R_2026": round(float(r[~first].mean()), 4) if (~first).any() else np.nan, "n_2026": int((~first).sum()),
            "q_pos": int((q > 0).sum()), "q_total": int(len(q)),
            "exp_R_long": round(float(r[tr.dir == 1].mean()), 4) if (tr.dir == 1).any() else np.nan, "n_long": int((tr.dir == 1).sum()),
            "exp_R_short": round(float(r[tr.dir == -1].mean()), 4) if (tr.dir == -1).any() else np.nan, "n_short": int((tr.dir == -1).sum()),
            "top5_trade_share": round(float(np.sort(m)[-5:].sum() / gp), 3) if gp > 0 else np.nan,
            "skipped": json.dumps(info.get("skipped", {})), "risk_real_pct_med": round(float(tr.risk_real_pct.median()), 3)}


def control(df, sig, n_draws=200, hours=None):
    """Control aleatorio: misma densidad de senales brutas, direccion aleatoria, SL/TP muestreados de la estrategia, mismo time_exit."""
    idx = np.flatnonzero(sig.direction != 0)
    k = len(idx)
    if k < 5:
        return None
    pool = np.flatnonzero(np.isin(df.time.dt.hour.to_numpy(), hours)) if hours is not None else np.arange(len(df) - 1)
    out = []
    for _ in range(n_draws):
        pos = rng.choice(pool, size=min(k, len(pool)), replace=False)
        d = np.zeros(len(df), int); sl = np.full(len(df), np.nan); tp = np.full(len(df), np.nan)
        src = rng.choice(idx, size=len(pos))
        d[pos] = rng.choice([-1, 1], size=len(pos)); sl[pos] = sig.sl_dist[src]; tp[pos] = sig.tp_dist[src]
        tr, info = run_backtest(df, Signals(d, sl, tp, sig.time_exit_hour), SPEC, CFG)
        out.append((tr.net_r.mean() if len(tr) else np.nan, len(tr)))
    a = np.array(out, float)
    return {"ctrl_expR_mean": round(float(np.nanmean(a[:, 0])), 4), "ctrl_expR_p95": round(float(np.nanpercentile(a[:, 0], 95)), 4),
            "ctrl_expR_p5": round(float(np.nanpercentile(a[:, 0], 5)), 4), "ctrl_trades_mean": round(float(a[:, 1].mean()), 1), "_dist": a[:, 0]}


runs, matrix = [], []
for sid in ("S01", "S02", "S03", "S04"):
    for tfname, raw in (("M15", M15), ("H1", H1)):
        if sid == "S01" and tfname == "H1":
            continue
        df = window(raw)
        for i, over in enumerate([{}] + NEIGH[sid]):
            sig = generate(sid, df, SPEC, over)
            tr, info = run_backtest(df, sig, SPEC, CFG)
            tag = {"strategy": sid, "tf": tfname, "variant": "canonica" if i == 0 else json.dumps(over), "raw_signals": int((sig.direction != 0).sum())}
            row = summarize(tr, info, tag)
            if i == 0:
                hrs = sorted(set(df.time.dt.hour.to_numpy()[np.flatnonzero(sig.direction != 0)])) if sid == "S01" else None
                c = control(df, sig, hours=hrs)
                if c and row.get("n", 0) > 0:
                    dist = c.pop("_dist"); row.update(c)
                    row["ctrl_pvalue_expR"] = round(float((np.nansum(dist >= row["exp_R"]) + 1) / (np.sum(~np.isnan(dist)) + 1)), 4)
                matrix.append(row)
                tr.to_csv(ROOT / f"results/phase3_trades_{sid}_{tfname}.csv", index=False)
            runs.append(row)
            print(sid, tfname, tag["variant"], row.get("n"), row.get("exp_R"), row.get("pf"), row.get("t"), flush=True)
R = pd.DataFrame(runs)
R["ci95_expR"] = R.ci95_expR.astype(str)
R.to_csv(ROOT / "research/PHASE3_RUNS.csv", index=False)
Mx = pd.DataFrame(matrix); Mx["ci95_expR"] = Mx.ci95_expR.astype(str)
Mx.to_csv(ROOT / "research/PHASE3_MATRIX.csv", index=False)
N = len(R) + 10   # + 10 variantes de salida S01
(ROOT / "research/PHASE3_META.json").write_text(json.dumps({"n_runs_phase3": len(R), "n_trials_total_incl_S01_exit_variants": N, "t_null_max_approx": round(float(np.sqrt(2 * np.log(N))), 2),
                                                           "capital": CAP, "risk_pct": RISK, "policy": "strict", "period": "2025-01-01..2026-10-31 (exploratorio)", "controls": 200}, indent=1), encoding="utf-8")
print(Mx.drop(columns=["skipped"]).T.to_string())

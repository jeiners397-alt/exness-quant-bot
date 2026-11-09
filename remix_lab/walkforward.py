"""F. WALK-FORWARD ENGINE - ventanas cronologicas train/test dentro de la muestra (nunca toca el holdout)."""
from __future__ import annotations

import pandas as pd

from .metrics import compute_metrics
from .optimization import guard_in_sample, optimize
from .experiments import run_one
from . import strategies as st


def make_windows(start, end, train_m, test_m, step_m):
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    out, t0 = [], s
    while True:
        tr_end = t0 + pd.DateOffset(months=train_m)
        te_end = tr_end + pd.DateOffset(months=test_m)
        if te_end > e + pd.Timedelta(days=1):
            break
        out.append((t0, tr_end, tr_end, te_end))
        t0 = t0 + pd.DateOffset(months=step_m)
    return out


def walk_forward(sid, symbol, tf, df, spec, bt, cfg, start, end, min_trades=15, grid=None):
    guard_in_sample(df, cfg)
    wf = cfg["walk_forward"]
    wins = make_windows(start, end, wf["train_months"], wf["test_months"], wf["step_months"])
    oos_parts, rows = [], []
    for k, (a, b, c, d) in enumerate(wins):
        dtr = df[(df.time >= a) & (df.time < b)].reset_index(drop=True)
        dte = df[(df.time >= c) & (df.time < d)].reset_index(drop=True)
        if len(dtr) < 300 or len(dte) < 50:
            continue
        res = optimize(sid, symbol, tf, dtr, spec, bt, cfg, str(a.date()), str(b.date()), min_trades=min_trades,
                       grid=grid, stage="wf_train")
        best = res[res.eligible].head(1)
        if best.empty:
            rows.append(dict(window=k, train=f"{a.date()}..{b.date()}", test=f"{c.date()}..{d.date()}", note="sin candidato elegible"))
            continue
        keys = list((grid or st.get_strategy(sid)[0].grid))
        params = {kk: best.iloc[0][kk] for kk in keys}
        params = {kk: (int(v) if float(v).is_integer() and kk.endswith(("_n", "_h", "fast", "mid", "slow", "lookback")) else float(v))
                  for kk, v in params.items()}
        tr, m, _ = run_one(sid, symbol, tf, params, str(c.date()), str(d.date()), cfg, stage="wf_test", df=dte, spec=spec, bt=bt)
        tr["wf_window"] = k
        oos_parts.append(tr)
        rows.append(dict(window=k, train=f"{a.date()}..{b.date()}", test=f"{c.date()}..{d.date()}",
                         params=params, is_expectancy_r=float(best.iloc[0]["expectancy_r"]),
                         oos_trades=m["trades"], oos_pf=m["profit_factor"], oos_expectancy_r=m["expectancy_r"]))
    oos = pd.concat([x for x in oos_parts if not x.empty], ignore_index=True) if oos_parts else pd.DataFrame()
    return pd.DataFrame(rows), oos

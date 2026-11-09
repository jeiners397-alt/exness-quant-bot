"""REMIX V3 — familias A y B: rejilla PREDEFINIDA (sin barrido), M15 y H1, 3000 USD, 0,5 %, estricto, compuertas de spread del EA (0,15xSL y 30 pts),
filtro de coste ex-ante 0,10 R. Cada configuracion se ejecuta UNA vez sobre todo el periodo; periodos, walk-forward y controles salen de esas operaciones.
Periodos H1: TRAIN 2018-21 | VALID 2022-24 | EXPL 2025-26. M15: TRAIN 2022-11..2023 | VALID 2024 | EXPL 2025-26. EXPL ya fue inspeccionado."""
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
from remix_lab.backtest import BacktestConfig, run_backtest  # noqa: E402
from remix_lab.v3 import gen_a, gen_b  # noqa: E402

F = H.load_frames()
FR = {"H1": pd.concat([F["RETRO"]["H1"], F["EXPL"]["H1"]]).reset_index(drop=True), "M15": pd.concat([F["RETRO"]["M15"], F["EXPL"]["M15"]]).drop_duplicates("time").reset_index(drop=True)}
PERIODS = {"H1": {"TRAIN": ("2018-01-01", "2022-01-01"), "VALID": ("2022-01-01", "2025-01-01"), "EXPL": ("2025-01-01", "2026-11-01")},
           "M15": {"TRAIN": ("2022-11-01", "2024-01-01"), "VALID": ("2024-01-01", "2025-01-01"), "EXPL": ("2025-01-01", "2026-11-01")}}
CFG = BacktestConfig(H.CAP, H.RISK, "strict", 0.0, 0.0, True, max_spread_frac_sl=0.15, max_spread_points=30, reenter_after_open_exit=True)
COST_THR = 0.10
GRID = []
for tf in ("M15", "H1"):
    for lv, cf, sm in itertools.product(("PD", "ASIA"), ("1", "2"), ("struct", "atr")):
        GRID.append(("A", tf, dict(levels=lv, confirm=cf, sl_mode=sm)))
    for k, ker, sm in itertools.product((1.5, 2.0), (True, False), ("atr", "struct")):
        GRID.append(("B", tf, dict(mode="impulse", k=k, ker_on=ker, sl_mode=sm)))
    for ker in (True, False):
        GRID.append(("B", tf, dict(mode="squeeze", ker_on=ker, sl_mode="atr")))
print("configuraciones:", len(GRID), flush=True)

rows, trades, t0 = [], {}, time.time()
for n, (fam, tf, p) in enumerate(GRID):
    df = FR[tf]
    sig = (gen_a if fam == "A" else gen_b)(df, p)
    raw = int((sig.direction != 0).sum())
    sig = H.cost_filter(df, sig, COST_THR)
    tr, info = run_backtest(df, sig, H.SPEC, CFG)
    cid = f"{fam}|{tf}|{json.dumps(p, sort_keys=True)}"
    trades[cid] = tr
    full = H.summarize(tr, info, dict(cid=cid, family=fam, tf=tf, params=json.dumps(p, sort_keys=True), period="FULL", raw_signals=raw, after_cost_filter=int((sig.direction != 0).sum())))
    if full.get("n", 0) >= 30:
        c = H.control(df, sig, 100, hours_from_signals=True)
        if c:
            cs, dist = c; full.update(cs); full["ctrl_p"] = round(float((np.nansum(dist >= full["exp_R"]) + 1) / (np.sum(~np.isnan(dist)) + 1)), 3)
    rows.append(full)
    for per, (a, b) in PERIODS[tf].items():
        sub = tr[(pd.to_datetime(tr.entry_time) >= a) & (pd.to_datetime(tr.entry_time) < b)].reset_index(drop=True)
        rows.append(H.summarize(sub, info, dict(cid=cid, family=fam, tf=tf, params=json.dumps(p, sort_keys=True), period=per)))
    print(f"[{time.time()-t0:4.0f}s] {cid[:70]:70s} n={full.get('n')} expR={full.get('exp_R')} pf={full.get('pf')} t={full.get('t')} p={full.get('ctrl_p')}", flush=True)

R = pd.DataFrame(rows)
for c in ("ci_block", "ci_boot"):
    R[c] = R[c].astype(str)
R.to_csv(ROOT / "research/V3_ALL_RUNS.csv", index=False)
out = ROOT / "results" / "v3_trades"; out.mkdir(parents=True, exist_ok=True)
allt = pd.concat([t.assign(cid=cid) for cid, t in trades.items() if len(t)], ignore_index=True)
allt[["cid", "entry_time", "exit_time", "dir", "lots", "entry", "exit", "exit_reason", "sl_dist", "tp_dist", "net_r", "net_money", "swap", "spread_cost"]].to_csv(out / "V3_AB_all_trades.csv", index=False)

# ---------------- walk-forward anual (expansivo): cada fold elige la configuracion por R medio de las operaciones ANTERIORES al ano de test (n>=30)
wf_rows, wf_trades = [], []
for fam in ("A", "B"):
    for tf in ("M15", "H1"):
        cids = [c for c in trades if c.startswith(f"{fam}|{tf}|")]
        years = range(2020, 2027) if tf == "H1" else range(2024, 2027)
        for y in years:
            start = pd.Timestamp(f"{y}-01-01"); end = pd.Timestamp(f"{y+1}-01-01")
            best, bestv = None, -9
            for c in cids:
                t = trades[c]
                if not len(t):
                    continue
                prev = t[pd.to_datetime(t.entry_time) < start]
                if len(prev) >= 30 and prev.net_r.mean() > bestv:
                    best, bestv = c, prev.net_r.mean()
            if best is None:
                continue
            t = trades[best]; te = t[(pd.to_datetime(t.entry_time) >= start) & (pd.to_datetime(t.entry_time) < end)]
            wf_rows.append(dict(family=fam, tf=tf, test_year=y, chosen=best.split("|", 2)[2], train_expR=round(bestv, 4), n_test=len(te), expR_test=round(float(te.net_r.mean()), 4) if len(te) else np.nan, net_usd_test=round(float(te.net_money.sum()), 2)))
            wf_trades.append(te.assign(family=fam, tf=tf))
W = pd.DataFrame(wf_rows); W.to_csv(ROOT / "research/V3_WALKFORWARD.csv", index=False)
agg = []
for (fam, tf), g in pd.concat(wf_trades, ignore_index=True).groupby(["family", "tf"]):
    r = g.net_r.to_numpy()
    agg.append(dict(family=fam, tf=tf, n_oos=len(r), expR_oos=round(float(r.mean()), 4), t=round(float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))), 2) if len(r) > 2 else np.nan,
                    pf=round(float(g.net_money[g.net_money > 0].sum() / max(-g.net_money[g.net_money < 0].sum(), 1e-9)), 3), net_usd=round(float(g.net_money.sum()), 2)))
A = pd.DataFrame(agg); A.to_csv(ROOT / "research/V3_WALKFORWARD_SUMMARY.csv", index=False)
print(A.to_string(index=False)); print(W.to_string(index=False))
meta = dict(n_configs=len(GRID), cost_filter_R=COST_THR, gates=dict(frac_sl=0.15, points=30), capital=H.CAP, risk=H.RISK, elapsed_s=round(time.time() - t0))
(ROOT / "research/V3_META.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
print(meta)

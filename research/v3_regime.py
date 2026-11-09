"""ESTRATEGIA D — Regime conditional reversal (H1, H4). Pregunta falsable: ¿alguna condicion OBSERVABLE al cierre de la barra de senal (KER10, Choppiness14, ADX14 (formula MT5),
percentil de volatilidad ATR/close en 500 barras) mejora la probabilidad de reversion tras |z50| >= 2?  Terciles FIJADOS con eventos TRAIN (2018-21); VALID 2022-24; EXPL 2025-26.
Parte 1: estudio de eventos (SL 1.5 ATR, +1 R antes de -1 R, cota conservadora). Parte 2: walk-forward anual por celda. Parte 3: backtests completos de 3 filtros pre-registrados."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab import harness as H  # noqa: E402
from remix_lab import indicators as ind  # noqa: E402
from remix_lab.backtest import BacktestConfig, run_backtest  # noqa: E402
from remix_lab.events import barrier_events  # noqa: E402
from remix_lab.strategies import Signals  # noqa: E402
from remix_lab.strategies_d import GEN, resample  # noqa: E402

RNG = np.random.default_rng(12345)
F = H.load_frames()
H1 = pd.concat([F["RETRO"]["H1"], F["EXPL"]["H1"]]).reset_index(drop=True)
FR = {"H1": H1, "H4": resample(H1, "H4")}
HOR = {"H1": 24, "H4": 12}
PER = {"TRAIN": ("2018-01-01", "2022-01-01"), "VALID": ("2022-01-01", "2025-01-01"), "EXPL": ("2025-01-01", "2026-11-01")}
CFG = BacktestConfig(H.CAP, H.RISK, "strict", 0.0, 0.0, True, max_spread_frac_sl=0.15, max_spread_points=30, reenter_after_open_exit=True)


def feats(df):
    f = pd.DataFrame({"ker": ind.ker(df.close, 10), "chop": ind.choppiness(df, 14), "adx": ind.adx_mt5(df, 14)[0], "z": ind.zscore(df.close, 50), "atr": ind.atr(df, 14)})
    f["volpct"] = ind.vol_percentile(df, 14, 500)
    return f


def ci_boot(x, B=1500, block=4):
    x = np.asarray(x, float); n = len(x)
    if n < 20:
        return (np.nan, np.nan)
    b = [np.concatenate([x[i:i + block] for i in RNG.integers(0, n - block + 1, size=n // block + 1)])[:n].mean() for _ in range(B)]
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


rows, wf_rows, bt_rows = [], [], []
for tf, df in FR.items():
    f = feats(df); z = f.z.to_numpy()
    d = np.where(z <= -2.0, 1, np.where(z >= 2.0, -1, 0))
    ev = barrier_events(df, d, f.atr.to_numpy() * 1.5, HOR[tf], (1.0,), min_gap=max(1, HOR[tf] // 4))
    ev["time"] = df.time.to_numpy()[ev.idx.to_numpy()]
    for c in ("ker", "chop", "adx", "volpct"):
        ev[c] = f[c].to_numpy()[ev.idx.to_numpy()]
    tr_ev = ev[(ev.time >= np.datetime64(PER["TRAIN"][0])) & (ev.time < np.datetime64(PER["TRAIN"][1]))]
    q = {c: tr_ev[c].quantile([1 / 3, 2 / 3]).to_numpy() for c in ("ker", "chop", "adx", "volpct")}      # umbrales SOLO con TRAIN
    cells = {"ALL": np.ones(len(ev), bool)}
    for c in ("ker", "chop", "adx", "volpct"):
        cells[f"{c}_LOW"] = (ev[c] < q[c][0]).to_numpy(); cells[f"{c}_MID"] = ((ev[c] >= q[c][0]) & (ev[c] < q[c][1])).to_numpy(); cells[f"{c}_HIGH"] = (ev[c] >= q[c][1]).to_numpy()
    cells["RANGE(ker<p33 & chop>p67)"] = ((ev.ker < q["ker"][0]) & (ev.chop >= q["chop"][1])).to_numpy()
    for name, m in cells.items():
        for per, (a, b) in PER.items():
            s = ev[m & (ev.time >= np.datetime64(a)).to_numpy() & (ev.time < np.datetime64(b)).to_numpy()]
            if len(s) < 20:
                continue
            rc = s["Rc_1.0"].to_numpy(); lo, hi = ci_boot(rc)
            rows.append(dict(tf=tf, cell=name, period=per, n=len(s), p_win=round(float(s["win_1.0"].mean()), 4), E_cons=round(float(rc.mean()), 4), E_opt=round(float(s["Ro_1.0"].mean()), 4),
                             ci_lo=round(lo, 4), ci_hi=round(hi, 4), t=round(float(rc.mean() / (rc.std(ddof=1) / np.sqrt(len(rc)))), 2), cost_R=round(float(s.cost_R.mean()), 4)))
    # walk-forward anual: elige la celda (no ALL) con mayor R medio previo (n>=50) y aplica el ano siguiente; compara con ALL
    ev["year"] = pd.to_datetime(ev.time).dt.year
    for y in range(2020, 2027):
        prev = ev[ev.time < np.datetime64(f"{y}-01-01")]
        best, bv = None, -9
        for name, m in cells.items():
            if name == "ALL":
                continue
            pm = prev[m[: len(ev)][prev.index]] if False else prev[pd.Series(m, index=ev.index)[prev.index].to_numpy()]
            if len(pm) >= 50 and pm["Rc_1.0"].mean() > bv:
                best, bv = name, pm["Rc_1.0"].mean()
        te = ev[ev.year == y]
        if best is None or te.empty:
            continue
        tm = te[pd.Series(cells[best], index=ev.index)[te.index].to_numpy()]
        wf_rows.append(dict(tf=tf, year=y, chosen=best, train_E=round(float(bv), 4), n_test=len(tm), E_test=round(float(tm["Rc_1.0"].mean()), 4) if len(tm) else np.nan, n_all=len(te), E_all=round(float(te["Rc_1.0"].mean()), 4)))
    # backtests completos de 3 filtros pre-registrados sobre S05 (z=2, SL 2 ATR, TP media, max_bars): NINGUN FILTRO, KER_LO(p33 TRAIN), RANGE
    base = GEN["S05"](df, dict(z_th=2.0, trend_filter=False, sl_atr=2.0, max_bars=18 if tf == "H4" else 48))
    masks = {"D0 sin filtro": np.ones(len(df), bool), "D1 ADX_MT5<25 (=L2)": (f.adx.to_numpy() < 25), "D2 KER<p33(TRAIN)": (f.ker.to_numpy() < q["ker"][0]),
             "D3 RANGE ker<p33 & chop>p67 (TRAIN)": (f.ker.to_numpy() < q["ker"][0]) & (f.chop.to_numpy() >= q["chop"][1])}
    for name, m in masks.items():
        sig = Signals(np.where(m, base.direction, 0), base.sl_dist, base.tp_dist, None, base.max_bars)
        tr, info = run_backtest(df, sig, H.SPEC, CFG)
        r = H.summarize(tr, info, dict(tf=tf, filtro=name, period="FULL"))
        if r.get("n", 0) >= 30:
            c = H.control(df, sig, 100)
            if c:
                cs, dist = c; r.update(cs); r["ctrl_p"] = round(float((np.nansum(dist >= r["exp_R"]) + 1) / (np.sum(~np.isnan(dist)) + 1)), 3)
        bt_rows.append(r)
        for per, (a, b) in PER.items():
            sub = tr[(pd.to_datetime(tr.entry_time) >= a) & (pd.to_datetime(tr.entry_time) < b)].reset_index(drop=True)
            bt_rows.append(H.summarize(sub, info, dict(tf=tf, filtro=name, period=per)))
    print(tf, "terciles TRAIN:", {k: [round(float(x), 3) for x in v] for k, v in q.items()}, flush=True)

E = pd.DataFrame(rows); E.to_csv(ROOT / "research/V3_D_EVENTS.csv", index=False)
W = pd.DataFrame(wf_rows); W.to_csv(ROOT / "research/V3_D_WALKFORWARD.csv", index=False)
B = pd.DataFrame(bt_rows)
for c in ("ci_block", "ci_boot"):
    B[c] = B[c].astype(str)
B.to_csv(ROOT / "research/V3_D_BACKTESTS.csv", index=False)
pd.set_option("display.width", 250)
print(E[(E.cell.isin(["ALL", "RANGE(ker<p33 & chop>p67)", "ker_LOW", "chop_HIGH", "adx_LOW", "volpct_LOW"]))].pivot_table(index=["tf", "cell"], columns="period", values="E_cons")[["TRAIN", "VALID", "EXPL"]].round(3).to_string())
print(W.to_string(index=False))
print(B[B.period == "FULL"][["tf", "filtro", "n", "wr", "pf", "exp_R", "t", "maxdd_pct", "net_usd", "ctrl_p"]].to_string(index=False))

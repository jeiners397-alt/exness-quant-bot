"""Fase D â€” arnes comun: datos por ventana, resumen robusto, controles aleatorios y escenarios de coste. Semilla fija 12345."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import BacktestConfig, run_backtest
from .experiments import load_spec
from .strategies import Signals
from .strategies_d import PT, resample

ROOT = Path(__file__).resolve().parent.parent
CAP, RISK = 3000.0, 0.5
SPEC = load_spec("EURUSDm")
CFG = BacktestConfig(initial_capital=CAP, risk_pct=RISK, sizing_policy="strict")
RNG = np.random.default_rng(12345)
DATA_NOTES = {}


def _read(path):
    return pd.read_csv(path, parse_dates=["time"])


def _fix_spread(df, label):
    z = int((df.spread <= 0).sum())
    DATA_NOTES[label] = {"bars": len(df), "spread_zero_replaced_by_median": z}
    if z:
        df = df.copy(); df.loc[df.spread <= 0, "spread"] = df.spread[df.spread > 0].median()
    return df


def load_frames():
    """EXPL = 2025-01-01..2026-10-31 (ya inspeccionado). RETRO = historia anterior a 2025 (H1 desde 2014, M15 desde 2022-11): no inspeccionada antes de la Fase D."""
    f = {"EXPL": {}, "RETRO": {}}
    h1 = _read(ROOT / "data/raw/EURUSDm_H1.csv"); m15 = _read(ROOT / "data/raw/EURUSDm_M15.csv")
    sel = lambda d: d[(d.time >= "2025-01-01") & (d.time < "2026-11-01")].reset_index(drop=True)
    f["EXPL"]["M15"], f["EXPL"]["H1"] = sel(m15), sel(h1)
    h1r_all = _read(ROOT / "data/raw/hist/EURUSDm_H1_pre2025.csv")
    DATA_NOTES["H1_excluded_before_2018"] = {"bars": int((h1r_all.time < "2018-01-01").sum()), "reason": "cobertura incompleta (2014-2016 ~300 barras/ano) y spread=0 en 2014-2017: datos invalidos"}
    h1r = _fix_spread(h1r_all[h1r_all.time >= "2018-01-01"].reset_index(drop=True), "H1_2018_2024")
    m15r = _fix_spread(_read(ROOT / "data/raw/hist/EURUSDm_M15_pre2025.csv"), "M15_pre2025")
    f["RETRO"]["M15"], f["RETRO"]["H1"] = m15r, h1r
    for per in ("EXPL", "RETRO"):
        base = h1 if per == "EXPL" else h1r
        base = sel(base) if per == "EXPL" else base      # H4/D1 derivados de H1 (ver strategies_d.resample)
        f[per]["H4"], f[per]["D1"] = resample(base, "H4"), resample(base, "D1")
    return f


def block_ci(x, block=5, B=2000):
    x = np.asarray(x, float); n = len(x)
    if n < 3 * block:
        return [np.nan, np.nan]
    bs = [np.concatenate([x[i:i + block] for i in RNG.integers(0, n - block + 1, size=n // block + 1)])[:n].mean() for _ in range(B)]
    return [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]


def iid_ci(x, B=2000):
    x = np.asarray(x, float)
    if len(x) < 10:
        return [np.nan, np.nan]
    bs = RNG.choice(x, size=(B, len(x))).mean(axis=1)
    return [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]


def _pf(v):
    g, l = v[v > 0].sum(), -v[v < 0].sum()
    return float(g / l) if l > 0 else np.nan


def summarize(tr, info=None, extra=None):
    row = dict(extra or {})
    if tr is None or len(tr) == 0:
        row.update(n=0, skipped=json.dumps((info or {}).get("skipped", {}))); return row
    r = tr.net_r.to_numpy(); m = tr.net_money.to_numpy(); n = len(r)
    bal = np.r_[CAP, CAP + np.cumsum(m)]; peak = np.maximum.accumulate(bal)
    ddm = float((peak - bal).max()); ddp = float(((peak - bal) / peak).max() * 100)
    et = pd.to_datetime(tr.entry_time)
    q = tr.groupby(et.dt.to_period("Q")).net_r.mean()
    half = et < et.iloc[0] + (et.iloc[-1] - et.iloc[0]) / 2
    se = r.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    srt = np.sort(r)
    loss = r < 0
    streak = best = 0
    for v in loss:
        streak = streak + 1 if v else 0; best = max(best, streak)
    cost_R = (tr.spread_cost - tr.swap) / (tr.lots * SPEC["value_per_price_unit_per_lot"] * tr.sl_dist)
    wins, losses = r[r > 0], r[r < 0]
    row.update(n=n, wr=round(float((m > 0).mean() * 100), 1), pf=round(_pf(m), 3) if not np.isnan(_pf(m)) else np.nan,
               exp_R=round(float(r.mean()), 4), ci_block=block_ci(r), ci_boot=iid_ci(r), t=round(float(r.mean() / se), 2) if se and se > 0 else np.nan,
               avg_win_R=round(float(wins.mean()), 3) if len(wins) else np.nan, avg_loss_R=round(float(losses.mean()), 3) if len(losses) else np.nan,
               payoff=round(float(wins.mean() / -losses.mean()), 3) if len(wins) and len(losses) else np.nan,
               net_usd=round(float(m.sum()), 2), ret_pct=round(float(m.sum() / CAP * 100), 2), maxdd_pct=round(ddp, 2),
               recovery=round(float(m.sum() / ddm), 3) if ddm > 0 else np.nan, max_consec_loss=int(best),
               exp_R_ex1=round(float(srt[:-1].mean()), 4) if n > 1 else np.nan, exp_R_ex5=round(float(srt[:-5].mean()), 4) if n > 5 else np.nan,
               pf_ex5=round(_pf(np.sort(m)[:-5]), 3) if n > 5 and not np.isnan(_pf(np.sort(m)[:-5])) else np.nan,
               top1_share=round(float(m.max() / m[m > 0].sum()), 3) if (m > 0).any() else np.nan,
               q_pos=int((q > 0).sum()), q_total=int(len(q)), exp_R_h1=round(float(r[half].mean()), 4) if half.any() else np.nan,
               exp_R_h2=round(float(r[~half].mean()), 4) if (~half).any() else np.nan,
               n_long=int((tr.dir == 1).sum()), exp_R_long=round(float(r[tr.dir == 1].mean()), 4) if (tr.dir == 1).any() else np.nan,
               n_short=int((tr.dir == -1).sum()), exp_R_short=round(float(r[tr.dir == -1].mean()), 4) if (tr.dir == -1).any() else np.nan,
               cost_R=round(float(cost_R.mean()), 4), gross_R=round(float((tr.net_r + cost_R).mean()), 4),
               risk_real_pct_med=round(float(tr.risk_real_pct.median()), 3), skipped=json.dumps((info or {}).get("skipped", {})))
    return row


def control(df, sig, n_draws=100, hours_from_signals=False):
    """Control aleatorio: misma densidad de senales brutas, misma proporcion LONG/SHORT, pares SL/TP muestreados de la estrategia,
    mismo riesgo (CFG) y mismas reglas temporales (time_exit/max_bars). No replica salidas por indicador."""
    idx = np.flatnonzero(sig.direction != 0); k = len(idx)
    if k < 10:
        return None
    p_long = float((sig.direction[idx] == 1).mean())
    if hours_from_signals:
        hrs = df.time.dt.hour.to_numpy(); pool = np.flatnonzero(np.isin(hrs, np.unique(hrs[idx])))
    else:
        pool = np.arange(len(df) - 1)
    pool = pool[pool < len(df) - 1]
    vals = []
    for _ in range(n_draws):
        pos = RNG.choice(pool, size=min(k, len(pool)), replace=False)
        d = np.zeros(len(df), int); sl = np.full(len(df), np.nan); tp = np.full(len(df), np.nan)
        src = RNG.choice(idx, size=len(pos))
        d[pos] = np.where(RNG.random(len(pos)) < p_long, 1, -1); sl[pos] = sig.sl_dist[src]; tp[pos] = sig.tp_dist[src]
        tr, _ = run_backtest(df, Signals(d, sl, tp, sig.time_exit_hour, sig.max_bars), SPEC, CFG)
        vals.append(tr.net_r.mean() if len(tr) else np.nan)
    a = np.array(vals, float)
    return dict(ctrl_mean=round(float(np.nanmean(a)), 4), ctrl_p5=round(float(np.nanpercentile(a, 5)), 4), ctrl_p95=round(float(np.nanpercentile(a, 95)), 4)), a


def run(df, sig, label: dict, n_ctrl=100, with_control=True, hours_from_signals=False):
    tr, info = run_backtest(df, sig, SPEC, CFG)
    row = summarize(tr, info, {**label, "raw_signals": int((sig.direction != 0).sum())})
    if with_control and row.get("n", 0) >= 30:
        c = control(df, sig, n_ctrl, hours_from_signals)
        if c:
            cs, dist = c; row.update(cs)
            row["ctrl_p"] = round(float((np.nansum(dist >= row["exp_R"]) + 1) / (np.sum(~np.isnan(dist)) + 1)), 3)
    return row, tr


# ------------------------------------------------------------------ costes
def est_cost_R(df, sig, slip_pts=2.0):
    """Coste ex-ante en R usando SOLO informacion de la barra de senal: (spread de la barra + slippage estimado) / distancia SL. Sin spreads futuros."""
    sp = df["spread"].to_numpy(float) * PT
    with np.errstate(invalid="ignore", divide="ignore"):
        return (sp + slip_pts * PT) / sig.sl_dist


def cost_filter(df, sig, thr, slip_pts=2.0):
    c = est_cost_R(df, sig, slip_pts)
    d = np.where(np.isfinite(c) & (c <= thr), sig.direction, 0)
    return Signals(d, sig.sl_dist, sig.tp_dist, sig.time_exit_hour, sig.max_bars, sig.exit_long, sig.exit_short)


def cost_scenarios(df, sig, label):
    """Base / estres (spread x1.5 y 10 pts de slippage por lado) / filtros ex-ante 0.05R y 0.10R. Devuelve una fila."""
    out = dict(label)
    c = est_cost_R(df, sig)[sig.direction != 0]
    out.update(n_signals=int(len(c)), est_cost_R_mean=round(float(np.nanmean(c)), 4) if len(c) else np.nan, share_gt_0p05=round(float(np.nanmean(c > 0.05)), 3) if len(c) else np.nan,
               share_gt_0p10=round(float(np.nanmean(c > 0.10)), 3) if len(c) else np.nan,
               sl_pips_median=round(float(np.nanmedian(sig.sl_dist[sig.direction != 0]) / 1e-4), 1) if len(c) else np.nan)
    base, _ = run(df, sig, {}, with_control=False)
    out.update(n_base=base.get("n", 0), expR_base=base.get("exp_R"), gross_R=base.get("gross_R"), cost_R=base.get("cost_R"), pf_base=base.get("pf"))
    d2 = df.copy(); d2["spread"] = d2["spread"] * 1.5
    tr, info = run_backtest(d2, sig, SPEC, BacktestConfig(CAP, RISK, "strict", 0.0, 10.0))
    s = summarize(tr, info)
    out.update(n_stress=s.get("n", 0), expR_stress=s.get("exp_R"), pf_stress=s.get("pf"))
    for thr, tag in ((0.05, "f05"), (0.10, "f10")):
        r, _ = run(df, cost_filter(df, sig, thr), {}, with_control=False)
        out.update({f"n_{tag}": r.get("n", 0), f"expR_{tag}": r.get("exp_R"), f"pf_{tag}": r.get("pf"), f"t_{tag}": r.get("t"), f"cost_R_{tag}": r.get("cost_R")})
    return out


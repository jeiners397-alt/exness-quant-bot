"""V9 - tablas descriptivas: microestructura, sesiones, spread, probabilidades de entrada, impulsos (modos de entrada), rangos, barridas."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from research import v9_scalp_study as S
from research import v8_tables as T8

V = S.V
ROOT = S.ROOT
RES = ROOT / "research"
R15 = "R_1.5"


def micro_session_spread():
    micro, sess, spr = [], [], []
    for tf in ("M1", "M5"):
        d = S.load("XAUUSDm", tf); V.HZ = S.CFG[tf]["HZ"]; V.MAXH = S.CFG[tf]["MAXH"]
        ret = np.log(d.close).diff()
        exp_dt = d.time.diff().dt.total_seconds().div(60)
        mins = S.CFG[tf]["mins"]
        for name, m in (("ALL", d.time > "1900"), ("DEV", S.split_mask(d.time, "DEV")), ("SEL", S.split_mask(d.time, "SEL")), ("VAL", S.split_mask(d.time, "VAL"))):
            x = d[m.values]; r = ret[m.values].dropna()
            r2 = r.rolling(5).sum().dropna(); r16 = r.rolling(15 // mins if mins <= 5 else 3).sum().dropna()
            micro.append(dict(tf=tf, split=name, bars=len(x), first=str(x.time.iloc[0]), last=str(x.time.iloc[-1]), dup_removed=0, gaps_gt_5x_tf=int((exp_dt[m.values] > 5 * mins).sum()), zero_range_pct=round(float((x.rng == 0).mean() * 100), 2),
                              spread_pts_med=float(x.spread.median()), spread_pts_p95=float(x.spread.quantile(.95)), cost_ATR_med=round(float((x.spr / x.atr).median()), 4), atr_usd_med=round(float(x.atr.median()), 4),
                              ret_mean_bp=round(float(r.mean() * 1e4), 5), ret_std_bp=round(float(r.std() * 1e4), 3), skew=round(float(r.skew()), 2), kurt=round(float(r.kurt()), 1),
                              ac1=round(float(r.autocorr(1)), 4), ac2=round(float(r.autocorr(2)), 4), ac5=round(float(r.autocorr(5)), 4), var_ratio_5=round(float(r2.var() / (5 * r.var())), 3),
                              mean_ER30=round(float(x.er30.mean()), 3), tick_vol_med=float(x.tick_volume.median()), tick_vol_cv=round(float(x.tick_volume.std() / x.tick_volume.mean()), 2),
                              note="spread por barra (historico real del servidor); tick_volume = proxy de actividad; NO hay profundidad ni order flow (no se inventa)"))
        ret_ = ret.shift(-3) * np.sign(ret.rolling(3).sum())
        for h, g in d.groupby("hour"):
            sess.append(dict(tf=tf, hour_utc=int(h), n=len(g), spread_pts_med=float(g.spread.median()), atr_usd_med=round(float(g.atr.median()), 4), range_usd_med=round(float(g.rng.median()), 4), cost_ATR_med=round(float((g.spr / g.atr).median()), 4),
                             tick_vol_med=float(g.tick_volume.median()), mean_abs_ret_bp=round(float(ret.loc[g.index].abs().mean() * 1e4), 3), mean_ER8=round(float(g.er8.mean()), 3),
                             p_momentum3_continues=round(float((ret_.loc[g.index].dropna() > 0).mean()), 4)))
        d["wd"] = d.time.dt.dayofweek
        rel = d.spread / d.spread.median()
        for lab, g in list(d.groupby("hour")) + [(f"wd{k}", g) for k, g in d.groupby("wd")]:
            spr.append(dict(tf=tf, group=lab if isinstance(lab, str) else f"hora_{int(lab)}", n=len(g), spread_pts_p10=float(g.spread.quantile(.1)), spread_pts_p50=float(g.spread.median()), spread_pts_p90=float(g.spread.quantile(.9)), spread_pts_p99=float(g.spread.quantile(.99)),
                            frac_spread_gt_2x_med=round(float((rel.loc[g.index] > 2).mean()), 4), cost_ATR_p50=round(float((g.spr / g.atr).median()), 4), cost_ATR_p90=round(float((g.spr / g.atr).quantile(.9)), 4),
                            gross_R_needed_to_breakeven=round(float((g.spr / g.atr).median()), 4)))
        corr = float(np.corrcoef(d.spr.dropna().iloc[100:], d.atr.dropna().iloc[:len(d.spr.dropna().iloc[100:])])[0, 1]) if False else float(d[["spr", "atr"]].dropna().corr().iloc[0, 1])
        spr.append(dict(tf=tf, group="corr(spread, ATR)", n=len(d), spread_pts_p50=round(corr, 3)))
    pd.DataFrame(micro).to_csv(RES / "V9_XAUUSD_MICROSTRUCTURE.csv", index=False)
    pd.DataFrame(sess).to_csv(RES / "V9_XAUUSD_SESSION_PROFILE.csv", index=False)
    pd.DataFrame(spr).to_csv(RES / "V9_XAUUSD_SPREAD_ANALYSIS.csv", index=False)


def entry_probabilities():
    rows = []
    import glob
    for f in glob.glob(str(ROOT / "results" / "v9" / "events_full_*.pkl")):
        F = pd.read_pickle(f); F["time"] = pd.to_datetime(F.time)
        sym, tf = F.symbol.iloc[0], F.tf.iloc[0]
        hz = S.CFG[tf]["HZ"]
        F["sess"] = pd.cut(F.hour, [-1, 6, 12, 20, 23], labels=[s[2] for s in S.SESS])
        F["split"] = np.select([S.split_mask(F.time, s) for s in ("DEV", "SEL", "VAL")], ["DEV", "SEL", "VAL"], "OUT")
        for (fam, var, sp, se), g in F.groupby(["family", "variant", "split", "sess"], observed=True):
            if len(g) < 30:
                continue
            r = dict(symbol=sym, tf=tf, family=fam, variant=var, split=sp, session=str(se), n=len(g))
            for h in hz:
                r[f"p_fav_h{h}"] = round(float((g[f"gross_h{h}"] > 0).mean()), 3); r[f"p_adv_h{h}"] = round(float((g[f"gross_h{h}"] < 0).mean()), 3)
                r[f"mean_net_h{h}_ATR"] = round(float((g[f"gross_h{h}"] - g.cost).mean()), 4); r[f"median_gross_h{h}_ATR"] = round(float(g[f"gross_h{h}"].median()), 4)
            for k in (1.0, 1.5, 2.0, 3.0):
                r[f"p_reach_{k}R_before_SL"] = round(float(g[f"hit_{k}"].mean()), 3)
            r.update(p_sl=round(float(g.p_sl.mean()), 3), mfe_med=round(float(g.mfe.median()), 3), mae_med=round(float(g.mae.median()), 3), t_mfe_med=float(g.t_mfe.median()), t_mae_med=float(g.t_mae.median()),
                     cost_ATR=round(float(g.cost.mean()), 4), expR_net_1p5=round(float(g[R15].mean()), 4), expR_gross_1p5=round(float((g[R15] + g.cost).mean()), 4))
            rows.append(r)
    pd.DataFrame(rows).to_csv(RES / "V9_ENTRY_PROBABILITIES.csv", index=False)


def tstat(x):
    t, _ = V.tstat(x)
    return round(t, 2) if t == t else np.nan


def momentum_analysis():
    rows = []
    for tf in ("M1", "M5"):
        F = pd.read_pickle(ROOT / "results" / "v9" / f"events_full_XAUUSDm_{tf}.pkl"); F["time"] = pd.to_datetime(F.time)
        for fam in ("A_MOMENTUM", "B_BREAKOUT", "F_VOL_EXPANSION"):
            for var in ("primary", "inverted"):
                g0 = F[(F.family == fam) & (F.variant == var)]
                for f in ("impulse3", "accel", "rng_atr", "tv_rel", "spr_atr", "prevvol", "compress", "er"):
                    x = g0[f].replace([np.inf, -np.inf], np.nan)
                    try:
                        q = pd.qcut(x, 3, labels=["T1_bajo", "T2_medio", "T3_alto"], duplicates="drop")
                    except ValueError:
                        continue
                    for lab, h in g0.groupby(q, observed=True):
                        rows.append(dict(kind="feature_bucket", tf=tf, family=fam, variant=var, feature=f, bucket=str(lab), n=len(h), feat_lo=round(float(h[f].min()), 4), feat_hi=round(float(h[f].max()), 4),
                                         expR_net_1p5=round(float(h[R15].mean()), 4), expR_gross_1p5=round(float((h[R15] + h.cost).mean()), 4), t=tstat(h[R15]), cost_ATR=round(float(h.cost.mean()), 4)))
    # modos de entrada (A y B, XAU): inmediata / confirmada (1 vela) / retroceso 0.3 ATR / retest (familia I)
    for tf in ("M1", "M5"):
        d = S.load("XAUUSDm", tf); T8.MAXH = S.CFG[tf]["MAXH"]
        fams = S.families(d, tf)
        for fam in ("A_MOMENTUM", "B_BREAKOUT"):
            idx, dr = fams[fam]; ok = idx > 100; idx, dr = idx[ok], dr[ok]
            V.COOL = 10; idx, dr, _ = V.dedupe(idx, dr, None)
            for var, sg in (("primary", 1), ("inverted", -1)):
                s = dr * sg
                res = {"inmediata": [], "confirmada_1vela": [], "retroceso_0.3ATR": []}
                for i, dd in zip(idx, s):
                    if i + 3 + T8.MAXH + 5 >= len(d):
                        continue
                    r = T8.sim_one(d, i, dd, "next_open", "TP1.5")
                    if r is not None: res["inmediata"].append(r)
                    c = d.close.values
                    if dd * (c[i + 1] - c[i]) > 0:                                  # confirmacion: la vela siguiente cierra a favor
                        r = T8.sim_one(d, i + 1, dd, "next_open", "TP1.5")
                        if r is not None: res["confirmada_1vela"].append(r)
                    r = T8.sim_one(d, i, dd, "limit_0.3ATR", "TP1.5")
                    if r is not None: res["retroceso_0.3ATR"].append(r)
                for k, v in res.items():
                    v = np.array(v)
                    rows.append(dict(kind="modo_entrada", tf=tf, family=fam, variant=var, feature="entry_mode", bucket=k, n=len(v), expR_net_1p5=round(float(v.mean()), 4), t=tstat(v), fill_rate=round(len(v) / max(len(idx), 1), 3)))
    pd.DataFrame(rows).to_csv(RES / "V9_MOMENTUM_ANALYSIS.csv", index=False)


def range_and_sweeps():
    rr, sw = [], []
    for tf in ("M1", "M5"):
        d = S.load("XAUUSDm", tf); V.HZ = S.CFG[tf]["HZ"]; V.MAXH = S.CFG[tf]["MAXH"]
        F = pd.read_pickle(ROOT / "results" / "v9" / f"events_full_XAUUSDm_{tf}.pkl"); F["time"] = pd.to_datetime(F.time)
        h, l, c, a = d.high.values, d.low.values, d.close.values, d.atr.values
        hh30 = d.high.rolling(30).max().shift(1).values; ll30 = d.low.rolling(30).min().shift(1).values
        hh60 = d.high.rolling(60).max().shift(1).values; ll60 = d.low.rolling(60).min().shift(1).values
        J = F[(F.family == "J_RANGE") & (F.variant == "primary")]
        for sp in ("DEV", "SEL", "VAL"):
            g = J[S.split_mask(J.time, sp).values]
            if len(g) < 20: continue
            i = g.idx.values; mid = (hh30[i] + ll30[i]) / 2; W = S.CFG[tf]["MAXH"]
            ret_mid = []; brk = []
            for ii, m, dd, hi, lo in zip(i, mid, g.dir.values, hh30[i], ll30[i]):
                if ii + 1 + W >= len(d): ret_mid.append(np.nan); brk.append(np.nan); continue
                seg_h, seg_l, seg_c = h[ii + 1: ii + 1 + W], l[ii + 1: ii + 1 + W], c[ii + 1: ii + 1 + W]
                ret_mid.append(float((seg_h >= m).any() if dd > 0 else (seg_l <= m).any()))
                brk.append(float(((seg_c > hi) | (seg_c < lo)).any()))
            rr.append(dict(tf=tf, split=sp, n=len(g), width_ATR_med=round(float(np.median((hh30[i] - ll30[i]) / a[i])), 3), p_returns_to_center=round(float(np.nanmean(ret_mid)), 3), p_breaks_range=round(float(np.nanmean(brk)), 3),
                           expR_net_1p5=round(float(g[R15].mean()), 4), expR_gross_1p5=round(float((g[R15] + g.cost).mean()), 4), t=tstat(g[R15]), cost_ATR=round(float(g.cost.mean()), 4),
                           mfe_med=round(float(g.mfe.median()), 3), mae_med=round(float(g.mae.median()), 3), events_per_day=round(len(g) / max(g.time.dt.normalize().nunique(), 1), 2),
                           nota="J: ER30<0.15 y anchura<3 ATR; fade en el 15% inferior/superior. El movimiento neto tras costes es el resultado, no la 'media' del rango"))
        C_ = F[(F.family == "C_SWEEP") & (F.variant == "primary")]
        i = C_.idx.values
        dist = np.maximum((h[i] - hh60[i]) / a[i], (ll60[i] - l[i]) / a[i])
        C_ = C_.assign(dist=dist)
        C_["dterc"] = pd.qcut(C_.dist, 3, labels=["corta", "media", "larga"], duplicates="drop")
        C_["sess"] = pd.cut(C_.hour, [-1, 6, 12, 20, 23], labels=[s[2] for s in S.SESS])
        for sp in ("DEV", "SEL", "VAL"):
            g0 = C_[S.split_mask(C_.time, sp).values]
            for (dt, se), g in g0.groupby(["dterc", "sess"], observed=True):
                if len(g) < 30: continue
                sw.append(dict(tf=tf, split=sp, sweep_dist=str(dt), session=str(se), n=len(g), dist_ATR_med=round(float(g.dist.median()), 3), p_reversal_h_mid=round(float((g[f"gross_h{S.CFG[tf]['HZ'][len(S.CFG[tf]['HZ']) // 2]}"] > 0).mean()), 3),
                               expR_net_1p5=round(float(g[R15].mean()), 4), expR_gross_1p5=round(float((g[R15] + g.cost).mean()), 4), t=tstat(g[R15]), mfe_med=round(float(g.mfe.median()), 3), mae_med=round(float(g.mae.median()), 3)))
    pd.DataFrame(rr).to_csv(RES / "V9_RANGE_SCALPING.csv", index=False)
    pd.DataFrame(sw).to_csv(RES / "V9_LIQUIDITY_SWEEPS.csv", index=False)


if __name__ == "__main__":
    micro_session_spread(); print("micro ok")
    entry_probabilities(); print("entry ok")
    momentum_analysis(); print("momentum ok")
    range_and_sweeps(); print("range ok")

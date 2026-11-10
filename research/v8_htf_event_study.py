"""V8 Lote B - estudio de eventos H4 y D1 (XAUUSDm, USTECm, BTCUSDm, ETHUSDm, EURUSDm), 9 conjuntos de reglas (8 familias, A con 2 ventanas), primario e invertido.
Metodologia identica a V7 (misma simulate/summarize): senal en el cierre de la vela i, entrada en apertura de i+1, coste = spread real de esa vela, SL medicion = 1 ATR(14),
TP en {0.5,1,1.5,2,3}R, max 40 velas, empate => SL. Enfriamiento 6 velas. IS < 2025-07-01 <= OOS. Control aleatorio por hora y tercil de ER.
Datos: M15 remuestreado (UTC). Las velas D1/H4 parciales se CONSERVAN (igual que MT5; verificado contra el probador). NADA posterior a 2026-10-31 (reserva prospectiva).
Regla de candidato prefijada para HTF (muestras pequenas): n_IS>=30, expR_IS>0, t_IS>=2; confirmacion OOS: n_OOS>=15, expR>0, t>=1.65. Clase B ademas: t_IS >= sqrt(2 ln N), coste x1.5 positivo, IC95 OOS excluye 0.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

os.environ.setdefault("V7_TF", "M15")
import numpy as np
import pandas as pd

from research import v7_event_study as V

V.COOL = 6
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "research"
SYMS = ["XAUUSDm", "USTECm", "BTCUSDm", "ETHUSDm", "EURUSDm"]
TFS = {"H4": "4h", "D1": "1D"}
TF_RULE = {"H1": "1h", "H4": "4h", "D1": "1D"}
SPLIT = V.SPLIT
INFO = V.INFO


def load_htf(s: str, tf: str) -> pd.DataFrame:
    d = pd.read_csv(V.D / f"{s}_M15.csv", parse_dates=["time"]).drop_duplicates("time").sort_values("time")
    d = d[d.time < "2026-11-01"]
    g = d.set_index("time").resample(TF_RULE[tf])
    cnt = g.close.count()
    a = g.agg(dict(open="first", high="max", low="min", close="last", tick_volume="sum", spread="mean", real_volume="sum"))
    a["nbars"] = cnt
    a = a[a.nbars >= 1].dropna(subset=["open"]).reset_index()      # se CONSERVAN las velas parciales: asi coincide con el grafico de MT5 (verificado: 4537 barras H4 = barras del probador)
    a["spr"] = a.spread * INFO[s]["point"]
    pc = a.close.shift(1)
    tr = np.maximum(a.high - a.low, np.maximum((a.high - pc).abs(), (a.low - pc).abs()))
    a["atr"] = tr.rolling(14).mean()
    a["er30"] = (a.close - a.close.shift(30)).abs() / a.close.diff().abs().rolling(30).sum()
    a["er8"] = (a.close - a.close.shift(8)).abs() / a.close.diff().abs().rolling(8).sum()
    a["hour"] = a.time.dt.hour
    a["rng"] = a.high - a.low
    a["sma20"] = a.close.rolling(20).mean(); a["sma50"] = a.close.rolling(50).mean()
    return a


def _up_dn(c, hh, ll):
    up = (c > hh) & np.r_[False, c[:-1] <= hh[:-1]]
    dn = (c < ll) & np.r_[False, c[:-1] >= ll[:-1]]
    return up, dn


def fam_events(d: pd.DataFrame) -> dict:
    """Devuelve {nombre: (idx, dir_primaria)}. Todo con informacion <= cierre de la vela i."""
    o, h, l, c, a = (d[k].values for k in ("open", "high", "low", "close", "atr"))
    sh = lambda x, k=1: np.r_[np.full(k, np.nan), x[:-k]]
    hh20 = d.high.rolling(20).max().shift(1).values; ll20 = d.low.rolling(20).min().shift(1).values
    hh55 = d.high.rolling(55).max().shift(1).values; ll55 = d.low.rolling(55).min().shift(1).values
    hh10 = d.high.rolling(10).max().shift(1).values; ll10 = d.low.rolling(10).min().shift(1).values
    ev = {}

    def pack(mask_up, mask_dn):
        m = mask_up | mask_dn
        return np.where(m)[0], np.where(mask_up, 1, -1)[m]

    up, dn = _up_dn(c, hh20, ll20); ev["A1_BREAKOUT20"] = pack(up, dn)
    up, dn = _up_dn(c, hh55, ll55); ev["A2_BREAKOUT55"] = pack(up, dn)
    mv = c - sh(c, 8); ok = d.er8.values > 0.5
    ev["B_MOMENTUM"] = pack((mv > 2 * a) & ok, (mv < -2 * a) & ok)
    comp = d.rng.rolling(5).mean().shift(1).values < 0.7 * sh(a)
    expn = d.rng.values > 1.8 * sh(a)
    ev["C_VOL_EXPANSION"] = pack(comp & expn & (c > o), comp & expn & (c < o))
    mv3 = c - sh(c, 3)
    ev["D_EXTREME_REVERSION"] = pack(mv3 < -2.5 * a, mv3 > 2.5 * a)             # primario = fade (largo tras caida extrema)
    tight = (hh10 - ll10) < 2.5 * a
    up, dn = _up_dn(c, hh10, ll10); ev["E_CONSOL_BREAKOUT"] = pack(up & tight, dn & tight)
    sw_up = (h > hh20 + 0.1 * a) & (c < hh20); sw_dn = (l < ll20 - 0.1 * a) & (c > ll20)
    conf_dn = np.r_[False, sw_up[:-1]] & (c < sh(l)); conf_up = np.r_[False, sw_dn[:-1]] & (c > sh(h))
    ev["F_SWEEP_CONFIRM"] = pack(conf_up, conf_dn)                               # primario = reversion tras confirmacion
    out_up = np.r_[False, (c[:-1] > hh20[:-1])]; out_dn = np.r_[False, (c[:-1] < ll20[:-1])]
    fb_dn = out_up & (c <= sh(hh20)); fb_up = out_dn & (c >= sh(ll20))
    ev["G_FAILED_BREAKOUT"] = pack(fb_up, fb_dn)                                  # primario = fade del fallo
    s20, s50 = d.sma20.values, d.sma50.values
    mn3 = d.low.rolling(3).min().values; mx3 = d.high.rolling(3).max().values
    pb_up = (s20 > s50) & (c > s50) & (sh(c) <= sh(s20)) & (c > s20) & (mn3 <= s20)
    pb_dn = (s20 < s50) & (c < s50) & (sh(c) >= sh(s20)) & (c < s20) & (mx3 >= s20)
    ev["H_PULLBACK_TREND"] = pack(pb_up, pb_dn)
    return ev


def features(d: pd.DataFrame, idx: np.ndarray, dr: np.ndarray) -> pd.DataFrame:
    c, a = d.close.values, d.atr.values
    hh20 = d.high.rolling(20).max().values; ll20 = d.low.rolling(20).min().values
    ma = d.sma20.values
    f = pd.DataFrame(dict(
        vol_pct=(d.atr / d.close).values[idx], er30=d.er30.values[idx], speed3=(dr * (c[idx] - c[idx - 3]) / a[idx]),
        trend_align=np.sign(dr * (ma[idx] - d.sma50.values[idx])), range_pos=(c[idx] - ll20[idx]) / np.maximum(hh20[idx] - ll20[idx], 1e-9),
        compression=(d.high.rolling(10).max() - d.low.rolling(10).min()).values[idx] / a[idx], dist_ma_ATR=(dr * (c[idx] - ma[idx]) / a[idx]),
        spread_ATR=(d.spr.values[idx] / a[idx]), bar_range_ATR=(d.rng.values[idx] / a[idx]), hour=d.hour.values[idx]))
    return f


def cls(n_is, e_is, t_is, n_oos, e_oos, t_oos, n_all, e_all, tstar, e_c15, ci_oos_lo) -> str:
    if n_all < 30:
        return "F"
    if not (e_all > 0):
        return "D"
    if n_is >= 30 and e_is > 0 and t_is >= 2:
        if n_oos >= 15 and e_oos > 0 and t_oos >= 1.65:
            if t_is >= tstar and e_c15 > 0 and ci_oos_lo > 0:
                return "B"
            return "C"
        if n_oos >= 15 and e_oos <= 0:
            return "G"
        return "C"
    return "D" if e_is <= 0 else "C"


def main():
    rows, feats_all, reg_rows, reg_state = [], [], [], []
    pools = {}
    for tf in TFS:
        for s in SYMS:
            d = load_htf(s, tf); n = len(d)
            pool = V.build_pool(d)
            # ----- regimenes -----
            vol = d.atr / d.close; ret = d.close.diff()
            volq = vol.quantile([1 / 3, 2 / 3]).values; erq = d.er30.quantile([1 / 3, 2 / 3]).values
            vslope = vol / vol.shift(10)
            trend_dir = np.sign(d.close - d.sma50)
            f8 = d.close.shift(-8) - d.close; r8 = d.close.diff(8)
            lab = pd.DataFrame(dict(vr=np.digitize(vol, volq), tr=np.digitize(d.er30, erq), vs=np.where(vslope > 1.1, "creciente", np.where(vslope < 0.9, "decreciente", "estable")),
                                    td=np.where(trend_dir > 0, "alcista", "bajista"), sprh=np.where((d.spr / d.atr) > (d.spr / d.atr).median(), "spread_alto", "spread_bajo")))
            for key in ("vr", "tr", "vs", "td", "sprh"):
                for val, g in lab.groupby(key):
                    ix = g.index; ok = ix[(~r8.loc[ix].isna()) & (~f8.loc[ix].isna())]
                    names = {"vr": ["vol_baja", "vol_media", "vol_alta"], "tr": ["rango", "mixto", "tendencia"]}
                    reg_rows.append(dict(symbol=s, tf=tf, dimension=key, regime=names[key][val] if key in names else val, share_pct=round(100 * len(ix) / n, 1),
                                         p_momentum8_continues=round(float((np.sign(r8.loc[ok]) == np.sign(f8.loc[ok])).mean()), 3) if len(ok) else np.nan,
                                         mean_abs_next8_ATR=round(float((f8.loc[ix].abs() / d.atr.loc[ix]).mean()), 3), med_cost_ATR=round(float((d.spr / d.atr).loc[ix].median()), 5), n=len(ix)))
            # ----- eventos -----
            for fam, (idx, dr) in fam_events(d).items():
                good = (idx > 60)
                idx, dr = idx[good], dr[good]
                if len(idx) == 0:
                    rows.append(dict(symbol=s, tf=tf, family=fam, variant="-", split="ALL", n=0)); continue
                idx, dr, _ = V.dedupe(idx, dr, None)
                for var, sign in (("primary", 1), ("inverted", -1)):
                    ev = V.simulate(d, idx, dr * sign)
                    if len(ev) == 0:
                        continue
                    fe = features(d, ev.idx.values, ev.dir.values)
                    for split, m in (("IS", ev.time < SPLIT), ("OOS", ev.time >= SPLIT), ("ALL", ev.time > "1900")):
                        e = ev[np.asarray(m)]
                        r = V.summarize(e, dict(symbol=s, tf=tf, family=fam, variant=var, split=split), d, None)
                        if split in ("IS", "OOS") and len(e) >= 20:
                            cm, cp = V.control_pvalue(e, pool); r["control_mean_R1.5"] = round(cm, 4); r["p_vs_control"] = round(cp, 3)
                        rows.append(r)
                    ff = pd.concat([fe.reset_index(drop=True), ev[["time", "R_1.5", "R_3.0", "mfe", "mae"]].reset_index(drop=True)], axis=1)
                    ff.insert(0, "symbol", s); ff.insert(1, "tf", tf); ff.insert(2, "family", fam); ff.insert(3, "variant", var)
                    feats_all.append(ff)
            print(tf, s, "ok", n, flush=True)
    E = pd.DataFrame(rows)
    E.to_csv(OUT / "V8_H4_D1_EVENT_STUDY.csv", index=False)
    pd.DataFrame(reg_rows).to_csv(OUT / "V8_MARKET_REGIMES.csv", index=False)
    F = pd.concat(feats_all)
    F.to_pickle(ROOT / "results" / "v8" / "htf_features.pkl")
    # ---------- seleccion con multiplicidad ----------
    keys = ["symbol", "tf", "family", "variant"]
    reg = []
    for k, g in E[E.n > 0].groupby(keys):
        S = {r["split"]: r for r in g.to_dict("records")}
        if not {"IS", "OOS", "ALL"} <= set(S):
            continue
        for rr in V.RRS:
            reg.append(dict(zip(keys, k), rr=rr, n_is=S["IS"]["n"], expR_is=S["IS"].get(f"expR_net_{rr}R", np.nan), t_is=S["IS"].get(f"t_{rr}R", np.nan),
                            n_oos=S["OOS"]["n"], expR_oos=S["OOS"].get(f"expR_net_{rr}R", np.nan), t_oos=S["OOS"].get(f"t_{rr}R", np.nan),
                            ci_oos_lo=S["OOS"].get(f"ci95_lo_{rr}R", np.nan), ci_oos_hi=S["OOS"].get(f"ci95_hi_{rr}R", np.nan),
                            n_all=S["ALL"]["n"], expR_all=S["ALL"].get(f"expR_net_{rr}R", np.nan), t_all=S["ALL"].get(f"t_{rr}R", np.nan),
                            cost_ATR=S["ALL"].get("mean_cost_ATR", np.nan), p_ctrl_is=S["IS"].get("p_vs_control", np.nan), p_ctrl_oos=S["OOS"].get("p_vs_control", np.nan)))
    R = pd.DataFrame(reg)
    N = len(R); tstar = math.sqrt(2 * math.log(N))
    R["expR_oos_cost1p5"] = R.expR_oos - 0.5 * R.cost_ATR; R["expR_oos_cost2"] = R.expR_oos - 1.0 * R.cost_ATR; R["expR_oos_cost3"] = R.expR_oos - 2.0 * R.cost_ATR
    R["expR_all_cost2"] = R.expR_all - R.cost_ATR
    R["N_tests"] = N; R["t_star_multiplicity"] = round(tstar, 2)
    R["class"] = [cls(r.n_is, r.expR_is, r.t_is, r.n_oos, r.expR_oos, r.t_oos, r.n_all, r.expR_all, tstar, r.expR_oos_cost1p5, r.ci_oos_lo) for r in R.itertuples()]
    R.to_csv(OUT / "V8_ROBUSTNESS_RESULTS.csv", index=False)
    R[R["class"].isin(["B", "C", "G"])].sort_values("t_all", ascending=False).to_csv(OUT / "V8_STRATEGY_CANDIDATES.csv", index=False)
    top = R.dropna(subset=["t_oos"]).sort_values("t_oos", ascending=False).head(40).copy()
    top.insert(0, "nota", "corte temporal IS(<2025-07)->OOS(>=2025-07) con reglas fijas; OOS ya visto en V4/V5/V7 => NO independiente; top 40 por t_oos = seleccion post-hoc, NO validacion")
    top.to_csv(OUT / "V8_FORWARD_RESULTS.csv", index=False)
    print("N tests", N, "t*", round(tstar, 2)); print(R["class"].value_counts().to_string())
    print(R[R["class"].isin(["B", "C", "G"])].sort_values("t_all", ascending=False).head(15)[["symbol", "tf", "family", "variant", "rr", "n_is", "expR_is", "t_is", "n_oos", "expR_oos", "t_oos", "n_all", "expR_all", "t_all", "class"]].to_string())
    print("mean expR_all by family/tf:"); print(R.groupby(["tf", "family"]).expR_all.mean().round(3).unstack(0).to_string())


if __name__ == "__main__":
    main()




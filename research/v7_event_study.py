"""REMIX V7 lote 1: perfiles de mercado, sesiones, regimenes y estudio de entradas (10 mercados, M15, 2024-01 -> 2026-10-31).
Reglas fijadas ANTES de mirar resultados:
 - senal en el cierre de la barra i, entrada en la APERTURA de i+1 (sin look-ahead), coste = spread real de la barra de entrada (round trip ~ 1 spread),
 - SL de medicion = 1 ATR(14) conocido en i; TP en {0.5,1,1.5,2,3} R; horizonte maximo 40 velas; SL antes que TP si ambos en la misma vela,
 - IS = hasta 2025-06-30; OOS = 2025-07-01..2026-10-31 (ambos ya vistos en V4/V5 => OOS NO es independiente; el holdout limpio es > 2026-11-01),
 - candidato: IS expR_neta(1.5R)>0, t_IS>=2, n_IS>=100; promocion B solo si OOS expR>0 y t_OOS>=1.65; multiplicidad t*=sqrt(2 ln N_total).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "raw" / "v7"
OUT = ROOT / "research"
SYMS = ["EURUSDm", "GBPUSDm", "USDJPYm", "XAUUSDm", "XAGUSDm", "US30m", "US500m", "USTECm", "BTCUSDm", "ETHUSDm"]
HZ = [1, 3, 5, 10, 20, 40]
RRS = [0.5, 1.0, 1.5, 2.0, 3.0]
MAXH = 40
SPLIT = pd.Timestamp("2025-07-01")
COOL = 12
RNG = np.random.default_rng(20261110)
INFO = json.load(open(D / "download_info.json"))
import os
TF = os.environ.get("V7_TF", "M15")           # M15 (lote 1) o H1 (lote 2: mismo estudio con coste/ATR menor)
SUF = "" if TF == "M15" else "_" + TF


def load(s: str) -> pd.DataFrame:
    d = pd.read_csv(D / f"{s}_M15.csv", parse_dates=["time"])
    d = d.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    if TF == "H1":
        d = d.set_index("time").resample("1h").agg(dict(open="first", high="max", low="min", close="last", tick_volume="sum", spread="mean", real_volume="sum")).dropna(subset=["open"]).reset_index()
    d["spr"] = d.spread * INFO[s]["point"]
    pc = d.close.shift(1)
    tr = np.maximum(d.high - d.low, np.maximum((d.high - pc).abs(), (d.low - pc).abs()))
    d["atr"] = tr.rolling(14).mean()
    d["er30"] = (d.close - d.close.shift(30)).abs() / d.close.diff().abs().rolling(30).sum()
    d["er8"] = (d.close - d.close.shift(8)).abs() / d.close.diff().abs().rolling(8).sum()
    dl = d.close.diff()
    up, dn = dl.clip(lower=0).rolling(14).mean(), (-dl.clip(upper=0)).rolling(14).mean()
    d["rsi"] = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    d["day"] = d.time.dt.normalize()
    g = d.groupby("day")
    dh, dlw = g.high.max(), g.low.min()
    d["pdh"] = d.day.map(dh.shift(1)); d["pdl"] = d.day.map(dlw.shift(1))
    d["hour"] = d.time.dt.hour
    d["rng"] = d.high - d.low
    return d


# ---------------- generadores de eventos: devuelven (indices_senal, direcciones) ----------------
def ev_sweep_pd(d):
    a = d.atr.values; h, l, c = d.high.values, d.low.values, d.close.values
    s = (h > d.pdh.values + 0.1 * a) & (c < d.pdh.values); b = (l < d.pdl.values - 0.1 * a) & (c > d.pdl.values)
    dist = np.where(s, (h - d.pdh.values) / a, np.where(b, (d.pdl.values - l) / a, np.nan))
    return np.where(s | b)[0], np.where(s, -1, 1)[s | b], dist[s | b]


def ev_sweep_96(d):
    a = d.atr.values; h, l, c = d.high.values, d.low.values, d.close.values
    ph = d.high.rolling(96).max().shift(1).values; pl = d.low.rolling(96).min().shift(1).values
    s = (h > ph + 0.1 * a) & (c < ph); b = (l < pl - 0.1 * a) & (c > pl)
    dist = np.where(s, (h - ph) / a, np.where(b, (pl - l) / a, np.nan))
    return np.where(s | b)[0], np.where(s, -1, 1)[s | b], dist[s | b]


def _breaks(d, n=48):
    c = d.close.values
    ph = d.high.rolling(n).max().shift(1).values; pl = d.low.rolling(n).min().shift(1).values
    up = (c > ph) & (np.r_[False, c[:-1] <= ph[:-1]]); dn = (c < pl) & (np.r_[False, c[:-1] >= pl[:-1]])
    return up, dn, ph, pl


def ev_breakout(d):
    up, dn, _, _ = _breaks(d)
    idx = np.where(up | dn)[0]
    return idx, np.where(up[idx], 1, -1), None


def ev_bo_retest(d):
    up, dn, ph, pl = _breaks(d)
    a = d.atr.values; h, l, c = d.high.values, d.low.values, d.close.values
    I, Dr = [], []
    for b in np.where(up | dn)[0]:
        long = up[b]; lvl = ph[b] if long else pl[b]
        for j in range(b + 1, min(b + 9, len(d) - 1)):
            if long:
                if c[j] < lvl - 0.5 * a[b]: break
                if l[j] <= lvl + 0.25 * a[b] and c[j] > lvl: I.append(j); Dr.append(1); break
            else:
                if c[j] > lvl + 0.5 * a[b]: break
                if h[j] >= lvl - 0.25 * a[b] and c[j] < lvl: I.append(j); Dr.append(-1); break
    return np.array(I, int), np.array(Dr, int), None


def ev_mom(d):
    a = d.atr.values; r8 = ((d.close - d.close.shift(8)) / d.atr).values
    m = (np.abs(r8) > 3) & (d.er8.values > 0.6)
    idx = np.where(m)[0]
    return idx, np.sign(r8[idx]).astype(int), None


def ev_volexp(d):
    a = d.atr.values; r12 = d.rng.rolling(12).max().values
    q = pd.Series(r12 / a).rolling(500).quantile(0.2).values
    comp_prev = np.r_[False, (r12[:-1] / a[:-1]) <= q[:-1]]
    pos = (d.close - d.low).values / np.where(d.rng.values == 0, np.nan, d.rng.values)
    big = d.rng.values > 1.5 * a
    up = comp_prev & big & (pos >= 0.75); dn = comp_prev & big & (pos <= 0.25)
    idx = np.where(up | dn)[0]
    return idx, np.where(up[idx], 1, -1), None


def ev_mr_regime(d):
    lo = (d.er30.values < 0.2) & (d.rsi.values < 20); hi = (d.er30.values < 0.2) & (d.rsi.values > 80)
    idx = np.where(lo | hi)[0]
    return idx, np.where(lo[idx], 1, -1), None


def ev_fvg(d):
    h, l, c, a = d.high.values, d.low.values, d.close.values, d.atr.values
    I, Dr = [], []
    for i in range(2, len(d) - 2):
        if l[i] - h[i - 2] >= 0.3 * a[i]:                         # FVG alcista: zona [h[i-2], l[i]]
            for j in range(i + 1, min(i + 21, len(d) - 1)):
                if l[j] <= l[i] and c[j] > h[i - 2]: I.append(j); Dr.append(1); break
                if c[j] < h[i - 2]: break
        elif l[i - 2] - h[i] >= 0.3 * a[i]:                      # FVG bajista: zona [h[i], l[i-2]]
            for j in range(i + 1, min(i + 21, len(d) - 1)):
                if h[j] >= h[i] and c[j] < l[i - 2]: I.append(j); Dr.append(-1); break
                if c[j] > l[i - 2]: break
    return np.array(I, int), np.array(Dr, int), None


def _structure(d, k=3):
    h, l = d.high.values, d.low.values
    n = len(d)
    ph = np.full(n, np.nan); pl = np.full(n, np.nan)             # ultimo pivote CONFIRMADO (confirmacion k velas despues => sin look-ahead)
    prev_pl = np.full(n, np.nan); prev_ph = np.full(n, np.nan)
    ch, cl, pch, pcl = np.nan, np.nan, np.nan, np.nan
    for i in range(n):
        j = i - k
        if j >= k:
            if h[j] == h[j - k:j + k + 1].max(): ph_new = h[j]; pch, ch = ch, ph_new
            if l[j] == l[j - k:j + k + 1].min(): pl_new = l[j]; pcl, cl = cl, pl_new
        ph[i], pl[i], prev_ph[i], prev_pl[i] = ch, cl, pch, pcl
    return ph, pl, prev_ph, prev_pl


def ev_bos(d, choch=False):
    c = d.close.values
    ph, pl, pph, ppl = _structure(d)
    I, Dr = [], []
    for i in range(1, len(d) - 1):
        if not np.isnan(ph[i]) and c[i] > ph[i] and c[i - 1] <= ph[i]:
            if not choch or (ppl[i] > pl[i]): I.append(i); Dr.append(1)       # CHoCH: venia con minimos decrecientes
        elif not np.isnan(pl[i]) and c[i] < pl[i] and c[i - 1] >= pl[i]:
            if not choch or (pph[i] < ph[i]): I.append(i); Dr.append(-1)
    return np.array(I, int), np.array(Dr, int), None


def ev_choch(d):
    return ev_bos(d, True)


def _orb(d, hh):
    I, Dr = [], []
    for day, g in d.groupby("day"):
        w = g[(g.hour == hh) ]
        if len(w) < 4: continue
        hi, lo = w.high.max(), w.low.min(); end = w.index[-1]
        for j in range(end + 1, min(end + 17, len(d) - 1)):
            if d.close.values[j] > hi: I.append(j); Dr.append(1); break
            if d.close.values[j] < lo: I.append(j); Dr.append(-1); break
    return np.array(I, int), np.array(Dr, int), None


def ev_orb_lon(d): return _orb(d, 8)
def ev_orb_ny(d): return _orb(d, 14)


EVENTS = {"E01_SWEEP_PD": ev_sweep_pd, "E02_SWEEP_96": ev_sweep_96, "E03_BREAKOUT": ev_breakout, "E04_BO_RETEST": ev_bo_retest, "E05_MOMENTUM": ev_mom,
          "E06_VOL_EXPANSION": ev_volexp, "E07_MR_REGIME": ev_mr_regime, "E08_FVG": ev_fvg, "E09_BOS": ev_bos, "E10_CHOCH": ev_choch,
          "E11_ORB_LONDON": ev_orb_lon, "E12_ORB_NY": ev_orb_ny}


def simulate(d, idx, dr):
    """Para cada senal: retornos a horizontes, MFE/MAE, tiempos, R netos por RR. Todo en unidades de ATR(i). Devuelve DataFrame."""
    n = len(d)
    o, h, l, c, a, sp = (d[k].values for k in ("open", "high", "low", "close", "atr", "spr"))
    keep = (idx + 1 + MAXH < n) & ~np.isnan(a[idx]) & (a[idx] > 0)
    idx, dr = idx[keep], dr[keep]
    if len(idx) == 0:
        return pd.DataFrame()
    e = o[idx + 1]; at = a[idx]; cost = sp[idx + 1] / at
    off = np.arange(1, MAXH + 1)
    H = h[idx[:, None] + off]; L = l[idx[:, None] + off]; C = c[idx[:, None] + off]
    fav = np.where(dr[:, None] > 0, H - e[:, None], e[:, None] - L) / at[:, None]
    adv = np.where(dr[:, None] > 0, e[:, None] - L, H - e[:, None]) / at[:, None]
    res = dict(idx=idx, time=d.time.values[idx], hour=d.hour.values[idx], dir=dr, cost=cost, er=d.er30.values[idx])
    for hz in HZ:
        res[f"gross_h{hz}"] = dr * (C[:, hz - 1] - e) / at
    res["mfe"] = fav.max(1); res["mae"] = adv.max(1)
    res["t_mfe"] = fav.argmax(1) + 1; res["t_mae"] = adv.argmax(1) + 1
    sl_t = np.where((adv >= 1).any(1), (adv >= 1).argmax(1), 999)
    tmo = np.clip(dr * (C[:, -1] - e) / at, -1, None)
    for k in RRS:
        tp_t = np.where((fav >= k).any(1), (fav >= k).argmax(1), 999)
        tp_first = tp_t < sl_t                                       # empate (misma vela) => SL primero
        R = np.where(tp_first, k, np.where(sl_t < 999, -1.0, np.minimum(tmo, k)))
        res[f"hit_{k}"] = tp_first.astype(float); res[f"R_{k}"] = R - cost
    res["p_sl"] = (sl_t < 999).astype(float)
    return pd.DataFrame(res)


def dedupe(idx, dr, extra=None):
    keep, last = [], -10**9
    for k, i in enumerate(idx):
        if i - last >= COOL: keep.append(k); last = i
    keep = np.array(keep, int)
    return idx[keep], dr[keep], (None if extra is None else extra[keep])


def tstat(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 3 or x.std(ddof=1) == 0: return np.nan, np.nan
    se = x.std(ddof=1) / math.sqrt(len(x))
    return x.mean() / se, se


def summarize(ev: pd.DataFrame, label: dict, d_all: pd.DataFrame, ctrl_idx_by_hour) -> dict:
    row = dict(label); row["n"] = len(ev)
    if len(ev) == 0:
        return row
    for hz in HZ:
        g = ev[f"gross_h{hz}"]
        row[f"mean_gross_h{hz}"] = round(g.mean(), 4); row[f"median_gross_h{hz}"] = round(g.median(), 4)
        row[f"mean_net_h{hz}"] = round((g - ev.cost).mean(), 4); row[f"p_cont_h{hz}"] = round((g > 0).mean(), 3); row[f"p_rev_h{hz}"] = round((g < 0).mean(), 3)
    row["mean_cost_ATR"] = round(ev.cost.mean(), 4)
    row["mfe_mean"] = round(ev.mfe.mean(), 3); row["mae_mean"] = round(ev.mae.mean(), 3)
    row["t_mfe_med"] = float(ev.t_mfe.median()); row["t_mae_med"] = float(ev.t_mae.median())
    for k in RRS:
        row[f"p_hit_{k}R"] = round(ev[f"hit_{k}"].mean(), 3)
        t, se = tstat(ev[f"R_{k}"]); m = ev[f"R_{k}"].mean()
        row[f"expR_net_{k}R"] = round(m, 4); row[f"t_{k}R"] = round(t, 2) if t == t else np.nan
        row[f"ci95_lo_{k}R"] = round(m - 1.96 * se, 4) if se == se else np.nan; row[f"ci95_hi_{k}R"] = round(m + 1.96 * se, 4) if se == se else np.nan
    row["p_sl"] = round(ev.p_sl.mean(), 3)
    row["expR_gross_1.5R"] = round((ev["R_1.5"] + ev.cost).mean(), 4)
    # control aleatorio: misma hora, direccion aleatoria, misma terciles de ER; 100 sorteos, estadistico = media R(1.5R)
    return row


def control_pvalue(ev: pd.DataFrame, pool: pd.DataFrame, nsim=100) -> tuple[float, float]:
    """pool: todas las barras simuladas (direccion +1) con R_1.5 para long y short precalculados -> control condicionado por hora y tercil de ER."""
    if len(ev) < 20: return np.nan, np.nan
    obs = ev["R_1.5"].mean()
    terc = np.digitize(ev.er.values, pool.attrs["er_q"]); ph = ev.hour.values
    sims = np.empty(nsim)
    key = pool.groupby(["hour", "terc"]).indices
    for s in range(nsim):
        tot = 0.0
        for hh, tt in zip(ph, terc):
            ids = key.get((hh, tt))
            if ids is None: tot += 0; continue
            j = ids[RNG.integers(len(ids))]
            tot += pool.R_long.values[j] if RNG.random() < 0.5 else pool.R_short.values[j]
        sims[s] = tot / len(ev)
    return float(sims.mean()), float((sims >= obs).mean())


def build_pool(d):
    """R(1.5R) de largos y cortos en TODAS las barras (muestra de 1 de cada 3 para ahorrar memoria)."""
    idx = np.arange(60, len(d) - MAXH - 2, 3)
    L = simulate(d, idx, np.ones(len(idx), int)); S = simulate(d, idx, -np.ones(len(idx), int))
    n = min(len(L), len(S)); L, S = L.iloc[:n], S.iloc[:n]
    p = pd.DataFrame(dict(hour=L.hour.values, er=L.er.values, R_long=L["R_1.5"].values, R_short=S["R_1.5"].values))
    q = np.nanquantile(p.er.values, [1 / 3, 2 / 3]); p["terc"] = np.digitize(p.er.values, q); p.attrs["er_q"] = q
    return p.dropna()


def main():
    profiles, sessions, regimes, liq, entries, reg = [], [], [], [], [], []
    for s in SYMS:
        d = load(s); n = len(d)
        # ---------- perfil ----------
        ret = np.log(d.close).diff()
        dr = d.groupby("day").close.last().pipe(np.log).diff().dropna()
        exp_dt = d.time.diff().dt.total_seconds().div(60)
        gaps = d.close.shift(1).sub(d.open).abs() / d.atr
        vr = lambda q: float(ret.rolling(q).sum().var() / (q * ret.var()))
        spr_atr = (d.spr / d.atr)
        profiles.append(dict(symbol=s, bars=n, first=str(d.time.iloc[0]), last=str(d.time.iloc[-1]), duplicates_removed=int(pd.read_csv(D / f"{s}_M15.csv").shape[0] - n),
                             gaps_gt_1h=int((exp_dt > 60).sum()), gaps_gt_1d=int((exp_dt > 1440).sum()), open_gaps_gt_2ATR=int((gaps > 2).sum()),
                             zero_range_pct=round(float((d.rng == 0).mean() * 100), 2), med_spread_points=float(d.spread.median()),
                             med_spread_price=float(d.spr.median()), med_cost_per_trade_ATR=round(float(spr_atr.median()), 4), atr_pct_price=round(float((d.atr / d.close).median() * 100), 4),
                             daily_ret_mean_pct=round(float(dr.mean() * 100), 4), daily_ret_std_pct=round(float(dr.std() * 100), 3), daily_skew=round(float(dr.skew()), 2),
                             daily_kurt=round(float(dr.kurt()), 2), ac1=round(float(ret.autocorr(1)), 4), ac2=round(float(ret.autocorr(2)), 4), ac5=round(float(ret.autocorr(5)), 4),
                             var_ratio_4=round(vr(4), 3), var_ratio_16=round(vr(16), 3), mean_ER30=round(float(d.er30.mean()), 3), min_lot=INFO[s]["min_lot"],
                             lot_step=INFO[s]["step"], contract=INFO[s]["contract"], tick_volume_median=float(d.tick_volume.median()),
                             note="spread bar-level real; sin comision (Exness Standard); tick_volume = proxy de actividad, no volumen real"))
        # ---------- sesiones ----------
        d["absret"] = ret.abs(); d["dow"] = d.time.dt.dayofweek
        for hh, g in d.groupby("hour"):
            sessions.append(dict(symbol=s, kind="hour_utc", key=int(hh), n=len(g), mean_ret_bp=round(float(ret.loc[g.index].mean() * 1e4), 3), mean_abs_ret_bp=round(float(g.absret.mean() * 1e4), 3),
                                 med_spread_ATR=round(float((g.spr / g.atr).median()), 4), mean_ER8=round(float(g.er8.mean()), 3), med_tick_volume=float(g.tick_volume.median())))
        for k, g in d.groupby("dow"):
            sessions.append(dict(symbol=s, kind="weekday", key=int(k), n=len(g), mean_ret_bp=round(float(ret.loc[g.index].mean() * 1e4), 3), mean_abs_ret_bp=round(float(g.absret.mean() * 1e4), 3),
                                 med_spread_ATR=round(float((g.spr / g.atr).median()), 4), mean_ER8=round(float(g.er8.mean()), 3), med_tick_volume=float(g.tick_volume.median())))
        # ---------- regimenes ----------
        vol = (d.atr / d.close); vq = vol.quantile([1 / 3, 2 / 3]).values; eq = d.er30.quantile([1 / 3, 2 / 3]).values
        d["volreg"] = np.digitize(vol, vq); d["trreg"] = np.digitize(d.er30, eq)
        r8 = d.close.diff(8); f8 = d.close.shift(-8) - d.close
        for (vr_, tr_), g in d.groupby(["volreg", "trreg"]):
            ok = g.index[(~r8.loc[g.index].isna()) & (~f8.loc[g.index].isna())]
            cont = float((np.sign(r8.loc[ok]) == np.sign(f8.loc[ok])).mean()) if len(ok) else np.nan
            regimes.append(dict(symbol=s, vol_regime=["baja", "media", "alta"][vr_], trend_regime=["rango", "mixto", "tendencia"][tr_], share_pct=round(100 * len(g) / n, 1),
                                p_momentum8_continues=round(cont, 4), mean_abs_next8_ATR=round(float((f8.loc[g.index].abs() / g.atr).mean()), 3), med_cost_ATR=round(float((g.spr / g.atr).median()), 4)))
        # ---------- entradas ----------
        pool = build_pool(d)
        for ename, fn in EVENTS.items():
            if TF == "H1" and ename.startswith(("E11", "E12")): continue
            out = fn(d)
            idx, dirs, extra = out
            if len(idx) == 0:
                reg.append(dict(symbol=s, event=ename, status="SIN_EVENTOS")); continue
            idx, dirs, extra = dedupe(idx, dirs, extra)
            for var, sign in (("primary", 1), ("inverted", -1)):
                ev = simulate(d, idx, dirs * sign)
                if len(ev) == 0: continue
                if extra is not None: ev["sweep_dist_ATR"] = extra[:len(ev)] if len(extra) >= len(ev) else np.nan
                for split, m in (("IS", ev.time < SPLIT), ("OOS", ev.time >= SPLIT), ("ALL", ev.time > "1900")):
                    e = ev[m.values] if hasattr(m, "values") else ev[m]
                    row = summarize(e, dict(symbol=s, event=ename, variant=var, split=split), d, None)
                    if split in ("IS", "OOS") and len(e) >= 20:
                        cm, cp = control_pvalue(e, pool); row["control_mean_R1.5"] = round(cm, 4); row["p_vs_control"] = round(cp, 3)
                    entries.append(row)
                if ename.startswith("E01") or ename.startswith("E02"):
                    if var == "primary" and "sweep_dist_ATR" in ev:
                        ev["terc"] = pd.qcut(ev.sweep_dist_ATR, 3, labels=["corta", "media", "larga"], duplicates="drop")
                        for tt, g in ev.groupby("terc", observed=True):
                            liq.append(dict(symbol=s, event=ename, sweep_dist_tercile=tt, n=len(g), sweep_dist_med_ATR=round(float(g.sweep_dist_ATR.median()), 3), p_reversal_h10=round(float((g.gross_h10 > 0).mean()), 3),
                                            expR_net_1R=round(float(g["R_1.0"].mean()), 4), expR_net_1p5R=round(float(g["R_1.5"].mean()), 4), mfe_med=round(float(g.mfe.median()), 3),
                                            t_mfe_med=float(g.t_mfe.median()), by_session_london_share=round(float(g.hour.between(7, 11).mean()), 3), by_session_ny_share=round(float(g.hour.between(13, 17).mean()), 3)))
            print(s, "ok", flush=True)
    if TF == "M15":
        pd.DataFrame(profiles).to_csv(OUT / "V7_MARKET_PROFILES.csv", index=False)
        pd.DataFrame(sessions).to_csv(OUT / "V7_SESSION_ANALYSIS.csv", index=False)
        pd.DataFrame(regimes).to_csv(OUT / "V7_MARKET_REGIMES.csv", index=False)
        pd.DataFrame(reg).to_csv(OUT / "V7_EVENT_SKIPPED.csv", index=False)
    pd.DataFrame(liq).to_csv(OUT / f"V7_LIQUIDITY_RESEARCH{SUF}.csv", index=False)
    E = pd.DataFrame(entries); E.to_csv(OUT / f"V7_ENTRY_ANALYSIS{SUF}.csv", index=False)


if __name__ == "__main__":
    main()



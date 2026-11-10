"""V10 Lote A - auditoria de las 248 operaciones oficiales de XAUUSDm H4 (Lookback 20, SL 1 ATR, TP 3R, cooldown 6, hold 40, lote 0,01) y comparacion con referencias simples.
Estrategia CONGELADA: nada se optimiza. Las 248 operaciones salen del trades.csv oficial del Strategy Tester (hash verificado contra results/v9/XAU_FROZEN.json).
Referencias (benchmarks) en el motor Python de V8 (misma regla de salida, SL gana empate, coste = spread de la vela de entrada). Controles aleatorios con semilla fija."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from research.v10_common import (H, R1, RES, V, block_boot, bars, m15, max_dd, norm_cdf, norm_ppf, official_h4, pf, split_of, summ, tstat)
from research import v8_lote_c_h4 as C4
from research.v10_macro import calendar

SEED = 20261111
MAXH = 40
RR = 3.0


EA_TRADES = RES.parent / "results" / "v8" / "RUN_20261110_XAUUSDm_H4_V8_XAU_BREAKOUT_V8H4A1_RR3.0_ohlc_1m_013" / "ea_trades.csv"


def prep():
    """Usa el registro del EA (ea_trades.csv, clave position_id) y NO el trades.csv: este ultimo empareja cierre-apertura por orden (FIFO) y, cuando dos posiciones
    coinciden, cruza hora/precio de cierre entre ellas (hallazgo V10). Los totales coinciden; los atributos por operacion no. Se concilia con el trades.csv oficial."""
    d = bars("H4")
    off = official_h4(3)                                          # verifica el hash congelado
    e = pd.read_csv(EA_TRADES)
    for c in ("open_time", "close_time"):
        e[c] = pd.to_datetime(e[c].astype(str).str.replace(r"\s+", " ", regex=True), format="%Y.%m.%d %H:%M:%S")
    e = e.sort_values("open_time").reset_index(drop=True)
    assert len(e) == len(off) == 248
    net_off, net_ea = off.pnl.sum(), (e.profit + e.swap + e.commission).sum()
    assert abs(net_off - net_ea) < 0.02, (net_off, net_ea)        # el neto oficial coincide con el registro del EA
    assert (e.open_time.values == off.sort_values("open_time").open_time.values).all()
    mis = int(((off.sort_values("open_time").close_time.values != e.close_time.values)).sum())
    t = pd.DataFrame(dict(open_time=e.open_time, close_time=e.close_time, dir=e.dir.astype(int), price_open=e.entry, price_close=e.exit, swap=e.swap, commission=e.commission,
                          pnl=e.profit + e.swap + e.commission, risk=e.sl_dist, comment=e.exit_reason.str.lower(), MFE_R=e.mfe_R, MAE_R=e.mae_R, bars_held_ea=e.bars_held, position_id=e.position_id))
    t.attrs["trades_csv_closetime_mismatch"] = mis
    pos = {x: i for i, x in enumerate(d.time)}
    t["ie"] = t.open_time.map(pos); assert t.ie.notna().all(); t["ie"] = t.ie.astype(int); t["isg"] = t.ie - 1
    t["R"] = t.pnl / t.risk
    t["hold_days"] = (t.close_time - t.open_time).dt.total_seconds() / 86400
    t["spr"] = d.spr.values[t.ie]; t["spr_R"] = t.spr / t.risk
    t["er30"] = d.er30.values[t.isg]; t["atrp"] = t.risk / d.close.values[t.isg]
    t["trend_al"] = np.sign(d.close.values[t.isg] - d.sma50.values[t.isg]) * t.dir
    t["trend_long"] = np.sign(d.close.values[t.isg] - d.close.rolling(300).mean().values[t.isg]) * t.dir
    t["hour"] = t.open_time.dt.hour
    t["exit_why"] = t.comment.str.upper().replace({"TIME": "TIME (40 velas)"})
    t["split"] = [split_of(x) for x in t.open_time]
    cal = calendar(); ev = cal.utc.values
    def news(x, hrs=24):
        k = np.searchsorted(ev, np.datetime64(x)) - 1
        return bool(k >= 0 and (np.datetime64(x) - ev[k]) <= np.timedelta64(hrs, "h"))
    t["post_news24"] = [news(x) for x in t.open_time]
    t["event_day"] = t.open_time.dt.normalize().isin(set(cal.utc.dt.normalize()))
    return d, t


def _prep_trades_csv():
    d = bars("H4")
    t = official_h4(3)
    pos = {x: i for i, x in enumerate(d.time)}
    t["ie"] = t.open_time.map(pos)
    assert t.ie.notna().all(), "operaciones oficiales sin vela H4 coincidente"
    t["ie"] = t.ie.astype(int); t["isg"] = t.ie - 1
    t["risk_atr"] = d.atr.values[t.isg]                                # SL = 1 ATR(14) de la vela de senal (Python; falta en las primeras velas: el terminal tenia mas historia)
    px = t.comment.str.extract(r"(sl|tp)\s+([0-9.]+)")
    lvl = pd.to_numeric(px[1], errors="coerce")
    r_c = np.where(px[0] == "sl", (t.price_open - lvl).abs(), np.where(px[0] == "tp", (lvl - t.price_open).abs() / RR, np.nan))
    t["risk"] = t.risk_atr.fillna(pd.Series(r_c))                      # ATR de la vela de senal; solo donde falta (1a operacion) se usa el nivel SL/TP del probador
    ok = t.risk_atr.notna() & pd.Series(r_c).notna()
    assert (abs(pd.Series(r_c)[ok] / t.risk_atr[ok] - 1) < 0.01).mean() > 0.90, "riesgo del comentario vs ATR Python no coincide"   # el resto: relleno con hueco (precio de salida != nivel)
    assert t.risk.notna().all()
    t["R"] = t.pnl / t.risk                                              # lote 0,01 XAU = 1 oz -> USD por dolar de precio
    t["hold_bars"] = ((t.close_time - t.open_time).dt.total_seconds() / 14400).round(2)
    t["hold_days"] = (t.close_time - t.open_time).dt.total_seconds() / 86400
    t["spr"] = d.spr.values[t.ie]; t["spr_R"] = t.spr / t.risk
    t["er30"] = d.er30.values[t.isg]; t["atrp"] = (d.atr / d.close).values[t.isg]
    t["trend_al"] = np.sign(d.close.values[t.isg] - d.sma50.values[t.isg]) * t.dir          # a favor (+1) o en contra (-1) de la SMA50 H4 (~8 dias)
    t["trend_long"] = np.sign(d.close.values[t.isg] - d.close.rolling(300).mean().values[t.isg]) * t.dir   # 300 velas H4 ~ 50 dias
    t["hour"] = t.open_time.dt.hour
    t["exit_why"] = np.where(t.comment.str.startswith("sl"), "SL", np.where(t.comment.str.startswith("tp"), "TP", "TIME/OTRA"))
    # MFE / MAE (en R) con M15 entre apertura y cierre
    M = m15(); mt = M.time.values; hh, ll = M.high.values, M.low.values
    mf, ma = [], []
    for _, r in t.iterrows():
        a, b = np.searchsorted(mt, np.datetime64(r.open_time)), np.searchsorted(mt, np.datetime64(r.close_time), side="right")
        h_, l_ = hh[a:b].max(), ll[a:b].min()
        up, dn = (h_ - r.price_open) / r.risk, (r.price_open - l_) / r.risk
        mf.append(up if r.dir > 0 else dn); ma.append(dn if r.dir > 0 else up)
    t["MFE_R"], t["MAE_R"] = mf, ma
    t["split"] = [split_of(x) for x in t.open_time]
    # noticias: entrada dentro de las 24 h posteriores a un NFP/CPI/FOMC
    cal = calendar()
    ev = cal.utc.values
    def news(x, hrs=24):
        k = np.searchsorted(ev, np.datetime64(x)) - 1
        return bool(k >= 0 and (np.datetime64(x) - ev[k]) <= np.timedelta64(hrs, "h"))
    t["post_news24"] = [news(x) for x in t.open_time]
    t["event_day"] = t.open_time.dt.normalize().isin(set(cal.utc.dt.normalize()))
    return d, t


def tercile(s, names=("bajo", "medio", "alto")):
    return pd.qcut(s, 3, labels=names)


def rows_for(t, dim, key):
    out = []
    for b, g in t.groupby(key, observed=True):
        s = summ(g.R)
        out.append(dict(dimension=dim, bucket=str(b), n=s["n"], net_usd=round(g.pnl.sum(), 2), expR=s["expR"], t=s["t"], pf=s["pf"], win=s["win"],
                        share_of_net=round(g.pnl.sum() / t.pnl.sum(), 3), mean_hold_days=round(g.hold_days.mean(), 2), mean_MFE_R=round(g.MFE_R.mean(), 2), mean_MAE_R=round(g.MAE_R.mean(), 2)))
    return out


def global_stats(t, d):
    R = t.R.values; pnl = t.pnl.values
    bal = 3000 + np.cumsum(pnl); peak = np.maximum.accumulate(np.r_[3000, bal])[1:]
    dd = peak - bal; k = int(np.argmax(dd)); ddp = float((dd / peak).max() * 100)
    # recuperacion tras el peor DD
    rec = next((j for j in range(k, len(bal)) if bal[j] >= peak[k]), None)
    rec_days = (t.close_time.iloc[rec] - t.close_time.iloc[k]).days if rec is not None else None
    # racha negativa
    streak = best = 0; sstreak = ssum = worst_sum = 0.0
    for p in pnl:
        if p < 0:
            streak += 1; ssum += p; best = max(best, streak); worst_sum = min(worst_sum, ssum)
        else:
            streak = 0; ssum = 0.0
    # periodo bajo el agua (dias entre maximos consecutivos)
    hi_idx = np.where(bal >= peak - 1e-9)[0]; gaps = np.diff(np.r_[hi_idx, len(bal) - 1]); longest_uw_trades = int(gaps.max())
    ct = t.close_time.values
    uw_days = max(((ct[min(b, len(ct) - 1)] - ct[a]) / np.timedelta64(1, "D") for a, b in zip(hi_idx, np.r_[hi_idx[1:], len(bal) - 1])), default=0)
    gross = pnl[pnl > 0].sum()
    srt = np.sort(pnl)[::-1]
    g = dict(n=len(t), net_usd=round(pnl.sum(), 2), pf=round(pf(pnl), 3), expR=round(R.mean(), 4), t=round(tstat(R), 2), win=round((pnl > 0).mean(), 3),
             avg_win_usd=round(pnl[pnl > 0].mean(), 2), avg_loss_usd=round(pnl[pnl < 0].mean(), 2),
             max_dd_balance_usd=round(float(dd.max()), 2), max_dd_balance_pct=round(ddp, 2), recovery_days_after_worst_dd=rec_days if rec_days is not None else "NO_RECUPERADO",
             longest_underwater_days=round(float(uw_days), 0), longest_underwater_trades=longest_uw_trades, longest_losing_streak=best, worst_streak_sum_usd=round(worst_sum, 2),
             best_trade_usd=round(float(srt[0]), 2), worst_trade_usd=round(float(srt[-1]), 2), best_trade_pct_of_net=round(float(srt[0] / pnl.sum()), 3),
             top3_share_of_gross=round(float(srt[:3].sum() / gross), 3), top5_share_of_gross=round(float(srt[:5].sum() / gross), 3), top10_share_of_gross=round(float(srt[:10].sum() / gross), 3),
             net_without_top1=round(float(pnl.sum() - srt[0]), 2), net_without_top3=round(float(pnl.sum() - srt[:3].sum()), 2), net_without_top5=round(float(pnl.sum() - srt[:5].sum()), 2),
             pf_without_top5=round(pf(np.sort(pnl)[:-5]), 3),
             spread_paid_usd=round(float(t.spr.sum()), 2), swap_usd=round(float(t.swap.sum()), 2), spread_R_mean=round(float(t.spr_R.mean()), 4),
             mean_MFE_R=round(float(t.MFE_R.mean()), 2), mean_MAE_R=round(float(t.MAE_R.mean()), 2),
             pct_trades_MFE_ge_1R=round(float((t.MFE_R >= 1).mean()), 3), pct_losers_with_MFE_ge_1R=round(float((t[t.pnl < 0].MFE_R >= 1).mean()), 3))
    # concentracion temporal
    mo = t.groupby(t.close_time.dt.to_period("M")).pnl.sum()
    g.update(months=len(mo), pct_months_positive=round(float((mo > 0).mean()), 3), best_month_usd=round(float(mo.max()), 2), best_month=str(mo.idxmax()),
             best_month_share_of_net=round(float(mo.max() / pnl.sum()), 3), top3_months_share_of_net=round(float(mo.sort_values(ascending=False)[:3].sum() / pnl.sum()), 3),
             net_without_best_month=round(float(pnl.sum() - mo.max()), 2), min_leave_one_month_out=round(float(pnl.sum() - mo.max()), 2), max_leave_one_month_out=round(float(pnl.sum() - mo.min()), 2))
    # bootstrap por bloques (8 operaciones) de la expectativa y del PF
    bm = block_boot(R, 8, 4000, SEED); bp = block_boot(pnl, 8, 4000, SEED + 1, stat=pf)
    g.update(boot_expR_lo=round(float(np.percentile(bm, 2.5)), 4), boot_expR_hi=round(float(np.percentile(bm, 97.5)), 4), boot_p_expR_le0=round(float((bm <= 0).mean()), 4),
             boot_pf_lo=round(float(np.percentile(bp, 2.5)), 3), boot_pf_hi=round(float(np.percentile(bp, 97.5)), 3), boot_p_pf_le1=round(float((bp <= 1).mean()), 4))
    return g


def dsr(R, n_trials: int, var_sr: float):
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014) sobre el Sharpe por operacion."""
    R = np.asarray(R, float); n = len(R); sr = R.mean() / R.std(ddof=1)
    sk = float(((R - R.mean()) ** 3).mean() / R.std() ** 3); ku = float(((R - R.mean()) ** 4).mean() / R.std() ** 4)
    gam = 0.5772156649
    sr0 = math.sqrt(var_sr) * ((1 - gam) * norm_ppf(1 - 1 / n_trials) + gam * norm_ppf(1 - 1 / (n_trials * math.e))) if n_trials > 1 else 0.0
    z = (sr - sr0) * math.sqrt(n - 1) / math.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2)
    return dict(sr_trade=sr, skew=sk, kurt=ku, sr0=sr0, dsr=norm_cdf(z))


def trial_sr_variance() -> float:
    """Varianza del Sharpe por operacion entre las pruebas H4/D1 de V8 (n>=30): SR_i = t_i / sqrt(n_i)."""
    e = pd.read_csv(RES / "V8_ROBUSTNESS_RESULTS.csv")
    e = e[(e.n_all >= 30)]
    sr = e.t_all.astype(float) / np.sqrt(e.n_all.astype(float))
    return float(np.nanvar(sr))


# ---------------- motor de simulacion (identico a v8_xau_h1_reference.trades) ----------------
class Sim:
    def __init__(self, d):
        self.d = d
        self.o, self.h, self.l, self.c, self.a, self.sp = (d[k].values for k in ("open", "high", "low", "close", "atr", "spr"))
        self.n = len(d)

    def one(self, i, s, rr=RR):
        o, h, l, c, a = self.o, self.h, self.l, self.c, self.a
        if i + 1 + MAXH >= self.n or not (a[i] > 0):
            return None
        e = o[i + 1]; at = a[i]; sl = e - s * at; tp = e + s * rr * at
        hh, ll = h[i + 1:i + MAXH + 1], l[i + 1:i + MAXH + 1]
        hs, ht = (ll <= sl, hh >= tp) if s > 0 else (hh >= sl, ll <= tp)
        fs = int(np.argmax(hs)) if hs.any() else 999; ft = int(np.argmax(ht)) if ht.any() else 999
        if fs <= ft and fs < 999:
            j, px = fs, sl
        elif ft < 999:
            j, px = ft, tp
        else:
            j, px = MAXH - 1, c[i + MAXH]
        gross = s * (px - e) / at; cost = self.sp[i + 1] / at
        why = "SL" if (fs <= ft and fs < 999) else "TP" if ft < 999 else "TIME"
        return gross - cost, i + 1 + j, at, why

    def many(self, idx, dirs, rr=RR):
        R, ex, at, ok = [], [], [], []
        for i, s in zip(idx, dirs):
            r = self.one(i, s, rr)
            if r is not None:
                R.append(r[0]); ex.append(r[1]); at.append(r[2]); ok.append(i)
        return np.array(R), np.array(ex), np.array(at), np.array(ok)


def trade_metrics(name, R, at, entry_idx, exit_idx, n_bars, d_days, extra=None):
    usd = R * at
    eq = np.cumsum(usd)
    exposure = float(np.minimum(exit_idx - entry_idx + 1, n_bars).sum() / n_bars)     # fraccion de barras en mercado (solapes contados una vez aprox.)
    q5 = np.sort(R)[: max(1, int(0.05 * len(R)))].mean()
    row = dict(benchmark=name, tipo="operaciones", n=len(R), net_usd_001=round(float(usd.sum()), 2), expR=round(float(R.mean()), 4), t=round(tstat(R), 2),
               pf=round(pf(usd), 3), win=round(float((R > 0).mean()), 3), max_dd_usd=round(max_dd(np.r_[0, eq]), 2), max_dd_pct_3000=round(max_dd(np.r_[0, eq]) / 3000 * 100, 2),
               net_over_maxdd=round(float(usd.sum() / max(1e-9, max_dd(np.r_[0, eq]))), 2), exposure_pct=round(min(exposure, 1) * 100, 1),
               spread_cost_R_mean=np.nan, worst_trade_R=round(float(R.min()), 2), cvar5_R=round(float(q5), 2), skew=round(float(pd.Series(R).skew()), 2),
               ann_return_pct=round(float(usd.sum() / 3000 * 100 / d_days * 365), 2), ann_sharpe_trade_equiv=np.nan)
    if extra:
        row.update(extra)
    return row


def mtm_metrics(name, w, d, d_days, note=""):
    """w[t] = posicion (oz, firmada) mantenida durante la barra t (decidida al cierre de t-1). PnL por barra = w[t]*(c[t]-c[t-1]) (apertura incluida via close previo)."""
    c = d.close.values; pnl = np.r_[0.0, w[1:] * np.diff(c)]
    day = d.time.dt.normalize().values
    daily = pd.Series(pnl).groupby(day).sum()
    eq = np.cumsum(pnl)
    sh = daily.mean() / daily.std(ddof=1) * math.sqrt(252) if daily.std() > 0 else np.nan
    return dict(benchmark=name, tipo="serie MTM por barra H4", n=int((np.abs(np.diff(np.r_[0, w])) > 1e-12).sum()), net_usd_001=round(float(pnl.sum()), 2), expR=np.nan, t=np.nan, pf=round(pf(pnl[pnl != 0]), 3),
                win=round(float((daily > 0).mean()), 3), max_dd_usd=round(max_dd(np.r_[0, eq]), 2), max_dd_pct_3000=round(max_dd(np.r_[0, eq]) / 3000 * 100, 2),
                net_over_maxdd=round(float(pnl.sum() / max(1e-9, max_dd(np.r_[0, eq]))), 2), exposure_pct=round(float((np.abs(w) > 0).mean() * 100), 1), spread_cost_R_mean=np.nan,
                worst_trade_R=np.nan, cvar5_R=round(float(np.sort(daily.values)[: max(1, int(0.05 * len(daily)))].mean()), 2), skew=round(float(daily.skew()), 2),
                ann_return_pct=round(float(pnl.sum() / 3000 * 100 / d_days * 365), 2), ann_vol_usd=round(float(daily.std() * math.sqrt(252)), 1), ann_sharpe_trade_equiv=round(float(sh), 2), nota=note)


def benchmarks(d, t):
    rng = np.random.default_rng(SEED)
    S = Sim(d); n = S.n
    d_days = (d.time.iloc[-1] - d.time.iloc[0]).total_seconds() / 86400
    idx, dr = C4.signals_n(d, 20)
    R0, ex0, at0, ok0 = S.many(idx, [dr[list(idx).index(i)] for i in idx])
    dr0 = np.array([dr[list(idx).index(i)] for i in ok0])
    # consistencia con la referencia de V8
    ref = pd.read_csv(RES.parent / "results" / "v8" / "xau_h1_reference_H4A1_rr3.0.csv")
    assert len(R0) == len(ref) and abs(R0.sum() - ref.R_net.sum()) < 1e-6, ("motor distinto a la referencia V8", len(R0), len(ref), R0.sum(), ref.R_net.sum())
    rows = []
    # estrategia: oficial (MT5) y referencia Python
    off = dict(benchmark="ESTRATEGIA H4 (oficial MT5, 248 op.)", tipo="operaciones", n=len(t), net_usd_001=round(t.pnl.sum(), 2), expR=round(t.R.mean(), 4), t=round(tstat(t.R), 2), pf=round(pf(t.pnl), 3),
               win=round((t.pnl > 0).mean(), 3), max_dd_usd=round(max_dd(np.r_[3000, 3000 + t.pnl.cumsum()] * -1 * -1) if False else float(((np.maximum.accumulate(3000 + t.pnl.cumsum()) - (3000 + t.pnl.cumsum()))).max()), 2),
               exposure_pct=np.nan, worst_trade_R=round(t.R.min(), 2), skew=round(float(t.R.skew()), 2), ann_return_pct=round(float(t.pnl.sum() / 3000 * 100 / d_days * 365), 2))
    off["max_dd_pct_3000"] = round(off["max_dd_usd"] / 3000 * 100, 2); off["net_over_maxdd"] = round(off["net_usd_001"] / off["max_dd_usd"], 2)
    off["cvar5_R"] = round(float(np.sort(t.R)[: max(1, int(0.05 * len(t)))].mean()), 2)
    rows.append(off)
    A = trade_metrics("ESTRATEGIA H4 (referencia Python, motor de los benchmarks)", R0, at0, ok0 + 1, ex0, n, d_days)
    A["spread_cost_R_mean"] = round(float(np.mean(S.sp[ok0 + 1] / at0)), 4); rows.append(A)
    lo = dr0 > 0
    for nm, m in (("B. solo LONG (misma regla)", lo), ("C. solo SHORT (misma regla)", ~lo)):
        rows.append(trade_metrics(nm, R0[m], at0[m], ok0[m] + 1, ex0[m], n, d_days))
    # ---- D: entradas aleatorias con misma frecuencia, hora de entrada y proporcion de direcciones
    hours = d.time.dt.hour.values; byh = {h: np.where(hours == h)[0] for h in np.unique(hours)}
    ent_h = hours[ok0 + 1]; p_long = lo.mean()
    stats = []
    for r in range(600):
        ii = np.array([rng.choice(byh[h][byh[h] > 60][:-45] ) - 1 for h in ent_h]); ss = np.where(rng.random(len(ii)) < p_long, 1, -1)
        Rr, ex_, at_, ok_ = S.many(ii, ss)
        stats.append((Rr.mean(), (Rr * at_).sum(), pf(Rr * at_), max_dd(np.r_[0, np.cumsum(Rr * at_)]), len(Rr)))
    st = np.array(stats)
    pD = float((st[:, 0] >= R0.mean()).mean())
    rows.append(dict(benchmark="D. entradas aleatorias (misma hora, frecuencia y % LONG), 600 reps", tipo="control aleatorio", n=int(st[:, 4].mean()), net_usd_001=round(float(st[:, 1].mean()), 2), expR=round(float(st[:, 0].mean()), 4),
                     pf=round(float(np.nanmean(st[:, 2])), 3), max_dd_usd=round(float(st[:, 3].mean()), 2), max_dd_pct_3000=round(float(st[:, 3].mean() / 3000 * 100), 2),
                     nota=f"expR p5-p95 = [{np.percentile(st[:,0],5):.3f}, {np.percentile(st[:,0],95):.3f}]; p(aleatorio >= estrategia) = {pD:.3f}"))
    # ---- D-L / D-S: control por lado (aisla la deriva del oro): entradas aleatorias en la misma hora, siempre LONG o siempre SHORT
    for side, nm, Rs in ((1, "D-L", R0[lo]), (-1, "D-S", R0[~lo])):
        hs_ = ent_h[lo] if side > 0 else ent_h[~lo]; st = []
        for r in range(600):
            ii = np.array([rng.choice(byh[h][byh[h] > 60][:-45]) - 1 for h in hs_]); Rr, _, at_, _ = S.many(ii, np.full(len(ii), side)); st.append((Rr.mean(), (Rr * at_).sum(), pf(Rr * at_)))
        st = np.array(st)
        rows.append(dict(benchmark=f"{nm}. entradas aleatorias solo {'LONG' if side > 0 else 'SHORT'} (misma hora y n), 600 reps", tipo="control aleatorio", n=len(hs_), net_usd_001=round(float(st[:, 1].mean()), 2),
                         expR=round(float(st[:, 0].mean()), 4), pf=round(float(np.nanmean(st[:, 2])), 3),
                         nota=f"expR p5-p95 = [{np.percentile(st[:,0],5):.3f}, {np.percentile(st[:,0],95):.3f}]; ruptura {'LONG' if side>0 else 'SHORT'} = {Rs.mean():.3f}; p(aleatorio >= ruptura) = {(st[:,0] >= Rs.mean()).mean():.3f}"))
    # ---- E1: mismas barras de ruptura, direccion barajada (prueba si la direccion de la ruptura contiene informacion)
    st = []
    for r in range(600):
        ss = np.where(rng.random(len(ok0)) < p_long, 1, -1); Rr, _, at_, _ = S.many(ok0, ss); st.append((Rr.mean(), (Rr * at_).sum(), pf(Rr * at_)))
    st = np.array(st); pE1 = float((st[:, 0] >= R0.mean()).mean())
    rows.append(dict(benchmark="E1. mismas barras de ruptura, direccion aleatoria, 600 reps", tipo="control aleatorio", n=len(ok0), net_usd_001=round(float(st[:, 1].mean()), 2), expR=round(float(st[:, 0].mean()), 4), pf=round(float(np.nanmean(st[:, 2])), 3),
                     nota=f"expR p5-p95 = [{np.percentile(st[:,0],5):.3f}, {np.percentile(st[:,0],95):.3f}]; p(>= estrategia) = {pE1:.3f}"))
    Rinv, _, ainv, _ = S.many(ok0, -dr0)
    rows.append(trade_metrics("E1b. mismas barras, direccion INVERTIDA (fade de la ruptura)", Rinv, ainv, ok0 + 1, ok0 + 1, n, d_days))
    # ---- E2: barras aleatorias con el mismo regimen (tercil ER30 x tercil ATR%) que cada operacion real, direccion aleatoria
    er = tercile(d.er30.fillna(d.er30.median()), (0, 1, 2)).astype(int).values; ap = tercile((d.atr / d.close).fillna((d.atr / d.close).median()), (0, 1, 2)).astype(int).values
    cell = er * 3 + ap; bycell = {c: np.where((cell == c) & (np.arange(n) > 60) & (np.arange(n) < n - 45))[0] for c in range(9)}
    st = []
    for r in range(600):
        ii = np.array([rng.choice(bycell[cell[i]]) for i in ok0]); ss = np.where(rng.random(len(ii)) < p_long, 1, -1)
        Rr, _, at_, _ = S.many(ii, ss); st.append((Rr.mean(), (Rr * at_).sum(), pf(Rr * at_)))
    st = np.array(st); pE2 = float((st[:, 0] >= R0.mean()).mean())
    rows.append(dict(benchmark="E2. barras aleatorias del mismo regimen (ER30 x ATR%), direccion aleatoria, 600 reps", tipo="control aleatorio", n=len(ok0), net_usd_001=round(float(st[:, 1].mean()), 2), expR=round(float(st[:, 0].mean()), 4),
                     pf=round(float(np.nanmean(st[:, 2])), 3), nota=f"expR p5-p95 = [{np.percentile(st[:,0],5):.3f}, {np.percentile(st[:,0],95):.3f}]; p(>= estrategia) = {pE2:.3f}"))
    # ---- F: momentum simple sin filtros (signo del retorno de 20 velas, una posicion cada vez, mismas salidas)
    c = d.close.values; i = 61; Rf, atf, enf, exf = [], [], [], []
    while i < n - MAXH - 2:
        s = int(np.sign(c[i] - c[i - 20]))
        if s == 0:
            i += 1; continue
        r = S.one(i, s)
        if r is None:
            break
        Rf.append(r[0]); atf.append(r[2]); enf.append(i + 1); exf.append(r[1]); i = r[1] + 1
    rows.append(trade_metrics("F. momentum simple sin filtros (signo ret. 20 velas, 1 posicion, SL1ATR/TP3R)", np.array(Rf), np.array(atf), np.array(enf), np.array(exf), n, d_days))
    # ---- A y G: comprar y mantener (1 oz = 0,01 lote) y variantes escaladas
    ones = np.ones(n)
    bh = mtm_metrics("A1. comprar y mantener 1 oz (0,01 lote) todo el periodo", ones, d, d_days); rows.append(bh)
    expo = A["exposure_pct"] / 100
    rows.append(mtm_metrics("A2. comprar y mantener, exposicion igualada a la estrategia (x fraccion de tiempo en mercado)", ones * expo, d, d_days, "escala lineal"))
    # PnL MTM de la estrategia (referencia Python) para igualar volatilidad
    w = np.zeros(n)
    for i_, s_, e_ in zip(ok0, dr0, ex0):
        w[i_ + 1:e_ + 1] += s_
    mt = mtm_metrics("ESTRATEGIA H4 (ref. Python) como serie MTM", w, d, d_days)
    mt["nota"] = "w = posicion firmada en oz (solapes suman); sin spread"; rows.append(mt)
    k = mt["ann_vol_usd"] / bh["ann_vol_usd"]
    rows.append(mtm_metrics("A3. comprar y mantener, volatilidad igualada a la estrategia", ones * k, d, d_days, f"posicion {k:.2f} oz"))
    a = d.atr.values; wv = np.nan_to_num(np.nanmean(a) / np.r_[np.nan, a[:-1]], nan=0.0)         # tamano inversamente proporcional al ATR previo
    mom = np.sign(c - np.r_[np.full(20, np.nan), c[:-20]]); mom = np.r_[np.nan, mom[:-1]]
    rows.append(mtm_metrics("G1. largo siempre, tamano 1/ATR (volatilidad escalada)", wv, d, d_days))
    rows.append(mtm_metrics("G2. momentum 20 velas (signo) con tamano 1/ATR (TSMOM escalado)", wv * np.nan_to_num(mom), d, d_days))
    rows.append(mtm_metrics("F2. momentum 20 velas (signo), 1 oz fija, siempre en mercado", np.nan_to_num(mom), d, d_days))
    B = pd.DataFrame(rows)
    B.insert(1, "periodo", f"{d.time.iloc[0].date()}..{d.time.iloc[-1].date()}")
    return B, dict(R0=R0, at0=at0, ok0=ok0, dr0=dr0, ex0=ex0, pD=pD, pE1=pE1, pE2=pE2, gold_move=float(d.close.iloc[-1] - d.open.iloc[0]), gold_pct=float(d.close.iloc[-1] / d.open.iloc[0] - 1))


def main():
    d, t = prep()
    t.to_csv(RES.parent / "results" / "v10" / "xau_h4_official_trades_enriched.csv", index=False) if (RES.parent / "results" / "v10").exists() else None
    g = global_stats(t, d)
    var_sr = trial_sr_variance()
    for nt in (1, 54, 890, 3719):
        x = dsr(t.R.values, nt, var_sr)
        g[f"DSR_N{nt}"] = round(x["dsr"], 4)
    g.update(sr_trade=round(x["sr_trade"], 4), sr0_N3719=round(x["sr0"], 4), var_sr_trials=round(var_sr, 5), skew_R=round(x["skew"], 2), kurt_R=round(x["kurt"], 2))
    rows = [dict(dimension="GLOBAL", bucket=k, n=np.nan, net_usd=np.nan, expR=v) for k, v in g.items()]
    t["year"] = t.open_time.dt.year; t["half"] = t.open_time.dt.year.astype(str) + "H" + ((t.open_time.dt.month > 6) + 1).astype(str)
    t["quarter"] = t.open_time.dt.to_period("Q").astype(str); t["month"] = t.open_time.dt.to_period("M").astype(str)
    t["dirn"] = np.where(t.dir > 0, "LONG", "SHORT")
    t["er_t"] = tercile(t.er30); t["atrp_t"] = tercile(t.atrp); t["sl_t"] = tercile(t.risk); t["spr_t"] = tercile(t.spr)
    t["trend_s"] = np.where(t.trend_al.isna(), "sin historial", np.where(t.trend_al > 0, "a favor SMA50", "contra SMA50"))
    t["trend_l"] = np.where(t.trend_long.isna(), "sin historial (<50 d)", np.where(t.trend_long > 0, "a favor 50d", "contra 50d"))
    t["dur"] = pd.cut(t.hold_days, [-1, 1, 3, 100], labels=["<=1d", "1-3d", ">3d"])
    t["sess"] = t.hour.map(lambda h: "00-04 Asia" if h < 4 else "04-08 Asia/Londres" if h < 8 else "08-12 Londres" if h < 12 else "12-16 Londres/NY" if h < 16 else "16-20 NY" if h < 20 else "20-24 cierre NY")
    for dim, key in (("anio", "year"), ("semestre", "half"), ("trimestre", "quarter"), ("mes", "month"), ("direccion", "dirn"), ("regimen_ER30", "er_t"), ("volatilidad_ATRpct", "atrp_t"),
                     ("distancia_SL", "sl_t"), ("spread_entrada", "spr_t"), ("tendencia_SMA50", "trend_s"), ("tendencia_50d", "trend_l"), ("duracion", "dur"), ("sesion_entrada", "sess"),
                     ("salida", "exit_why"), ("tras_noticia_24h", "post_news24"), ("dia_de_evento", "event_day"), ("split", "split")):
        rows += rows_for(t, dim, key)
    A = pd.DataFrame(rows); A.to_csv(RES / "V10_XAU_H4_AUDIT.csv", index=False)

    # ---- direccional
    D = []
    for dn, gg in list(t.groupby("dirn")) + [("TOTAL", t)]:
        for sp_, g2 in list(gg.groupby("split")) + [("TODO", gg)]:
            s = summ(g2.R)
            D.append(dict(direccion=dn, split=sp_, n=s["n"], net_usd=round(g2.pnl.sum(), 2), expR=s["expR"], t=s["t"], pf=s["pf"], win=s["win"], avg_win=round(g2[g2.pnl > 0].pnl.mean(), 2) if (g2.pnl > 0).any() else np.nan,
                          avg_loss=round(g2[g2.pnl < 0].pnl.mean(), 2) if (g2.pnl < 0).any() else np.nan, MFE_R=round(g2.MFE_R.mean(), 2), MAE_R=round(g2.MAE_R.mean(), 2), hold_days=round(g2.hold_days.mean(), 2)))
    L, Sh = t[t.dir > 0].R.values, t[t.dir < 0].R.values
    se = math.sqrt(L.var(ddof=1) / len(L) + Sh.var(ddof=1) / len(Sh)); tw = (L.mean() - Sh.mean()) / se
    D.append(dict(direccion="LONG-SHORT", split="TODO", n=len(L) - len(Sh), expR=round(L.mean() - Sh.mean(), 4), t=round(tw, 2), nota="Welch: diferencia de expectativa LONG - SHORT"))
    D.append(dict(direccion="ORO", split="2024-01..2026-10", nota=f"el precio paso de {d.open.iloc[0]:.1f} a {d.close.iloc[-1]:.1f} ({(d.close.iloc[-1]/d.open.iloc[0]-1)*100:.1f} %); fraccion LONG de la estrategia = {(t.dir>0).mean():.3f}"))
    pd.DataFrame(D).to_csv(RES / "V10_XAU_H4_DIRECTIONAL_ANALYSIS.csv", index=False)

    B, info = benchmarks(d, t)
    B.to_csv(RES / "V10_XAU_H4_BENCHMARKS.csv", index=False)
    json.dump({k: (v if not isinstance(v, np.ndarray) else None) for k, v in info.items()} | {"global": g}, open(RES.parent / "results" / "v10" / "h4_audit_summary.json", "w"), indent=1, default=str)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(pd.Series(g).to_string()); print(pd.DataFrame(D).to_string()); print(B.drop(columns=["tipo", "periodo"]).to_string())
    return t, B


if __name__ == "__main__":
    (RES.parent / "results" / "v10").mkdir(parents=True, exist_ok=True)
    main()

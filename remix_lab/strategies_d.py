"""Fase D — S05..S12 (EURUSDm) e inversion de senales. Todas las senales se calculan al CIERRE de la barra i y se ejecutan en la apertura de i+1
(motor `run_backtest`). Parametros canonicos fijados a priori (manual); ninguno optimizado. max_spread_frac=1.0 por defecto en las nuevas:
el filtro de coste ex-ante se aplica aparte (harness.cost_filter) para poder medirlo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind
from .strategies import Signals

PT = 1e-5


# ------------------------------------------------------------------ datos derivados
def to_day_key(t: pd.Series) -> pd.Series:
    """Dia de servidor; las barras del domingo se asignan al lunes (apertura FX)."""
    d = t.dt.normalize()
    return d.where(t.dt.dayofweek != 6, d + pd.Timedelta(days=1))


def resample(h1: pd.DataFrame, tf: str) -> pd.DataFrame:
    """H4 (bloques 00,04,..,20 h servidor) o D1 (dia de servidor, domingo->lunes) DERIVADOS de H1. spread = el de la primera barra H1 (apertura)."""
    key = h1.time.dt.floor("4h") if tf == "H4" else to_day_key(h1.time)
    g = h1.groupby(key)
    out = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(),
                        "tick_volume": g.tick_volume.sum(), "spread": g.spread.first(), "real_volume": 0, "n_h1": g.size()})
    out.index.name = "time"
    out = out.reset_index()
    need = 4 if tf == "H4" else 20
    return out[out.n_h1 >= need // 2].drop(columns="n_h1").reset_index(drop=True)


def htf_align(df: pd.DataFrame, htf: pd.DataFrame, cols: list[str], htf_minutes: int, base_minutes: int) -> pd.DataFrame:
    """Valores de `cols` de la ultima barra HTF YA CERRADA al cierre de cada barra base (sin lookahead)."""
    h = htf[["time"] + cols].copy()
    h["avail"] = h.time + pd.Timedelta(minutes=htf_minutes)
    left = pd.DataFrame({"t_close": df.time + pd.Timedelta(minutes=base_minutes)})
    m = pd.merge_asof(left.sort_values("t_close"), h.sort_values("avail"), left_on="t_close", right_on="avail", direction="backward")
    return m[cols].set_axis(df.index)


# ------------------------------------------------------------------ utilidades
def _sig(df, d, sl, tp, max_spread_frac=1.0, **kw) -> Signals:
    d = np.asarray(d, int); sl = np.asarray(sl, float); tp = np.asarray(tp, float)
    sp = df["spread"].to_numpy(float) * PT
    with np.errstate(invalid="ignore"):
        ok = np.isfinite(sl) & np.isfinite(tp) & (sl > 0) & (tp > 0) & (sp <= max_spread_frac * sl)
    return Signals(np.where(ok, d, 0), sl, tp, **kw)


def _a(df, n=14):
    return ind.atr(df, n).to_numpy()


# ------------------------------------------------------------------ S05 Z-score
S05_DEF = dict(sma_n=50, z_th=2.0, trend_filter=False, atr_n=14, sl_atr=2.0, max_bars=48, adx_max=25.0, adx_impl="mt5")   # adx_impl: "mt5" (formula del iADX de referencia) | "wilder" (Fase D, reproduce resultados antiguos)


def gen_s05(df, p):
    p = {**S05_DEF, **p}
    c = df.close
    z = ind.zscore(c, p["sma_n"]).to_numpy(); m = ind.sma(c, p["sma_n"]).to_numpy()
    d = np.where(z <= -p["z_th"], 1, np.where(z >= p["z_th"], -1, 0))
    if p["trend_filter"]:                       # filtro "de tendencia": solo operar reversion cuando NO hay tendencia fuerte (ADX < adx_max)
        a, _, _ = (ind.adx_mt5 if p["adx_impl"] == "mt5" else ind.adx)(df, 14); d = np.where(a.to_numpy() < p["adx_max"], d, 0)
    atr_ = _a(df, p["atr_n"])
    return _sig(df, d, atr_ * p["sl_atr"], np.abs(m - c.to_numpy()), max_bars=p["max_bars"])   # TP = retorno a la media (distancia al cierre de senal)


# ------------------------------------------------------------------ S06 RSI-2 + SMA100
S06_DEF = dict(rsi_lo=10, rsi_hi=90, sma_n=100, sl_atr=2.0, tp_atr=5.0, exit_rsi_long=70.0, exit_rsi_short=30.0, max_bars=20)


def gen_s06(df, p):
    p = {**S06_DEF, **p}
    c = df.close; r = ind.rsi(c, 2).to_numpy(); s = ind.sma(c, p["sma_n"]).to_numpy(); cc = c.to_numpy()
    d = np.where((cc > s) & (r < p["rsi_lo"]), 1, np.where((cc < s) & (r > p["rsi_hi"]), -1, 0))
    atr_ = _a(df)
    return _sig(df, d, atr_ * p["sl_atr"], atr_ * p["tp_atr"], max_bars=p["max_bars"], exit_long=(r > p["exit_rsi_long"]), exit_short=(r < p["exit_rsi_short"]))


# ------------------------------------------------------------------ S07 PDH/PDL
S07_DEF = dict(mode="breakout", sl_atr=1.5, rr=1.5, h0=7, h1=17, time_exit=20, retest_lb=12, retest_tol_atr=0.1)


def prev_day_levels(df):
    key = to_day_key(df.time)
    day = pd.DataFrame({"k": key, "h": df.high, "l": df.low}).groupby("k").agg(h=("h", "max"), l=("l", "min"))
    prev = day.shift(1)                                       # SOLO el dia anterior terminado (el dia actual nunca entra)
    return key.map(prev.h).to_numpy(), key.map(prev.l).to_numpy()


def gen_s07(df, p):
    p = {**S07_DEF, **p}
    pdh, pdl = prev_day_levels(df)
    c, o, h, l = (df[k].to_numpy() for k in ("close", "open", "high", "low"))
    hr = df.time.dt.hour.to_numpy(); win = (hr >= p["h0"]) & (hr < p["h1"])
    c1 = np.r_[np.nan, c[:-1]]
    atr_ = _a(df)
    if p["mode"] == "breakout":
        up = (c > pdh) & (c1 <= pdh); dn = (c < pdl) & (c1 >= pdl)
    elif p["mode"] == "sweep":                                 # barrida y rechazo: mecha supera el nivel, cierra de nuevo dentro -> contra la ruptura
        dn_ = (h > pdh) & (c < pdh) & (c < o); up_ = (l < pdl) & (c > pdl) & (c > o)
        up, dn = up_, dn_
    else:                                                      # retest: ruptura reciente (cierre fuera) y vuelta al nivel que se sostiene
        lb = p["retest_lb"]; tol = p["retest_tol_atr"] * atr_
        bo_up = pd.Series((np.r_[np.nan, c[:-1]] > pdh).astype(float)).rolling(lb).max().to_numpy() == 1
        bo_dn = pd.Series((np.r_[np.nan, c[:-1]] < pdl).astype(float)).rolling(lb).max().to_numpy() == 1
        up = bo_up & (l <= pdh + tol) & (c > pdh); dn = bo_dn & (h >= pdl - tol) & (c < pdl)
    d = np.where(win & up, 1, np.where(win & dn, -1, 0))
    sl = atr_ * p["sl_atr"]
    return _sig(df, d, sl, sl * p["rr"], time_exit_hour=p["time_exit"])


# ------------------------------------------------------------------ S08 Keltner reversion
S08_DEF = dict(ema_n=20, k=2.0, atr_n=14, sl_atr=1.5, confirm=False, regime=False, adx_max=25.0, max_bars=24, adx_impl="mt5")


def gen_s08(df, p):
    p = {**S08_DEF, **p}
    c = df.close; mid = ind.ema(c, p["ema_n"]); atr_s = ind.atr(df, p["atr_n"])
    up, lo = (mid + p["k"] * atr_s).to_numpy(), (mid - p["k"] * atr_s).to_numpy()
    cc = c.to_numpy(); cp = np.r_[np.nan, cc[:-1]]; upp = np.r_[np.nan, up[:-1]]; lop = np.r_[np.nan, lo[:-1]]
    if p["confirm"]:     # cierre de confirmacion: la barra anterior cerro FUERA del canal y esta cierra de nuevo DENTRO
        long_, short_ = (cp < lop) & (cc >= lo), (cp > upp) & (cc <= up)
    else:
        long_, short_ = cc < lo, cc > up
    d = np.where(long_, 1, np.where(short_, -1, 0))
    if p["regime"]:
        a, _, _ = (ind.adx_mt5 if p["adx_impl"] == "mt5" else ind.adx)(df, 14); d = np.where(a.to_numpy() < p["adx_max"], d, 0)
    return _sig(df, d, atr_s.to_numpy() * p["sl_atr"], np.abs(mid.to_numpy() - cc), max_bars=p["max_bars"])


# ------------------------------------------------------------------ S09 Momentum
S09_DEF = dict(mom_n=20, ema_n=100, exit_mode="atr", sl_atr=2.0, tp_atr=4.0, cat_sl_atr=3.0)


def gen_s09(df, p):
    p = {**S09_DEF, **p}
    c = df.close; e = ind.ema(c, p["ema_n"]).to_numpy(); cc = c.to_numpy()
    mom = (c / c.shift(p["mom_n"]) - 1).to_numpy()
    st_l = (mom > 0) & (cc > e); st_s = (mom < 0) & (cc < e)
    f_l = st_l & ~np.r_[False, st_l[:-1]]; f_s = st_s & ~np.r_[False, st_s[:-1]]      # solo el cambio de estado (primera barra)
    d = np.where(f_l, 1, np.where(f_s, -1, 0)); atr_ = _a(df)
    if p["exit_mode"] == "atr":
        return _sig(df, d, atr_ * p["sl_atr"], atr_ * p["tp_atr"])
    return _sig(df, d, atr_ * p["cat_sl_atr"], atr_ * 20.0, exit_long=(cc < e), exit_short=(cc > e))     # salida por perdida de tendencia (cierre cruza EMA)


# ------------------------------------------------------------------ S10 EMA pullback multitemporal
S10_DEF = dict(confirm="cross", sl_atr=1.5, tp_atr=3.0, htf=None)


def gen_s10(df, p, htf_df=None, base_minutes=60):
    p = {**S10_DEF, **p}
    c = df.close; e20, e50, e200 = (ind.ema(c, n).to_numpy() for n in (20, 50, 200)); cc = c.to_numpy()
    up_tr = (e20 > e50) & (e50 > e200); dn_tr = (e20 < e50) & (e50 < e200)
    if htf_df is not None:
        h4 = htf_df.copy(); h4["e50"] = ind.ema(h4.close, 50); h4["e200"] = ind.ema(h4.close, 200)
        al = htf_align(df, h4, ["e50", "e200"], 240, base_minutes)
        up_tr &= (al.e50 > al.e200).to_numpy(); dn_tr &= (al.e50 < al.e200).to_numpy()
    cp, e20p = np.r_[np.nan, cc[:-1]], np.r_[np.nan, e20[:-1]]
    hp, lp = np.r_[np.nan, df.high.to_numpy()[:-1]], np.r_[np.nan, df.low.to_numpy()[:-1]]
    if p["confirm"] == "cross":
        lg, sh = up_tr & (cp < e20p) & (cc > e20), dn_tr & (cp > e20p) & (cc < e20)
    else:                # estructura: la barra previa toco/perforo la EMA20 y esta cierra por encima de su maximo (o bajo su minimo)
        lg, sh = up_tr & (lp <= e20p) & (cc > hp), dn_tr & (hp >= e20p) & (cc < lp)
    d = np.where(lg, 1, np.where(sh, -1, 0)); atr_ = _a(df)
    return _sig(df, d, atr_ * p["sl_atr"], atr_ * p["tp_atr"])


# ------------------------------------------------------------------ S11 Bollinger reversion con filtro
S11_DEF = dict(bb_n=20, bb_k=2.0, rsi_lo=30.0, rsi_hi=70.0, filt=False, adx_max=25.0, sl_atr=2.0, max_bars=24)


def gen_s11(df, p):
    p = {**S11_DEF, **p}
    c = df.close; mid, up, lo = ind.bollinger(c, p["bb_n"], p["bb_k"]); r = ind.rsi(c, 14).to_numpy(); cc = c.to_numpy()
    d = np.where((cc < lo.to_numpy()) & (r < p["rsi_lo"]), 1, np.where((cc > up.to_numpy()) & (r > p["rsi_hi"]), -1, 0))
    if p["filt"]:
        a, _, _ = ind.adx(df, 14); d = np.where(a.to_numpy() < p["adx_max"], d, 0)
    return _sig(df, d, _a(df) * p["sl_atr"], np.abs(mid.to_numpy() - cc), max_bars=p["max_bars"])


# ------------------------------------------------------------------ S12 VWAP(proxy) + pin bar
S12_DEF = dict(vwap_start=0, wick_mult=2.0, body_max=0.33, rr=1.5, buf_atr=0.1, h0=7, h1=17, time_exit=20)


def gen_s12(df, p):
    p = {**S12_DEF, **p}
    vw = ind.session_vwap_proxy(df, p["vwap_start"]).to_numpy()      # PROXY (tick_volume), no es VWAP institucional
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    rng = np.maximum(h - l, 1e-9); body = np.abs(c - o)
    lw, uw = np.minimum(o, c) - l, h - np.maximum(o, c)
    bull = (lw >= p["wick_mult"] * np.maximum(body, 1e-9)) & (lw >= 0.5 * rng) & (body <= p["body_max"] * rng) & (l < vw) & (c > vw)
    bear = (uw >= p["wick_mult"] * np.maximum(body, 1e-9)) & (uw >= 0.5 * rng) & (body <= p["body_max"] * rng) & (h > vw) & (c < vw)
    hr = df.time.dt.hour.to_numpy(); win = (hr >= p["h0"]) & (hr < p["h1"]) & (hr >= p["vwap_start"])
    d = np.where(win & bull, 1, np.where(win & bear, -1, 0)); atr_ = _a(df)
    sl = np.where(d == 1, c - l, h - c) + p["buf_atr"] * atr_
    return _sig(df, d, sl, sl * p["rr"], time_exit_hour=p["time_exit"])


GEN = {"S05": gen_s05, "S06": gen_s06, "S07": gen_s07, "S08": gen_s08, "S09": gen_s09, "S10": gen_s10, "S11": gen_s11, "S12": gen_s12}


# ------------------------------------------------------------------ inversion de senales
def transform(sig: Signals, mode: str, geometry: str = "mirror") -> Signals:
    """mode: orig | inv | long | short | long_inv | short_inv.
    long_inv = tomar las senales LARGAS originales y operarlas CORTAS; short_inv = cortas originales operadas largas.
    geometry: mirror = mismas distancias SL/TP (mismo riesgo y geometria); swap = SL<-TP, TP<-SL (geometria de payoff invertida).
    Siempre se reconstruye la operacion completa en el motor (Bid/Ask, SL/TP, riesgo, costes); nunca se multiplica un resultado por -1."""
    d = sig.direction.copy()
    keep = {"orig": d != 0, "inv": d != 0, "long": d == 1, "short": d == -1, "long_inv": d == 1, "short_inv": d == -1}[mode]
    nd = np.where(keep, d, 0)
    sl, tp = sig.sl_dist, sig.tp_dist
    if mode in ("inv", "long_inv", "short_inv"):
        nd = -nd
        if geometry == "swap":
            sl, tp = tp, sl
    # sin exit flags ni max_bars en inversiones de S02-S04 (no los usan); para otras se anulan las reglas de salida por indicador
    return Signals(nd, sl, tp, sig.time_exit_hour, sig.max_bars, None if mode in ("inv", "long_inv", "short_inv") else sig.exit_long,
                   None if mode in ("inv", "long_inv", "short_inv") else sig.exit_short)


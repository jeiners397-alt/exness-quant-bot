"""REMIX EURUSD V3 — familias A (False Breakout Reversal) y B (Volatility Momentum). Senales al CIERRE de la barra i; ejecucion en la apertura de i+1.
Reglas completas y parametros PREDEFINIDOS en los docstrings; sin lookahead (niveles de sesion solo de sesiones terminadas; ATR de barras cerradas)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind
from .strategies import Signals
from .strategies_d import PT, _sig, prev_day_levels, to_day_key


def session_levels(df: pd.DataFrame, asia_end: int = 7):
    """Maximo/minimo de la sesion asiatica [0, asia_end) del MISMO dia de servidor, disponibles solo para barras con hora >= asia_end (sesion terminada).
    Devuelve (asia_hi, asia_lo) alineados con df."""
    key = to_day_key(df.time)
    hr = df.time.dt.hour
    a = df[hr < asia_end]
    hi = a.groupby(key[a.index]).high.max()
    lo = a.groupby(key[a.index]).low.min()
    ah = key.map(hi).to_numpy(float); al = key.map(lo).to_numpy(float)
    done = (hr >= asia_end).to_numpy()
    return np.where(done, ah, np.nan), np.where(done, al, np.nan)


# ---------------------------------------------------------------- A: False breakout reversal
A_DEF = dict(levels="PD", confirm="1", sl_mode="struct", rr=1.5, h0=7, h1=17, buf_atr=0.1, min_depth_atr=0.1, sl_atr=1.5, sl_min_atr=0.5, sl_max_atr=3.0, time_exit=20)


def gen_a(df: pd.DataFrame, p: dict) -> Signals:
    """A. Barrida de un nivel (PDH/PDL del dia anterior terminado, o maximo/minimo de la sesion asiatica) y recuperacion.
    SHORT: high[i] > nivel_alto y close[i] < nivel_alto, con profundidad (high-nivel) >= min_depth_atr*ATR[i-1].  LONG: espejo con el nivel bajo.
    confirm='1': la propia barra de barrida confirma con su cierre dentro. confirm='2': barrida en i-1 y la barra i cierra mas alla del extremo opuesto de la barrida
    (SHORT: close[i] < low[i-1]); entrada en la apertura de i+1.  Ventana de la barra de senal: h0 <= hora < h1 (servidor).
    SL 'struct': extremo de la barrida + buf_atr*ATR (distancia medida desde el cierre de senal; se descarta si < sl_min_atr o > sl_max_atr ATR);
    SL 'atr': sl_atr*ATR.  TP = rr*SL.  Cierre temporal a la hora time_exit."""
    p = {**A_DEF, **p}
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    atr_ = ind.atr(df, 14).to_numpy(); atr_p = np.r_[np.nan, atr_[:-1]]
    if p["levels"] == "PD":
        hi_l, lo_l = prev_day_levels(df)
    else:
        hi_l, lo_l = session_levels(df)
    hr = df.time.dt.hour.to_numpy(); win = (hr >= p["h0"]) & (hr < p["h1"])
    depth_s = (h - hi_l) >= p["min_depth_atr"] * atr_p
    depth_l = (lo_l - l) >= p["min_depth_atr"] * atr_p
    sweep_s = (h > hi_l) & (c < hi_l) & depth_s
    sweep_l = (l < lo_l) & (c > lo_l) & depth_l
    ext_hi, ext_lo = h.copy(), l.copy()
    if p["confirm"] == "2":
        s1, l1 = np.r_[False, sweep_s[:-1]], np.r_[False, sweep_l[:-1]]
        lo1, hi1 = np.r_[np.nan, l[:-1]], np.r_[np.nan, h[:-1]]
        ext_hi = np.maximum(h, hi1); ext_lo = np.minimum(l, lo1)
        short_ = s1 & (c < lo1); long_ = l1 & (c > hi1)
    else:
        short_, long_ = sweep_s, sweep_l
    d = np.where(win & short_, -1, np.where(win & long_, 1, 0))
    if p["sl_mode"] == "struct":
        sl = np.where(d == -1, ext_hi + p["buf_atr"] * atr_ - c, np.where(d == 1, c - (ext_lo - p["buf_atr"] * atr_), np.nan))
        ok = (sl >= p["sl_min_atr"] * atr_) & (sl <= p["sl_max_atr"] * atr_)
        d = np.where(ok, d, 0)
    else:
        sl = atr_ * p["sl_atr"]
    return _sig(df, d, sl, sl * p["rr"], time_exit_hour=p["time_exit"])


# ---------------------------------------------------------------- B: Volatility momentum
B_DEF = dict(mode="impulse", k=1.5, body_min=0.6, ker_on=True, ker_min=0.3, sl_mode="atr", rr=1.5, h0=7, h1=17, buf_atr=0.1, sl_atr=1.5, sl_min_atr=0.5, sl_max_atr=3.0,
             sq_pct=0.2, sq_body=0.5, time_exit=20)


def gen_b(df: pd.DataFrame, p: dict) -> Signals:
    """B. Continuacion tras impulso anormal de volatilidad.
    mode='impulse': rango[i] >= k*ATR[i-1] (ATR de barras previas) y cuerpo >= body_min*rango; direccion = signo(close-open); si ker_on exige KER(10)[i] >= ker_min.
    mode='squeeze': percentil de anchura Bollinger(20,2) en i-1 < sq_pct (consolidacion) y close[i] fuera de la banda con cuerpo >= sq_body*rango.
    Entrada en la apertura de i+1 en la direccion del impulso (NO se asume que una vela grande continue: se mide contra controles aleatorios).
    SL 'atr': sl_atr*ATR; 'struct': extremo opuesto de la barra de impulso +/- buf_atr*ATR (descarta si fuera de [sl_min_atr, sl_max_atr] ATR). TP = rr*SL. Cierre temporal a time_exit."""
    p = {**B_DEF, **p}
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    atr_ = ind.atr(df, 14).to_numpy(); atr_p = np.r_[np.nan, atr_[:-1]]
    rng = np.maximum(h - l, 1e-9); body = np.abs(c - o)
    hr = df.time.dt.hour.to_numpy(); win = (hr >= p["h0"]) & (hr < p["h1"])
    ker = ind.ker(df.close, 10).to_numpy()
    if p["mode"] == "impulse":
        big = (rng >= p["k"] * atr_p) & (body >= p["body_min"] * rng)
        up, dn = big & (c > o), big & (c < o)
    else:
        mid, bu, bl = ind.bollinger(df.close, 20, 2.0)
        bw = ((bu - bl) / mid)
        pct = bw.rolling(100).apply(lambda w: float((w <= w[-1]).mean()), raw=True).to_numpy()
        sq = np.r_[False, (pct < p["sq_pct"])[:-1]]
        strong = body >= p["sq_body"] * rng
        up, dn = sq & strong & (c > bu.to_numpy()), sq & strong & (c < bl.to_numpy())
    if p["ker_on"]:
        up, dn = up & (ker >= p["ker_min"]), dn & (ker >= p["ker_min"])
    d = np.where(win & up, 1, np.where(win & dn, -1, 0))
    if p["sl_mode"] == "struct":
        sl = np.where(d == 1, c - (l - p["buf_atr"] * atr_), np.where(d == -1, (h + p["buf_atr"] * atr_) - c, np.nan))
        ok = (sl >= p["sl_min_atr"] * atr_) & (sl <= p["sl_max_atr"] * atr_)
        d = np.where(ok, d, 0)
    else:
        sl = atr_ * p["sl_atr"]
    return _sig(df, d, sl, sl * p["rr"], time_exit_hour=p["time_exit"])

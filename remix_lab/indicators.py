"""B. INDICATOR ENGINE - indicadores causales (el valor en t solo usa datos hasta t).

Convenciones elegidas para coincidir con MT5:
- EMA: semilla = primer valor (iMA MODE_EMA), alpha = 2/(n+1).
- ATR: media simple del True Range (iATR de MT5 usa SMA).
- Bollinger: desviacion tipica poblacional (ddof=0), como iBands.
- ADX/+DI/-DI: suavizado de Wilder (RMA). iADX de MT5 puede diferir ligeramente;
  la paridad se debe verificar comparando listas de operaciones (ver docs/).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    out = s.ewm(alpha=2.0 / (n + 1), adjust=False).mean()
    out.iloc[: n - 1] = np.nan
    return out


def rma(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift(1)
    return pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    tr = true_range(df)
    tr.iloc[0] = df["high"].iloc[0] - df["low"].iloc[0]
    return tr.rolling(n, min_periods=n).mean()


def adx(df: pd.DataFrame, n: int = 14):
    """Devuelve (ADX, +DI, -DI) con suavizado de Wilder."""
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = true_range(df)
    str_ = rma(tr.fillna(0), n)
    pdi = 100 * rma(pd.Series(plus_dm, index=df.index).fillna(0), n) / str_
    mdi = 100 * rma(pd.Series(minus_dm, index=df.index).fillna(0), n) / str_
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    a = rma(dx.fillna(0), n)
    warm = 2 * n
    for s in (a, pdi, mdi):
        s.iloc[:warm] = np.nan
    return a, pdi, mdi


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    return mid, mid + k * sd, mid - k * sd


def donchian_prev(df: pd.DataFrame, n: int):
    """Maximo/minimo de las n barras ANTERIORES (excluye la barra actual)."""
    hh = df["high"].shift(1).rolling(n, min_periods=n).max()
    ll = df["low"].shift(1).rolling(n, min_periods=n).min()
    return hh, ll


# ======================= Fase D: indicadores adicionales (verificados en tests/test_indicators_d.py) =======================
def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """RSI de Wilder (RMA de ganancias/perdidas). Para n=2 es el RSI-2 de Connors."""
    d = close.diff()
    up, dn = d.clip(lower=0), (-d).clip(lower=0)
    ru, rd = up.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean(), dn.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    out = 100 - 100 / (1 + ru / rd)
    return out.where(rd != 0, 100.0).where(ru.notna())


def zscore(close: pd.Series, n: int = 50) -> pd.Series:
    """(close - SMA_n) / std_n (desviacion poblacional, ventana que incluye la barra actual)."""
    m = close.rolling(n).mean()
    s = close.rolling(n).std(ddof=0)
    return (close - m) / s.replace(0, np.nan)


def ker(close: pd.Series, n: int = 10) -> pd.Series:
    """Kaufman Efficiency Ratio = |c_t - c_{t-n}| / sum |c_i - c_{i-1}|  (0 = ruido, 1 = tendencia limpia)."""
    path = close.diff().abs().rolling(n).sum()
    return (close - close.shift(n)).abs() / path.replace(0, np.nan)


def choppiness(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Choppiness Index = 100*log10(sum(TR_n)/(maxH_n - minL_n))/log10(n). Alto (>61.8) = lateral; bajo (<38.2) = tendencia."""
    tr = true_range(df).rolling(n).sum()
    rng = df["high"].rolling(n).max() - df["low"].rolling(n).min()
    return 100 * np.log10(tr / rng.replace(0, np.nan)) / np.log10(n)


def linreg_slope(close: pd.Series, n: int = 20) -> pd.Series:
    """Pendiente de la regresion lineal OLS de las ultimas n cierres (unidades de precio por barra)."""
    x = np.arange(n, dtype=float); xc = x - x.mean(); den = (xc ** 2).sum()
    return close.rolling(n).apply(lambda y: float((xc * (y - y.mean())).sum() / den), raw=True)


def vol_percentile(df: pd.DataFrame, n_atr: int = 14, lookback: int = 500) -> pd.Series:
    """Percentil (0..1) del ATR normalizado (ATR/close) de la barra actual dentro de las `lookback` barras previas INCLUIDA la actual."""
    a = atr(df, n_atr) / df["close"]
    return a.rolling(lookback).apply(lambda w: float((w <= w[-1]).mean()), raw=True)


def bb_width(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.Series:
    mid, up, lo = bollinger(close, n, k)
    return (up - lo) / mid


def hurst_rs(close: pd.Series, window: int = 128) -> pd.Series:
    """Exponente de Hurst por R/S sobre retornos logaritmicos en ventana movil (pendiente log-log en escalas 8..window/2).
    Estimador ruidoso en ventanas cortas (sesgo conocido ~0.5-0.6 en ruido); usar solo como descriptor de regimen."""
    r = np.log(close).diff().to_numpy()
    out = np.full(len(r), np.nan)
    sizes = [s for s in (8, 16, 32, 64) if s <= window // 2]
    ls = np.log(sizes)
    for t in range(window, len(r)):
        w = r[t - window + 1:t + 1]
        if np.isnan(w).any():
            continue
        rs = []
        for s in sizes:
            segs = w[: (len(w) // s) * s].reshape(-1, s)
            z = np.cumsum(segs - segs.mean(axis=1, keepdims=True), axis=1)
            R = z.max(axis=1) - z.min(axis=1); S = segs.std(axis=1)
            ok = S > 0
            rs.append(np.log((R[ok] / S[ok]).mean()) if ok.any() else np.nan)
        rs = np.array(rs)
        if np.isnan(rs).any():
            continue
        out[t] = np.polyfit(ls, rs, 1)[0]
    return pd.Series(out, index=close.index)


def session_vwap_proxy(df: pd.DataFrame, start_hour: int = 0) -> pd.Series:
    """PROXY de VWAP de sesion con tick_volume como ponderacion (en Forex OTC no existe volumen consolidado: NO es el VWAP institucional).
    Acumula desde `start_hour` del dia del servidor; NaN antes de la hora de inicio."""
    t = df["time"]
    day = (t - pd.to_timedelta(start_hour, unit="h")).dt.normalize()
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    v = df["tick_volume"].astype(float)
    cum_pv = (tp * v).groupby(day).cumsum()
    cum_v = v.groupby(day).cumsum()
    out = cum_pv / cum_v
    return out.where(t.dt.hour >= start_hour)


def adx_mt5(df: pd.DataFrame, n: int = 14):
    """ADX/+DI/-DI con la formula de la implementacion de referencia de MetaQuotes (MQL5\\Indicators\\Examples\\ADX.mq5, verificada en el terminal):
    - DM y TR por barra: +DM/-DM exclusivos, TR = max(|H-L|,|H-Cprev|,|L-Cprev|); PD = 100*+DM/TR, ND = 100*-DM/TR (se suavizan los cocientes, NO DM y TR por separado);
    - suavizado = EMA con alpha = 2/(n+1) (MovingAverages.mqh::ExponentialMA), NO el 1/n de Wilder; semilla 0 en la barra 0;
    - ADX = EMA(n) de DX = 100*|PDI-NDI|/(PDI+NDI).
    El iADX nativo de MT5 se asume equivalente; se contrasta con el export por barra del EA V2.1 (tests/compare_bar_diag)."""
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    m = len(df)
    pr = 2.0 / (n + 1.0)
    pdi = np.zeros(m); ndi = np.zeros(m); adx_ = np.zeros(m)
    for i in range(1, m):
        pos, neg = h[i] - h[i - 1], l[i - 1] - l[i]
        pos, neg = max(pos, 0.0), max(neg, 0.0)
        if pos > neg:
            neg = 0.0
        elif pos < neg:
            pos = 0.0
        else:
            pos = neg = 0.0
        tr = max(abs(h[i] - l[i]), abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        pd_, nd_ = (100.0 * pos / tr, 100.0 * neg / tr) if tr != 0.0 else (0.0, 0.0)
        pdi[i] = pd_ * pr + pdi[i - 1] * (1 - pr)
        ndi[i] = nd_ * pr + ndi[i - 1] * (1 - pr)
        s = pdi[i] + ndi[i]
        dx = 100.0 * abs((pdi[i] - ndi[i]) / s) if s != 0.0 else 0.0
        adx_[i] = dx * pr + adx_[i - 1] * (1 - pr)
    return pd.Series(adx_, index=df.index), pd.Series(pdi, index=df.index), pd.Series(ndi, index=df.index)

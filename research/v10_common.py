"""V10 - utilidades comunes (XAUUSDm). Solo lectura de datos historicos; nada de ordenes.
Importa v8_htf_event_study ANTES que v8_xau_h1_reference (el orden de importacion fija el TF de v7_event_study; ver errores de V8/V9)."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

os.environ.setdefault("V7_TF", "M15")
import numpy as np
import pandas as pd

from research import v8_htf_event_study as H          # noqa: E402  (fija V.COOL = 6)
from research import v8_xau_h1_reference as R1        # noqa: E402

V = H.V
V.COOL = 6
ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "research"
DATA = ROOT / "data" / "raw"
SYM = "XAUUSDm"
POINT = json.load(open(DATA / "v9" / "download_info.json"))[SYM]["point"] if (DATA / "v9" / "download_info.json").exists() else 0.001
DEV = ("2024-01-01", "2025-01-01"); SEL = ("2025-01-01", "2026-01-01"); VAL = ("2026-01-01", "2026-11-01")
RESERVE_START = pd.Timestamp("2026-11-01")
OFFICIAL_H4_RR3 = ROOT / "results" / "v4_runs" / "RUN_20261110_XAUUSDm_H4_V8_XAU_BREAKOUT_V8H4A1_RR3.0_ohlc_1m_013" / "trades.csv"
OFFICIAL_H4_RR2 = ROOT / "results" / "v4_runs" / "RUN_20261110_XAUUSDm_H4_V8_XAU_BREAKOUT_V8H4A1_RR2.0_ohlc_1m_012" / "trades.csv"


def sha256(p) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def split_of(ts) -> str:
    ts = pd.Timestamp(ts)
    return "DEV" if ts < pd.Timestamp(SEL[0]) else "SEL" if ts < pd.Timestamp(VAL[0]) else "VAL" if ts < RESERVE_START else "RESERVA"


def bars(tf: str) -> pd.DataFrame:
    """H1/H4/D1 desde M15 (velas parciales conservadas, igual que MT5); NADA >= 2026-11-01."""
    d = H.load_htf(SYM, tf)
    return d[d.time < RESERVE_START].reset_index(drop=True)


def m15() -> pd.DataFrame:
    d = pd.read_csv(V.D / f"{SYM}_M15.csv", parse_dates=["time"]).drop_duplicates("time").sort_values("time")
    d = d[d.time < RESERVE_START].reset_index(drop=True)
    d["spr"] = d.spread * POINT
    return d


def m5() -> pd.DataFrame:
    d = pd.read_csv(DATA / "v9" / f"{SYM}_M5.csv", parse_dates=["time"]).drop_duplicates("time").sort_values("time")
    d = d[d.time < RESERVE_START].reset_index(drop=True)
    d["spr"] = d.spread * POINT
    return d


def tstat(x) -> float:
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 3 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))


def pf(x) -> float:
    x = np.asarray(x, float); g = x[x > 0].sum(); l = -x[x < 0].sum()
    return float(g / l) if l > 0 else float("inf")


def max_dd(eq) -> float:
    eq = np.asarray(eq, float); peak = np.maximum.accumulate(eq)
    return float((peak - eq).max())


def summ(R) -> dict:
    R = np.asarray(R, float); R = R[~np.isnan(R)]
    n = len(R)
    return dict(n=n, expR=round(float(R.mean()), 4) if n else np.nan, t=round(tstat(R), 2) if n > 2 else np.nan,
                pf=round(pf(R), 3) if n else np.nan, win=round(float((R > 0).mean()), 3) if n else np.nan, sumR=round(float(R.sum()), 2) if n else 0.0)


def norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p: float) -> float:
    # Acklam
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    pl = 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p)); return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > 1 - pl:
        q = math.sqrt(-2 * math.log(1 - p)); return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5; r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5]) * q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def block_boot(x, block=8, reps=4000, seed=7, stat=np.mean):
    x = np.asarray(x, float); n = len(x); rng = np.random.default_rng(seed)
    nb = int(math.ceil(n / block)); out = np.empty(reps)
    for r in range(reps):
        st = rng.integers(0, max(1, n - block + 1), nb)
        out[r] = stat(np.concatenate([x[s:s + block] for s in st])[:n])
    return out


def newey_west_t(y, x=None, lag=5) -> tuple[float, float]:
    """t de la media (x=None) o de la pendiente de y~x con errores HAC Newey-West."""
    y = np.asarray(y, float)
    if x is None:
        X = np.ones((len(y), 1))
    else:
        X = np.column_stack([np.ones(len(y)), np.asarray(x, float)])
    m = ~np.isnan(X).any(1) & ~np.isnan(y); X, y = X[m], y[m]
    n = len(y)
    if n < 30:
        return float("nan"), float("nan")
    b = np.linalg.lstsq(X, y, rcond=None)[0]; u = y - X @ b
    Xu = X * u[:, None]; S = Xu.T @ Xu / n
    for k in range(1, lag + 1):
        G = Xu[k:].T @ Xu[:-k] / n
        S += (1 - k / (lag + 1)) * (G + G.T)
    XtXi = np.linalg.inv(X.T @ X / n)
    cov = XtXi @ S @ XtXi / n
    j = X.shape[1] - 1
    return float(b[j]), float(b[j] / math.sqrt(cov[j, j]))


def official_h4(rr: int = 3) -> pd.DataFrame:
    p = OFFICIAL_H4_RR3 if rr == 3 else OFFICIAL_H4_RR2
    frozen = json.load(open(ROOT / "results" / "v9" / "XAU_FROZEN.json"))["official_runs"][f"H4_RR{rr}"]["trades_sha256"]
    assert sha256(p) == frozen, "trades.csv oficial modificado respecto a la linea congelada"
    t = pd.read_csv(p)
    for c in ("open_time", "close_time"):
        t[c] = pd.to_datetime(t[c], format="%Y.%m.%d %H:%M:%S")
    t["dir"] = np.where(t.type == "buy", 1, -1)
    t["pnl"] = t.profit + t.swap + t.commission
    return t

"""V9 Lotes B/C - microestructura y estudio de eventos de scalping (M1/M5), 10 familias A-J, primario e invertido.
Convenciones (identicas a V7/V8): senal en el cierre de la vela i, entrada en la apertura de i+1, coste = spread real de esa vela / ATR(i), SL de medicion = 1 ATR(14),
TP en {0.5,1,1.5,2,3}R, tiempo maximo 60 min, empate => SL. Enfriamiento 10 velas. Particion TEMPORAL fijada de antemano:
  DEV  2024-01-01..2024-12-31 (desarrollo/descubrimiento)    SEL 2025-01-01..2025-12-31 (seleccion)    VAL 2026-01-01..2026-10-31 (validacion, se evalua UNA vez al final)
Control: entradas aleatorias con la misma hora y tercil de ER (esperanza exacta de largos y cortos aleatorios en cada celda).
Uso: python -m research.v9_scalp_study <SYMBOL> <M1|M5>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from research import v7_event_study as V

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "raw" / "v9"
OUT = ROOT / "research"
INFO = json.load(open(D / "download_info.json"))
SPL = {"DEV": ("2024-01-01", "2025-01-01"), "SEL": ("2025-01-01", "2026-01-01"), "VAL": ("2026-01-01", "2026-11-01")}
V.COOL = 10
CFG = {"M1": dict(HZ=[1, 2, 3, 5, 10, 15, 30, 60], MAXH=60, mins=1), "M5": dict(HZ=[1, 2, 3, 6, 12], MAXH=12, mins=5)}
SESS = [(0, 6, "asia_0-6"), (7, 12, "londres_7-12"), (13, 20, "ny_13-20"), (21, 23, "cierre_21-23")]


def load(sym: str, tf: str) -> pd.DataFrame:
    d = pd.read_csv(D / f"{sym}_{tf}.csv", parse_dates=["time"]).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    d["spr"] = d.spread * INFO[sym]["point"]
    pc = d.close.shift(1)
    tr = np.maximum(d.high - d.low, np.maximum((d.high - pc).abs(), (d.low - pc).abs()))
    d["atr"] = tr.rolling(14).mean()
    d["er30"] = (d.close - d.close.shift(30)).abs() / d.close.diff().abs().rolling(30).sum()
    d["er8"] = (d.close - d.close.shift(8)).abs() / d.close.diff().abs().rolling(8).sum()
    d["hour"] = d.time.dt.hour
    d["rng"] = d.high - d.low
    d["sma20"] = d.close.rolling(20).mean(); d["sma50"] = d.close.rolling(50).mean(); d["sd20"] = d.close.rolling(20).std()
    d["tv_rel"] = d.tick_volume / d.tick_volume.rolling(60).mean()
    return d


def mtf_trend(d: pd.DataFrame) -> np.ndarray:
    """Tendencia M15 (SMA20>SMA50 de cierres M15) con la ULTIMA vela M15 COMPLETADA (sin look-ahead)."""
    m = d.set_index("time").close.resample("15min", label="left", closed="left").last().dropna()
    tr = np.sign(m.rolling(20).mean() - m.rolling(50).mean()).shift(1)       # shift(1): solo velas M15 ya cerradas
    return tr.reindex(d.time.values, method="ffill").values


def families(d: pd.DataFrame, tf: str) -> dict:
    o, h, l, c, a = (d[k].values for k in ("open", "high", "low", "close", "atr"))
    sh = lambda x, k=1: np.r_[np.full(k, np.nan), x[:-k]]
    pack = lambda up, dn: (np.where(up | dn)[0], np.where(up, 1, -1)[up | dn])
    ev = {}
    hh30 = d.high.rolling(30).max().shift(1).values; ll30 = d.low.rolling(30).min().shift(1).values
    hh60 = d.high.rolling(60).max().shift(1).values; ll60 = d.low.rolling(60).min().shift(1).values
    # A momentum: impulso de 3 velas > 2 ATR con vela de senal > 1.2 ATR
    mv = c - sh(c, 3); big = d.rng.values > 1.2 * a
    ev["A_MOMENTUM"] = pack((mv > 2 * a) & big, (mv < -2 * a) & big)
    # B breakout: primera vela que cierra fuera del rango de 30 velas
    up = (c > hh30) & np.r_[False, c[:-1] <= hh30[:-1]]; dn = (c < ll30) & np.r_[False, c[:-1] >= ll30[:-1]]
    ev["B_BREAKOUT"] = pack(up, dn)
    # C sweep: pico > 0.1 ATR sobre el extremo de 60 velas que cierra dentro. primario = reversion
    sw_u = (h > hh60 + 0.1 * a) & (c < hh60); sw_d = (l < ll60 - 0.1 * a) & (c > ll60)
    ev["C_SWEEP"] = pack(sw_d, sw_u)                                             # primario: largo tras barrida de minimos
    # D reversion a la media: |z|>2.5 con ER30<0.3 -> fade
    z = (c - d.sma20.values) / d.sd20.replace(0, np.nan).values; rg = d.er30.values < 0.3
    ev["D_MEAN_REVERSION"] = pack((z < -2.5) & rg, (z > 2.5) & rg)
    # E pullback en tendencia: SMA20>SMA50 y cruce de vuelta sobre SMA20 tras haber tocado
    s20, s50 = d.sma20.values, d.sma50.values
    mn3 = d.low.rolling(3).min().values; mx3 = d.high.rolling(3).max().values
    ev["E_PULLBACK"] = pack((s20 > s50) & (sh(c) <= sh(s20)) & (c > s20) & (mn3 <= s20), (s20 < s50) & (sh(c) >= sh(s20)) & (c < s20) & (mx3 >= s20))
    # F expansion de volatilidad tras compresion
    comp = d.rng.rolling(5).mean().shift(1).values < 0.7 * sh(a); ex = d.rng.values > 2.0 * sh(a)
    ev["F_VOL_EXPANSION"] = pack(comp & ex & (c > o), comp & ex & (c < o))
    # G sesion: ruptura del rango de apertura (primeros 15 min de Londres 08:00 y NY 13:30 UTC), primer cierre fuera, antes de +2h
    t = d.time
    up = np.zeros(len(d), bool); dn = np.zeros(len(d), bool)
    for hs, ms in ((8, 0), (13, 30)):
        day = t.dt.normalize()
        mins = t.dt.hour * 60 + t.dt.minute
        inr = (mins >= hs * 60 + ms) & (mins < hs * 60 + ms + 15)
        rh = d.high.where(inr).groupby(day).transform("max"); rl = d.low.where(inr).groupby(day).transform("min")
        win = (mins >= hs * 60 + ms + 15) & (mins < hs * 60 + ms + 135)
        u = win & (d.close > rh) & (d.close.shift(1) <= rh.shift(1).fillna(np.inf)); dd_ = win & (d.close < rl) & (d.close.shift(1) >= rl.shift(1).fillna(-np.inf))
        up |= u.values; dn |= dd_.values
    ev["G_SESSION_ORB"] = pack(up, dn)
    # H multi-timeframe: ruptura de 30 velas alineada con la tendencia M15 (ultima vela M15 completada)
    mt = mtf_trend(d)
    up = (c > hh30) & np.r_[False, c[:-1] <= hh30[:-1]]; dn = (c < ll30) & np.r_[False, c[:-1] >= ll30[:-1]]
    ev["H_MTF_BREAKOUT"] = pack(up & (mt > 0), dn & (mt < 0))
    # I ruptura + retest: tras primer cierre fuera, en las siguientes 10 velas el precio toca el nivel y cierra de nuevo fuera
    ru = np.zeros(len(d), bool); rd = np.zeros(len(d), bool)
    for i in np.where(up | dn)[0]:
        lvl = hh30[i] if up[i] else ll30[i]
        for j in range(i + 2, min(i + 11, len(d))):
            if up[i] and l[j] <= lvl and c[j] > lvl: ru[j] = True; break
            if dn[i] and h[j] >= lvl and c[j] < lvl: rd[j] = True; break
    ev["I_BREAKOUT_RETEST"] = pack(ru, rd)
    # J rango: ER30<0.15 y amplitud 30 velas < 3 ATR -> fade en el 15% inferior/superior
    width = hh30 - ll30; pos = (c - ll30) / np.where(width > 0, width, np.nan)
    rngm = (d.er30.values < 0.15) & (width < 3 * a)
    ev["J_RANGE"] = pack(rngm & (pos < 0.15), rngm & (pos > 0.85))
    return ev


def control_expect(d: pd.DataFrame, ev: pd.DataFrame, pool: pd.DataFrame) -> float:
    """Esperanza del control: media sobre eventos de 0.5*(R_long_celda + R_short_celda) con celda = (hora, tercil ER)."""
    q = pool.attrs["er_q"]
    cell = pool.groupby(["hour", "terc"]).agg(rl=("R_long", "mean"), rs=("R_short", "mean"))
    k = pd.MultiIndex.from_arrays([ev.hour.values, np.digitize(ev.er.values, q)])
    m = cell.reindex(k)
    return float((0.5 * (m.rl + m.rs)).mean())


def build_pool(d: pd.DataFrame, step: int) -> pd.DataFrame:
    idx = np.arange(60, len(d) - V.MAXH - 2, step)
    L = V.simulate(d, idx, np.ones(len(idx), int)); S = V.simulate(d, idx, -np.ones(len(idx), int))
    n = min(len(L), len(S)); L, S = L.iloc[:n], S.iloc[:n]
    p = pd.DataFrame(dict(hour=L.hour.values, er=L.er.values, R_long=L["R_1.5"].values, R_short=S["R_1.5"].values)).dropna()
    q = np.nanquantile(p.er.values, [1 / 3, 2 / 3]); p["terc"] = np.digitize(p.er.values, q); p.attrs["er_q"] = q
    return p


def split_mask(t: pd.Series, name: str):
    a, b = SPL[name]
    return (t >= a) & (t < b)


def run(sym: str, tf: str):
    cfg = CFG[tf]; V.HZ = cfg["HZ"]; V.MAXH = cfg["MAXH"]
    d = load(sym, tf); n = len(d)
    pool = build_pool(d, step=max(3, n // 40000))
    rows, feats = [], []
    for fam, (idx, dr) in families(d, tf).items():
        ok = idx > 100
        idx, dr = idx[ok], dr[ok]
        if len(idx) == 0:
            continue
        idx, dr, _ = V.dedupe(idx, dr, None)
        for var, sign in (("primary", 1), ("inverted", -1)):
            ev = V.simulate(d, idx, dr * sign)
            if len(ev) == 0:
                continue
            ev["tv_rel"] = d.tv_rel.values[ev.idx.values]; ev["spr_atr"] = (d.spr.values[ev.idx.values + 1] / d.atr.values[ev.idx.values]); ev["rng_atr"] = d.rng.values[ev.idx.values] / d.atr.values[ev.idx.values]
            ev["accel"] = (d.close.values[ev.idx.values] - d.close.values[ev.idx.values - 1]) * ev.dir / d.atr.values[ev.idx.values]
            ev["impulse3"] = (d.close.values[ev.idx.values] - d.close.values[ev.idx.values - 3]) * ev.dir / d.atr.values[ev.idx.values]
            ev["prevvol"] = d.atr.values[ev.idx.values] / d.atr.rolling(100).mean().values[ev.idx.values]
            ev["compress"] = d.rng.rolling(5).mean().shift(1).values[ev.idx.values] / d.atr.values[ev.idx.values]
            for sp in ("DEV", "SEL", "VAL", "ALL"):
                e = ev if sp == "ALL" else ev[split_mask(pd.to_datetime(ev.time), sp).values]
                if len(e) == 0:
                    continue
                r = V.summarize(e, dict(symbol=sym, tf=tf, family=fam, variant=var, split=sp), d, None)
                r["control_mean_R1.5"] = round(control_expect(d, e, pool), 4)
                sd = e["R_1.5"].std(ddof=1) if len(e) > 2 else np.nan
                r["t_vs_control"] = round((e["R_1.5"].mean() - r["control_mean_R1.5"]) / (sd / math.sqrt(len(e))), 2) if sd == sd and sd > 0 else np.nan
                r["events_per_day"] = round(len(e) / max(pd.to_datetime(e.time).dt.normalize().nunique(), 1), 2)
                rows.append(r)
            ev.insert(0, "family", fam); ev.insert(1, "variant", var); ev.insert(0, "symbol", sym); ev.insert(1, "tf", tf)
            feats.append(ev)
        print(sym, tf, fam, "ok", flush=True)
    E = pd.DataFrame(rows)
    E.to_csv(ROOT / "results" / "v9" / f"events_{sym}_{tf}.csv", index=False)
    F = pd.concat(feats)
    F.to_pickle(ROOT / "results" / "v9" / f"events_full_{sym}_{tf}.pkl")
    return E


if __name__ == "__main__":
    (ROOT / "results" / "v9").mkdir(parents=True, exist_ok=True)
    run(sys.argv[1], sys.argv[2])

"""V10 Lote D - XAUUSDm M15 con costes reales. Hipotesis cerradas (escritas antes de ver resultados), 5 familias x {primaria, invertida} x RR {1.5, 3} = 20 pruebas + 2 de noticias.
Senal al cierre de la vela i, entrada en la apertura de i+1, coste = spread de esa vela, SL 1 ATR(14) de M15, TP = RR x SL, tiempo maximo segun familia, empate => SL.
Se calcula la expectativa BRUTA y la NETA (V9: el coste elimino todas las ventajas de M1/M5). Control: misma serie de barras con direccion aleatoria (300 reps) para medir si la DIRECCION contiene informacion.
Reglas de clase (prefijadas): ver v10_momentum.classify; candidata exige n_DEV>=200, expR_DEV>0 con t>=2 y SEL>0 con t>=1,65 Y p(control) <= 0,05; B exige ademas t_DEV>=t* y coste x1,5 positivo."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from research.v10_common import RES, m15, split_of, summ, tstat
from research.v10_macro import calendar

T_STAR = math.sqrt(2 * math.log(3719 + 60))
SEED = 20261113
COOL = 16                                   # velas M15 entre senales de la misma familia (4 h)


def prep():
    d = m15()
    pc = d.close.shift(1)
    tr = np.maximum(d.high - d.low, np.maximum((d.high - pc).abs(), (d.low - pc).abs()))
    d["atr"] = tr.rolling(14).mean()
    d["er30"] = (d.close - d.close.shift(30)).abs() / d.close.diff().abs().rolling(30).sum()
    d["sma20"] = d.close.rolling(20).mean(); d["sma50"] = d.close.rolling(50).mean()
    d["hour"] = d.time.dt.hour; d["date"] = d.time.dt.normalize()
    # tendencia H1 (ultima vela H1 COMPLETADA): SMA20 y SMA50 de H1
    h1 = d.set_index("time").close.resample("1h").last().dropna().to_frame("c")
    h1["s20"] = h1.c.rolling(20).mean(); h1["s50"] = h1.c.rolling(50).mean(); h1["avail"] = h1.index + pd.Timedelta(hours=1)
    h1 = h1.reset_index(drop=True)[["avail", "c", "s20", "s50"]]
    k = pd.merge_asof(pd.DataFrame({"t": d.time + pd.Timedelta(minutes=15)}), h1, left_on="t", right_on="avail", direction="backward")
    d["h1_up"] = ((k.c > k.s50) & (k.s20 > k.s50)).values; d["h1_dn"] = ((k.c < k.s50) & (k.s20 < k.s50)).values
    # tendencia H4 (SMA50 de H4, ultima vela completada)
    h4 = d.set_index("time").close.resample("4h").last().dropna().to_frame("c"); h4["s50"] = h4.c.rolling(50).mean(); h4["avail"] = h4.index + pd.Timedelta(hours=4)
    h4 = h4.reset_index(drop=True)[["avail", "c", "s50"]]
    k4 = pd.merge_asof(pd.DataFrame({"t": d.time + pd.Timedelta(minutes=15)}), h4, left_on="t", right_on="avail", direction="backward")
    d["h4_up"] = (k4.c > k4.s50).values; d["h4_dn"] = (k4.c < k4.s50).values
    return d


def dedupe(idx, dr, cool=COOL):
    out_i, out_d, last = [], [], -10**9
    for i, s in zip(idx, dr):
        if i - last >= cool:
            out_i.append(i); out_d.append(s); last = i
    return np.array(out_i, int), np.array(out_d, int)


# ---------------- familias ----------------
def fam_breakout96(d, trend=None):
    c = d.close.values
    hh = d.high.rolling(96).max().shift(1).values; ll = d.low.rolling(96).min().shift(1).values
    up = (c > hh) & np.r_[False, c[:-1] <= hh[:-1]]; dn = (c < ll) & np.r_[False, c[:-1] >= ll[:-1]]
    if trend == "h4":
        up &= d.h4_up.values; dn &= d.h4_dn.values
    idx = np.where(up | dn)[0]; dr = np.where(up, 1, -1)[up | dn]
    keep = idx > 120
    return dedupe(idx[keep], dr[keep])


def fam_asia_orb(d):
    """Rango 00:00-08:00 UTC; primer cierre fuera del rango entre 08:00 y 12:00; una senal al dia."""
    idx, dr = [], []
    for day, g in d.groupby("date"):
        a = g[(g.hour < 8)]; w = g[(g.hour >= 8) & (g.hour < 12)]
        if len(a) < 20 or len(w) < 4:
            continue
        hi, lo = a.high.max(), a.low.min()
        for i, c in zip(w.index, w.close.values):
            if c > hi:
                idx.append(i); dr.append(1); break
            if c < lo:
                idx.append(i); dr.append(-1); break
    return np.array(idx, int), np.array(dr, int)


def fam_compression(d):
    rng10 = (d.high.rolling(10).max() - d.low.rolling(10).min()).shift(1) / d.atr
    rk = rng10.rolling(250, min_periods=100).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True).values
    c = d.close.values
    hh = d.high.rolling(48).max().shift(1).values; ll = d.low.rolling(48).min().shift(1).values
    up = (c > hh) & (rk <= 0.25); dn = (c < ll) & (rk <= 0.25)
    idx = np.where(up | dn)[0]; dr = np.where(up, 1, -1)[up | dn]
    keep = idx > 300
    return dedupe(idx[keep], dr[keep])


def fam_pullback(d):
    """Tendencia H1 alcista (cierre>SMA50 y SMA20>SMA50); en M15 el precio toca la SMA20 (minimo <= SMA20) y la vela cierra de nuevo por encima: continuacion."""
    c, l, h = d.close.values, d.low.values, d.high.values
    s20 = d.sma20.values
    up = d.h1_up.values & (l <= s20) & (c > s20)
    dn = d.h1_dn.values & (h >= s20) & (c < s20)
    idx = np.where(up | dn)[0]; dr = np.where(up, 1, -1)[up | dn]
    keep = idx > 300
    return dedupe(idx[keep], dr[keep])


FAMS = {
    "M15-1 ruptura de 96 velas (rango de 1 dia), continuacion": (lambda d: fam_breakout96(d), 96, "la ruptura del rango diario traslada a M15 el mecanismo de H4 (persistencia tras superar extremos recientes)"),
    "M15-2 ruptura de 96 velas alineada con tendencia H4": (lambda d: fam_breakout96(d, "h4"), 96, "el momentum de series temporales sugiere que las rupturas a favor de la tendencia de mayor horizonte persisten mas"),
    "M15-3 ruptura del rango asiatico en Londres (08-12 UTC)": (fam_asia_orb, 48, "la liquidez de Londres tras un rango asiatico estrecho produce desplazamientos direccionales (apertura de sesion)"),
    "M15-4 ruptura de 48 velas tras compresion de volatilidad": (fam_compression, 48, "agrupamiento de volatilidad: tras compresion, la expansion concentra movimientos largos"),
    "M15-5 pullback a la SMA20 en tendencia H1": (fam_pullback, 48, "las entradas en retroceso a favor de la tendencia mejoran el coste de entrada relativo (reaccion lenta)"),
}


def sim(d, idx, dr, rr, maxh):
    o, h, l, c, a, sp = (d[k].values for k in ("open", "high", "low", "close", "atr", "spr")); n = len(d)
    Rn, Rg, ok, ex = [], [], [], []
    for i, s in zip(idx, dr):
        if i + 1 + maxh >= n or not (a[i] > 0):
            continue
        e = o[i + 1]; at = a[i]; sl = e - s * at; tp = e + s * rr * at
        hh_, ll_ = h[i + 1:i + maxh + 1], l[i + 1:i + maxh + 1]
        hs, ht = (ll_ <= sl, hh_ >= tp) if s > 0 else (hh_ >= sl, ll_ <= tp)
        fs = int(np.argmax(hs)) if hs.any() else 999; ft = int(np.argmax(ht)) if ht.any() else 999
        if fs <= ft and fs < 999:
            px = sl
        elif ft < 999:
            px = tp
        else:
            px = c[i + maxh]
        g = s * (px - e) / at; Rg.append(g); Rn.append(g - sp[i + 1] / at); ok.append(i)
    return np.array(Rn), np.array(Rg), np.array(ok)


def classify(sm, p_ctrl, cost15_ok, tstar=T_STAR):
    dev, sel, val = sm["DEV"], sm["SEL"], sm["VAL"]
    if dev["n"] < 200 or sel["n"] < 100:
        return "F"
    cand = dev["expR"] > 0 and dev["t"] >= 2 and sel["expR"] > 0 and sel["t"] >= 1.65 and p_ctrl <= 0.05
    if not cand:
        return "D" if sm["ALL"]["expR"] <= 0 else "C"
    if dev["t"] >= tstar and cost15_ok and val["n"] >= 100 and val["expR"] > 0 and val["t"] >= 2:
        return "A"
    if dev["t"] >= tstar and cost15_ok:
        return "B"
    return "C"


def microstructure(d):
    rows = []
    d = d.dropna(subset=["atr"])
    for nm, m in (("TODO", np.ones(len(d), bool)), ("Asia 00-08", d.hour < 8), ("Londres 08-13", (d.hour >= 8) & (d.hour < 13)), ("NY 13-21", (d.hour >= 13) & (d.hour < 21)), ("cierre 21-24", d.hour >= 21)):
        g = d[m]
        rows.append(dict(tipo="microestructura", familia=nm, n=len(g), spread_mediano_usd=round(g.spr.median(), 3), atr_m15_mediano_usd=round(g.atr.median(), 2), coste_sobre_ATR=round(float((g.spr / g.atr).median()), 4),
                         nota="coste/ATR M1=0,166, M5=0,070, H4=0,009 (V9)"))
    return rows


def main():
    d = prep(); rng = np.random.default_rng(SEED)
    split = np.array([split_of(t) for t in d.time])
    rows = microstructure(d)
    n_id = 0
    for fam, (fn, maxh, why) in FAMS.items():
        idx, dr = fn(d)
        for var, sg in (("primaria", 1), ("invertida", -1)):
            for rr in (1.5, 3.0):
                Rn, Rg, ok = sim(d, idx, dr * sg, rr, maxh)
                sp_ = split[ok + 1]
                sm = {k: summ(Rn[sp_ == k] if k != "ALL" else Rn) for k in ("DEV", "SEL", "VAL", "ALL")}
                gm = {k: summ(Rg[sp_ == k] if k != "ALL" else Rg) for k in ("DEV", "SEL", "VAL", "ALL")}
                # coste x1,5 en DEV
                cost = Rg - Rn
                r15 = (Rg - 1.5 * cost)[sp_ == "DEV"]
                # control: direccion barajada en las mismas barras
                p_share = float(np.mean(dr * sg > 0)); ctrl = []
                for _ in range(300):
                    s2 = np.where(rng.random(len(idx)) < p_share, 1, -1)
                    R2, _, ok2 = sim(d, idx, s2, rr, maxh); ctrl.append(R2.mean())
                p_ctrl = float((np.array(ctrl) >= Rn.mean()).mean())
                cls = classify(sm, p_ctrl, r15.mean() > 0 if len(r15) else False)
                rows.append(dict(exp_id=f"V10D_{n_id:03d}", tipo="evento", familia=fam, variante=var, RR=rr, maxh_velas=maxh, hipotesis_fundamento=why, n_senales=len(idx),
                                 n_ALL=sm["ALL"]["n"], expR_bruta_ALL=gm["ALL"]["expR"], expR_neta_ALL=sm["ALL"]["expR"], t_neta_ALL=sm["ALL"]["t"], pf_neta_ALL=sm["ALL"]["pf"], win_ALL=sm["ALL"]["win"],
                                 coste_medio_R=round(float(cost.mean()), 4),
                                 n_DEV=sm["DEV"]["n"], expR_DEV=sm["DEV"]["expR"], t_DEV=sm["DEV"]["t"], n_SEL=sm["SEL"]["n"], expR_SEL=sm["SEL"]["expR"], t_SEL=sm["SEL"]["t"],
                                 n_VAL=sm["VAL"]["n"], expR_VAL=sm["VAL"]["expR"], t_VAL=sm["VAL"]["t"], expR_bruta_DEV=gm["DEV"]["expR"], expR_bruta_SEL=gm["SEL"]["expR"], expR_bruta_VAL=gm["VAL"]["expR"],
                                 expR_DEV_coste_x1_5=round(float(r15.mean()), 4) if len(r15) else np.nan, p_control_direccion=round(p_ctrl, 3), operaciones_por_dia=round(sm["ALL"]["n"] / ((d.time.iloc[-1] - d.time.iloc[0]).days * 5 / 7), 2),
                                 clase=cls))
                n_id += 1
    # noticias: fade/continuacion tras los primeros 15 min (M5): entrada en T+15 min, salida en T+60 min, sin SL (medicion en R = ATR M5 previa)
    from research.v10_common import m5
    M = m5(); pos = {t: i for i, t in enumerate(M.time)}
    cal = calendar()
    for var, sg in (("continuacion", 1), ("reversion", -1)):
        Rn = []; tt = []
        for _, e in cal.iterrows():
            i0 = pos.get(e.utc)
            if i0 is None or i0 < 14 or i0 + 14 >= len(M) or e.utc >= pd.Timestamp("2026-11-01"):
                continue
            if (M.time.values[i0 + 13] - M.time.values[i0]) != np.timedelta64(65, "m").astype("timedelta64[ns]"):
                continue
            atr = (M.high.values[i0 - 14:i0] - M.low.values[i0 - 14:i0]).mean()
            move = M.open.values[i0 + 3] - M.open.values[i0]
            s = sg * np.sign(move)
            if s == 0:
                continue
            r = s * (M.open.values[i0 + 12] - M.open.values[i0 + 3]) / atr - M.spr.values[i0 + 3] / atr
            Rn.append(r); tt.append(e.utc)
        Rn = np.array(Rn); sp_ = np.array([split_of(t) for t in tt])
        sm = {k: summ(Rn[sp_ == k] if k != "ALL" else Rn) for k in ("DEV", "SEL", "VAL", "ALL")}
        rows.append(dict(exp_id=f"V10D_{n_id:03d}", tipo="evento", familia="M15-N noticias NFP/CPI/FOMC: entrada T+15min, salida T+60min", variante=var, RR=np.nan, maxh_velas=9,
                         hipotesis_fundamento="tras el anuncio la reaccion inicial se extiende o se revierte (liquidez / reevaluacion de la informacion)", n_senales=len(Rn), n_ALL=sm["ALL"]["n"], expR_neta_ALL=sm["ALL"]["expR"], t_neta_ALL=sm["ALL"]["t"],
                         pf_neta_ALL=sm["ALL"]["pf"], win_ALL=sm["ALL"]["win"], n_DEV=sm["DEV"]["n"], expR_DEV=sm["DEV"]["expR"], n_SEL=sm["SEL"]["n"], expR_SEL=sm["SEL"]["expR"], n_VAL=sm["VAL"]["n"], expR_VAL=sm["VAL"]["expR"],
                         clase="F" if sm["ALL"]["n"] < 100 else "D" if sm["ALL"]["expR"] <= 0 else "C", nota="expectativa en ATR(M5); n < 100: datos insuficientes por construccion (86 eventos)"))
        n_id += 1
    E = pd.DataFrame(rows); E.to_csv(RES / "V10_XAU_M15_EVENTS.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(E[E.tipo == "microestructura"].dropna(axis=1, how="all").to_string())
    X = E[E.tipo == "evento"]
    print(X[["familia", "variante", "RR", "n_senales", "n_ALL", "expR_bruta_ALL", "expR_neta_ALL", "t_neta_ALL", "pf_neta_ALL", "expR_DEV", "expR_SEL", "expR_VAL", "p_control_direccion", "operaciones_por_dia", "clase"]].to_string())
    print(X.clase.value_counts().to_dict())


if __name__ == "__main__":
    main()

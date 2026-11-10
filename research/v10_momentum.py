"""V10 Lote B - momentum / reversion / volatilidad / regimen economico en XAUUSDm (H1, H4, D1; M15 solo como observacion).
Cada prueba tiene hipotesis y fundamento escritos ANTES de mirar resultados (lista HYP). Presupuesto cerrado: 25 TSMOM + 4 reversion + 6 condicionadas + 3 ruptura + 12 macro = ~50 pruebas.
Regla de clase (prefijada): A requiere DEV, SEL y VAL con el mismo signo, |t_HAC|>=t* (t*=sqrt(2 ln N_total), N_total acumulado) en el global Y en VAL, con n>=100 en VAL;
B: signo coherente en los 3 tramos y |t_HAC|>=2 global (sin alcanzar t*); C: significativo global (|t|>=2) pero no coherente; D: sin evidencia (|t|<2); F: n insuficiente.
Estadistico: pendiente de y (retorno futuro a h barras escalado por volatilidad previa) sobre x = signo del retorno de L barras (TSMOM, Moskowitz-Ooi-Pedersen 2012), con errores Newey-West de rezago h."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from research.v10_common import DATA, RES, bars, m15, split_of, norm_cdf, tstat, summ
from research import v8_lote_c_h4 as C4
from research.v10_h4_audit import Sim, MAXH

T_STAR_N = 3719 + 60          # acumulado V7+V8+V9 + presupuesto V10 (se actualiza en el registro final)
T_STAR = math.sqrt(2 * math.log(T_STAR_N))
SEED = 20261112


def ols_hac(y, X, lag):
    """OLS con constante; devuelve (coef, t_HAC) para cada regresor (sin la constante)."""
    X = np.column_stack([np.ones(len(y)), X]); m = ~np.isnan(X).any(1) & ~np.isnan(y); X, y = X[m], y[m]
    n = len(y)
    if n < 40:
        return None
    b = np.linalg.lstsq(X, y, rcond=None)[0]; u = y - X @ b; Xu = X * u[:, None]; S = Xu.T @ Xu / n
    for k in range(1, lag + 1):
        G = Xu[k:].T @ Xu[:-k] / n; S += (1 - k / (lag + 1)) * (G + G.T)
    Xi = np.linalg.inv(X.T @ X / n); cov = Xi @ S @ Xi / n
    return b[1:], b[1:] / np.sqrt(np.diag(cov)[1:]), n


def vol_scaled_forward(d: pd.DataFrame, h: int, vw: int = 60):
    c = d.close.values; lr = np.r_[np.nan, np.diff(np.log(c))]
    sig = pd.Series(lr).rolling(vw).std().values
    fwd = np.full(len(c), np.nan); fwd[:-h] = np.log(c[h:] / c[:-h])
    return fwd / (sig * math.sqrt(h)), sig


def classify(sl_all, t_all, n_all, sl_sp, n_val, tstar=T_STAR):
    """sl_sp: dict split -> (pendiente, t)."""
    if n_all < 100 or any(v is None for v in sl_sp.values()):
        return "F"
    signs = {np.sign(v[0]) for v in sl_sp.values()}
    coh = len(signs) == 1 and 0 not in signs
    if coh and abs(t_all) >= tstar and abs(sl_sp["VAL"][1]) >= tstar and n_val >= 100:
        return "A"
    if coh and abs(t_all) >= 2:
        return "B"
    if abs(t_all) >= 2:
        return "C"
    return "D"


def tsmom_tests(tf: str, d: pd.DataFrame, Ls, hs, rationale, tag):
    rows = []
    c = d.close.values; split = np.array([split_of(x) for x in d.time])
    for L in Ls:
        x = np.sign(c / np.r_[np.full(L, np.nan), c[:-L]] - 1)
        for h in hs:
            y, sig = vol_scaled_forward(d, h)
            r = ols_hac(y, x, max(h, 1))
            if r is None:
                continue
            row = dict(hipotesis=f"TSMOM {tf} L={L} h={h}", familia="TSMOM", mercado="XAUUSDm", tf=tf, L=L, h=h, fundamento=rationale, n=r[2], pendiente=round(float(r[0][0]), 4), t_hac=round(float(r[1][0]), 2))
            sp = {}
            for s_ in ("DEV", "SEL", "VAL"):
                m = split == s_
                rr = ols_hac(np.where(m, y, np.nan), np.where(m, x, np.nan), max(h, 1))
                sp[s_] = (float(rr[0][0]), float(rr[1][0])) if rr else None
                row[f"pend_{s_}"] = round(sp[s_][0], 4) if rr else np.nan; row[f"t_{s_}"] = round(sp[s_][1], 2) if rr else np.nan
                row[f"n_{s_}"] = rr[2] if rr else 0
            # no solapadas: retorno medio con signo, bloques de h barras
            idx = np.arange(max(L, 60), len(c) - h, h); ns = x[idx] * y[idx]; ns = ns[~np.isnan(ns)]
            row.update(n_no_solapadas=len(ns), media_signo_x_ret_ns=round(float(ns.mean()), 4) if len(ns) else np.nan, t_no_solapadas=round(tstat(ns), 2) if len(ns) > 2 else np.nan)
            row["coste_en_unidades_vol"] = round(float(np.nanmean(d.spr.values / (c * sig * math.sqrt(h)))), 4)
            row["clase"] = classify(row["pendiente"], row["t_hac"], r[2], sp, row["n_VAL"])
            rows.append(row)
    return rows


def reversal_tests(tf, d, L, h, z=2.0):
    c = d.close.values; lr = np.r_[np.nan, np.diff(np.log(c))]
    sig = pd.Series(lr).rolling(60).std().values
    ret = np.log(c / np.r_[np.full(L, np.nan), c[:-L]]); zs = ret / (sig * math.sqrt(L))
    y, _ = vol_scaled_forward(d, h)
    ev = np.where(np.abs(zs) > z)[0]; ev = ev[(ev > 80) & (ev < len(c) - h - 1)]
    # un evento por ventana h (evita solape)
    keep = []; last = -10**9
    for i in ev:
        if i - last >= h:
            keep.append(i); last = i
    keep = np.array(keep); sgn = -np.sign(zs[keep])               # apostar contra el extremo
    v = sgn * y[keep]; v = v[~np.isnan(v)]
    split = np.array([split_of(d.time.iloc[i]) for i in keep])
    row = dict(hipotesis=f"REVERSION tras |z{L}|>{z} {tf} h={h}", familia="REVERSION", mercado="XAUUSDm", tf=tf, L=L, h=h, fundamento="sobrerreaccion de corto plazo / liquidez (reversion tras extremos)",
               n=len(v), pendiente=round(float(v.mean()), 4) if len(v) else np.nan, t_hac=round(tstat(v), 2) if len(v) > 2 else np.nan)
    sp = {}
    for s_ in ("DEV", "SEL", "VAL"):
        vv = (sgn * y[keep])[split == s_]; vv = vv[~np.isnan(vv)]
        sp[s_] = (float(vv.mean()), tstat(vv)) if len(vv) > 2 else None
        row[f"pend_{s_}"] = round(sp[s_][0], 4) if sp[s_] else np.nan; row[f"t_{s_}"] = round(sp[s_][1], 2) if sp[s_] else np.nan; row[f"n_{s_}"] = len(vv)
    row["clase"] = classify(row["pendiente"], row["t_hac"] if row["t_hac"] == row["t_hac"] else 0, len(v), sp, row["n_VAL"]) if len(v) >= 100 else "F"
    row["nota"] = "pendiente = media de (signo contrario al extremo) x retorno futuro escalado; eventos no solapados"
    return row


def rolling_rank(x, w=250):
    s = pd.Series(x)
    return s.rolling(w, min_periods=100).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True).values


def conditioned_tests(d):
    """TSMOM H4 L=30 h=6 condicionada por tercil de volatilidad (rango percentil pasado, sin look-ahead) y por ER30."""
    rows = []
    c = d.close.values; x = np.sign(c / np.r_[np.full(30, np.nan), c[:-30]] - 1)
    y, sig = vol_scaled_forward(d, 6)
    vr = rolling_rank(sig); er = d.er30.values
    split = np.array([split_of(t) for t in d.time])
    for nm, key, edges in (("volatilidad (rango percentil previo 250 velas)", vr, (1 / 3, 2 / 3)), ("eficiencia ER30 (terciles muestrales de rango movil)", rolling_rank(er), (1 / 3, 2 / 3))):
        for lab, lo, hi in (("bajo", -1, edges[0]), ("medio", edges[0], edges[1]), ("alto", edges[1], 2)):
            m = (key > lo) & (key <= hi) if lab != "bajo" else (key <= hi)
            r = ols_hac(np.where(m, y, np.nan), np.where(m, x, np.nan), 6)
            if r is None:
                continue
            row = dict(hipotesis=f"TSMOM H4 L=30 h=6 | {nm} = {lab}", familia="TSMOM_CONDICIONADO", mercado="XAUUSDm", tf="H4", L=30, h=6,
                       fundamento="el momentum deberia ser mas fuerte con tendencia eficiente y volatilidad moderada/alta (persistencia de flujos)", n=r[2], pendiente=round(float(r[0][0]), 4), t_hac=round(float(r[1][0]), 2))
            sp = {}
            for s_ in ("DEV", "SEL", "VAL"):
                rr = ols_hac(np.where(m & (split == s_), y, np.nan), np.where(m & (split == s_), x, np.nan), 6)
                sp[s_] = (float(rr[0][0]), float(rr[1][0])) if rr else None
                row[f"pend_{s_}"] = round(sp[s_][0], 4) if rr else np.nan; row[f"t_{s_}"] = round(sp[s_][1], 2) if rr else np.nan; row[f"n_{s_}"] = rr[2] if rr else 0
            row["clase"] = classify(row["pendiente"], row["t_hac"], r[2], sp, row["n_VAL"])
            rows.append(row)
    return rows


def breakout_tests(d):
    """Continuacion tras rupturas y tras consolidaciones, con el motor de V8 (SL 1 ATR, TP 3R, 40 velas)."""
    S = Sim(d); idx, dr = C4.signals_n(d, 20)
    res = S.many(idx, [dr[list(idx).index(i)] for i in idx]); R, ex, at, ok = res
    drs = np.array([dr[list(idx).index(i)] for i in ok])
    rng10 = (d.high.rolling(10).max() - d.low.rolling(10).min()).shift(1) / d.atr                  # compresion de las 10 velas previas a la senal
    thr = rolling_rank(rng10.values)
    comp = thr[ok] <= 0.25                                                                          # compresion = rango 10 velas en el cuartil inferior de las 250 previas
    rows = []
    def row_of(name, mask, fundamento):
        R_ = R[mask]; s = summ(R_); spl = np.array([split_of(d.time.iloc[i + 1]) for i in ok[mask]])
        r = dict(hipotesis=name, familia="RUPTURA", mercado="XAUUSDm", tf="H4", L=20, h=40, fundamento=fundamento, n=s["n"], pendiente=s["expR"], t_hac=s["t"])
        sp = {}
        for s_ in ("DEV", "SEL", "VAL"):
            ss = summ(R_[spl == s_]); sp[s_] = (ss["expR"], ss["t"]) if ss["n"] > 2 else None
            r[f"pend_{s_}"] = ss["expR"]; r[f"t_{s_}"] = ss["t"]; r[f"n_{s_}"] = ss["n"]
        r["clase"] = "F" if s["n"] < 100 else classify(s["expR"], s["t"], s["n"], sp, r["n_VAL"]) if all(v is not None for v in sp.values()) else "F"
        r["nota"] = "pendiente = expectativa neta en R (SL 1 ATR, TP 3R)"
        return r
    rows.append(row_of("RUPTURA 20 velas con consolidacion previa (rango 10v <= cuartil inferior)", comp, "tras compresion de volatilidad, la expansion deberia concentrar la continuacion (agrupamiento de volatilidad)"))
    rows.append(row_of("RUPTURA 20 velas SIN consolidacion previa", ~comp, "complemento: ruptura en regimen no comprimido"))
    # diferencia entre ambas (Welch)
    a, b = R[comp], R[~comp]
    tw = (a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)) if len(a) > 2 and len(b) > 2 else np.nan
    rows.append(dict(hipotesis="DIFERENCIA ruptura con vs sin consolidacion (Welch)", familia="RUPTURA", mercado="XAUUSDm", tf="H4", n=len(a) + len(b), pendiente=round(float(a.mean() - b.mean()), 4), t_hac=round(float(tw), 2),
                     clase="D" if abs(tw) < 2 else "C", fundamento="contraste directo", nota=f"n con={len(a)}, sin={len(b)}"))
    return rows, dict(S=S, ok=ok, drs=drs, R=R, comp=comp)


def vol_regime_table(d, B):
    """Fase 8: como cambian P(TP), P(SL), duracion y expectativa de la ruptura H4 20 segun el estado de volatilidad (pool de senales de la baseline, motor Python)."""
    S, ok, drs = B["S"], B["ok"], B["drs"]
    rows = []
    out = [S.one(i, s) for i, s in zip(ok, drs)]
    R = np.array([o[0] for o in out]); dur = np.array([o[1] - (i + 1) + 1 for o, i in zip(out, ok)]); why = np.array([o[3] for o in out])
    atrp = (d.atr / d.close).values; c = d.close.values
    lr = np.r_[np.nan, np.diff(np.log(c))]
    rv20 = pd.Series(lr).rolling(20).std().values; rvl = pd.Series(lr).rolling(120).std().values
    feats = {
        "ATR% (nivel, terciles muestrales)": atrp[ok],
        "volatilidad relativa rv20/rv120": (rv20 / rvl)[ok],
        "expansion ATR14 / ATR14 de 30 velas atras": (d.atr / d.atr.shift(30)).values[ok],
        "rango de la vela de ruptura / ATR": (d.rng / d.atr).values[ok],
        "compresion previa (rango 10 velas / ATR)": ((d.high.rolling(10).max() - d.low.rolling(10).min()).shift(1) / d.atr).values[ok],
    }
    for nm, f in feats.items():
        f = pd.Series(f); q = pd.qcut(f, 3, labels=["bajo", "medio", "alto"], duplicates="drop")
        for lab in q.cat.categories:
            m = (q == lab).values & ~np.isnan(R); s = summ(R[m])
            rows.append(dict(analisis="ruptura H4 20 por estado de volatilidad", variable=nm, tercil=lab, n=s["n"], expR=s["expR"], t=s["t"], pf=s["pf"], p_TP=round(float((why[m] == "TP").mean()), 3),
                             p_SL=round(float((why[m] == "SL").mean()), 3), p_TIME=round(float((why[m] == "TIME").mean()), 3), duracion_media_velas=round(float(dur[m].mean()), 1)))
    # agrupamiento de volatilidad y transiciones (todas las velas H4)
    a = np.abs(lr[~np.isnan(lr)])
    ac = [float(pd.Series(a).autocorr(k)) for k in (1, 2, 3, 6, 12, 30)]
    rows.append(dict(analisis="agrupamiento de volatilidad (autocorrelacion de |r| H4)", variable="lags 1,2,3,6,12,30", tercil="", n=len(a), expR=np.nan, nota=" ".join(f"{x:.3f}" for x in ac)))
    st = pd.qcut(pd.Series(rv20).dropna(), 3, labels=[0, 1, 2]).astype(int).values
    T = np.zeros((3, 3))
    for u, v in zip(st[:-6], st[6:]):
        T[u, v] += 1
    T = T / T.sum(1, keepdims=True)
    rows.append(dict(analisis="transicion de regimen de volatilidad (rv20) a 6 velas", variable="P(bajo->bajo, medio->medio, alto->alto)", tercil="", n=len(st), nota=f"{T[0,0]:.2f} {T[1,1]:.2f} {T[2,2]:.2f}"))
    # volatilidad posterior a noticias (de la tabla macro): razon vol post/pre ya medida en V10_MACRO_SUMMARY.csv
    ms = pd.read_csv(RES / "V10_MACRO_SUMMARY.csv")
    for _, r in ms.iterrows():
        rows.append(dict(analisis="volatilidad posterior a noticias (M5)", variable=r.event, tercil="", n=r.n, expR=np.nan, nota=f"razon vol 60min post/pre mediana {r.razon_vol_post_pre_mediana}; rango30 x{r.razon_rango_media_geom} vs control"))
    return pd.DataFrame(rows), R


def economic_regimes(d_h4, d_d1, trades):
    """Series FRED de mercado, con retardo de 2 dias de calendario (publicadas D+1 tarde). 6 variables; (a) relacion con el retorno 5d futuro del oro, (b) expectativa de la ruptura por tercil."""
    ser = {}
    for sid in ("DFII10", "DGS10", "T10YIE", "DTWEXBGS", "VIXCLS"):
        s = pd.read_csv(DATA / "v10" / f"fred_{sid}.csv", parse_dates=["observation_date"]).set_index("observation_date").iloc[:, 0].astype(float)
        ser[sid] = s.replace(0, np.nan)
    cal = pd.date_range("2023-10-01", "2026-10-31")
    F = pd.DataFrame({k: v.reindex(cal).ffill() for k, v in ser.items()})
    F = F.shift(2)                                                       # el dato de D-2 es el ultimo publicado de forma segura al operar el dia D
    X = pd.DataFrame(index=cal)
    X["real10_chg20"] = F.DFII10 - F.DFII10.shift(20)
    X["nom10_chg20"] = F.DGS10 - F.DGS10.shift(20)
    X["breakeven_chg20"] = F.T10YIE - F.T10YIE.shift(20)
    X["usd_ret20"] = F.DTWEXBGS / F.DTWEXBGS.shift(20) - 1
    X["vix_level_rank"] = F.VIXCLS.rolling(250, min_periods=120).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True)
    X["vix_chg20"] = F.VIXCLS - F.VIXCLS.shift(20)
    rows = []
    # (a) D1: retorno futuro 5d escalado vs variable (z-score expansivo, sin look-ahead)
    y, _ = vol_scaled_forward(d_d1, 5)
    dd = d_d1.time.dt.normalize()
    split = np.array([split_of(t) for t in d_d1.time])
    for k in X.columns:
        v = X[k].reindex(dd).values
        z = (v - pd.Series(v).expanding(60).mean().values) / pd.Series(v).expanding(60).std().values
        r = ols_hac(y, z, 5)
        if r is None:
            continue
        sp = {}
        row = dict(analisis="oro D1: retorno futuro 5d ~ variable (z expansivo)", variable=k, n=r[2], pendiente=round(float(r[0][0]), 4), t_hac=round(float(r[1][0]), 2))
        for s_ in ("DEV", "SEL", "VAL"):
            rr = ols_hac(np.where(split == s_, y, np.nan), np.where(split == s_, z, np.nan), 5)
            sp[s_] = (float(rr[0][0]), float(rr[1][0])) if rr else None
            row[f"pend_{s_}"] = round(sp[s_][0], 4) if rr else np.nan; row[f"t_{s_}"] = round(sp[s_][1], 2) if rr else np.nan
        row["clase"] = classify(row["pendiente"], row["t_hac"], r[2], sp, 100 if r[2] > 300 else 0)
        row["nota"] = "relacion economica esperada: tasas reales/dolar/VIX con signo propio; aqui solo se mide estabilidad de signo"
        rows.append(row)
    # (b) expectativa de las 248 operaciones de la ruptura por tercil de cada variable (conocida en la fecha de entrada)
    td = trades.open_time.dt.normalize()
    for k in X.columns:
        v = X[k].reindex(td).values
        q = pd.qcut(pd.Series(v), 3, labels=["bajo", "medio", "alto"], duplicates="drop")
        for lab in q.cat.categories:
            m = (q == lab).values; s = summ(trades.R.values[m])
            rows.append(dict(analisis="ruptura H4 (248 op. oficiales) por tercil de la variable", variable=k, tercil=lab, n=s["n"], pendiente=s["expR"], t_hac=s["t"], pf=s["pf"], clase="D" if abs(s["t"]) < 2 else "C",
                             nota="retrospectivo; 3 terciles x 6 variables = 18 comparaciones"))
    X.to_csv(RES.parent / "results" / "v10" / "economic_features_lag2d.csv")
    return pd.DataFrame(rows)


def main():
    d4 = bars("H4"); d1 = bars("D1"); dh = bars("H1"); dm = m15().assign(er30=lambda x: np.nan)
    rows = []
    rows += tsmom_tests("D1", d1, (5, 21, 63), (1, 5, 21), "persistencia de tendencias en series temporales (Moskowitz-Ooi-Pedersen 2012): retornos pasados predicen los futuros a 1-12 meses por reaccion lenta a la informacion y flujos de cobertura", "D1")
    rows += tsmom_tests("H4", d4, (6, 30, 126), (6, 30), "mismo mecanismo a escala intradia/semanal; no es transferible automaticamente desde futuros mensuales", "H4")
    rows += tsmom_tests("H1", dh, (4, 24, 120), (4, 24), "replica en H1 de las escalas 4h/1d/5d", "H1")
    dm2 = dm.copy(); rows += tsmom_tests("M15", dm2, (16, 96), (16, 96), "observacion complementaria M15 (4h y 1d)", "M15")
    rows.append(reversal_tests("H4", d4, 30, 6)); rows.append(reversal_tests("H1", dh, 24, 6)); rows.append(reversal_tests("D1", d1, 5, 5)); rows.append(reversal_tests("M15", dm2, 32, 8))
    rows += conditioned_tests(d4)
    br, B = breakout_tests(d4); rows += br
    M = pd.DataFrame(rows)
    M.insert(0, "exp_id", [f"V10M_{i:03d}" for i in range(len(M))])
    M.to_csv(RES / "V10_MOMENTUM_RESEARCH.csv", index=False)
    VR, _ = vol_regime_table(d4, B); VR.to_csv(RES / "V10_VOLATILITY_REGIMES.csv", index=False)
    from research.v10_h4_audit import prep
    _, t = prep()
    ER = economic_regimes(d4, d1, t); ER.insert(0, "exp_id", [f"V10E_{i:03d}" for i in range(len(ER))]); ER.to_csv(RES / "V10_ECONOMIC_REGIMES.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); pd.set_option("display.max_colwidth", 60)
    print(M[["hipotesis", "n", "pendiente", "t_hac", "pend_DEV", "pend_SEL", "pend_VAL", "t_VAL", "clase"]].to_string())
    print(M.clase.value_counts().to_dict()); print(VR.to_string()); print(ER[ER.analisis.str.startswith("oro")][["variable", "n", "pendiente", "t_hac", "pend_DEV", "pend_SEL", "pend_VAL", "clase"]].to_string())
    print(ER[~ER.analisis.str.startswith("oro")][["variable", "tercil", "n", "pendiente", "t_hac"]].to_string())


if __name__ == "__main__":
    main()

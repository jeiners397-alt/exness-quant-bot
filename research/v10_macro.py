"""V10 Lote C - ventanas de anuncios macro en XAUUSDm (NFP, CPI, FOMC) y procedencia de datos.
Fuentes: fechas de NFP/CPI = enlaces de archivo de BLS (bls.gov/bls/news-release/{empsit,cpi}.htm, hora 08:30 ET); FOMC = federalreserve.gov/monetarypolicy/fomccalendars.htm
(declaracion 14:00 ET, ultimo dia de la reunion). NO hay consenso verificable (ALFRED/FRED API/BLS directo no accesibles desde el equipo; ningun proveedor de consenso gratuito
verificable) => solo estudio de ventanas, SIN sorpresas. Series de mercado de FRED (DFII10, DGS10, T10YIE, DTWEXBGS, VIXCLS) solo en research/V10_ECONOMIC_REGIMES.csv.
Control: misma hora del dia en +-1 y +-2 semanas (mismo dia de la semana) sin ningun otro evento ese dia."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from research.v10_common import DATA, RES, ROOT, m5, sha256, split_of, norm_cdf

NFP = {  # fecha de publicacion -> mes de referencia (BLS, enlaces de archivo)
    "2024-01-05": "2023-12", "2024-02-02": "2024-01", "2024-03-08": "2024-02", "2024-04-05": "2024-03", "2024-05-03": "2024-04", "2024-06-07": "2024-05",
    "2024-07-05": "2024-06", "2024-08-02": "2024-07", "2024-09-06": "2024-08", "2024-10-04": "2024-09", "2024-11-01": "2024-10", "2024-12-06": "2024-11",
    "2025-01-10": "2024-12", "2025-02-07": "2025-01", "2025-03-07": "2025-02", "2025-04-04": "2025-03", "2025-05-02": "2025-04", "2025-06-06": "2025-05",
    "2025-07-03": "2025-06", "2025-08-01": "2025-07", "2025-09-05": "2025-08", "2025-11-20": "2025-09", "2025-12-16": "2025-11",
    "2026-01-09": "2025-12", "2026-02-11": "2026-01", "2026-03-06": "2026-02", "2026-04-03": "2026-03", "2026-05-08": "2026-04", "2026-06-05": "2026-05",
    "2026-07-02": "2026-06", "2026-08-07": "2026-07", "2026-09-04": "2026-08", "2026-10-02": "2026-09"}
CPI = {
    "2024-01-11": "2023-12", "2024-02-13": "2024-01", "2024-03-12": "2024-02", "2024-04-10": "2024-03", "2024-05-15": "2024-04", "2024-06-12": "2024-05",
    "2024-07-11": "2024-06", "2024-08-14": "2024-07", "2024-09-11": "2024-08", "2024-10-10": "2024-09", "2024-11-13": "2024-10", "2024-12-11": "2024-11",
    "2025-01-15": "2024-12", "2025-02-12": "2025-01", "2025-03-12": "2025-02", "2025-04-10": "2025-03", "2025-05-13": "2025-04", "2025-06-11": "2025-05",
    "2025-07-15": "2025-06", "2025-08-12": "2025-07", "2025-09-11": "2025-08", "2025-10-24": "2025-09", "2025-12-18": "2025-11",
    "2026-01-13": "2025-12", "2026-02-13": "2026-01", "2026-03-11": "2026-02", "2026-04-10": "2026-03", "2026-05-12": "2026-04", "2026-06-10": "2026-05",
    "2026-07-14": "2026-06", "2026-08-12": "2026-07", "2026-09-11": "2026-08", "2026-10-14": "2026-09"}
FOMC = ["2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
        "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
        "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28"]


def us_dst(d: dt.date) -> bool:
    """Horario de verano de EE.UU.: 2o domingo de marzo 02:00 local -> 1er domingo de noviembre 02:00 (aqui por fecha, los eventos son >= 08:30 ET)."""
    def nth_sun(y, m, n):
        d0 = dt.date(y, m, 1); first = d0 + dt.timedelta(days=(6 - d0.weekday()) % 7); return first + dt.timedelta(days=7 * (n - 1))
    return nth_sun(d.year, 3, 2) <= d < nth_sun(d.year, 11, 1)


def to_utc(date: str, hhmm: str) -> pd.Timestamp:
    d = dt.date.fromisoformat(date); h, m = map(int, hhmm.split(":"))
    off = 4 if us_dst(d) else 5
    return pd.Timestamp(dt.datetime(d.year, d.month, d.day, h, m) + dt.timedelta(hours=off))


def calendar() -> pd.DataFrame:
    rows = []
    for k, ref in NFP.items():
        rows.append(dict(event="NFP", date_local=k, ref=ref, time_local="08:30", tz="America/New_York"))
    for k, ref in CPI.items():
        rows.append(dict(event="CPI", date_local=k, ref=ref, time_local="08:30", tz="America/New_York"))
    for k in FOMC:
        rows.append(dict(event="FOMC", date_local=k, ref="", time_local="14:00", tz="America/New_York"))
    c = pd.DataFrame(rows)
    # plausibilidad: ningun evento en fin de semana
    c["dow"] = pd.to_datetime(c.date_local).dt.dayofweek
    assert (c.dow < 5).all(), "fecha de evento en fin de semana"
    c["utc"] = [to_utc(d, t) for d, t in zip(c.date_local, c.time_local)]
    c["dst"] = [us_dst(dt.date.fromisoformat(d)) for d in c.date_local]
    return c.sort_values("utc").reset_index(drop=True)


def metrics(m: pd.DataFrame, ts: pd.Timestamp, pos: dict) -> dict | None:
    """m: M5 indexado por posicion; pos: tiempo->indice. Todas las medidas usan solo barras con apertura en la ventana."""
    i0 = pos.get(ts)
    if i0 is None or i0 < 14 or i0 + 60 >= len(m):
        return None
    o, h, l, c, sp = (m[k].values for k in ("open", "high", "low", "close", "spr"))
    # comprobar que la rejilla de 5 min no tiene huecos en [-12, +48] barras
    if (m.time.values[i0 + 12] - m.time.values[i0 - 12]) != np.timedelta64(24 * 5, "m").astype("timedelta64[ns]"):
        return None
    full240 = (m.time.values[i0 + 48] - m.time.values[i0]) == np.timedelta64(240, "m").astype("timedelta64[ns]")
    p0 = o[i0]
    r = lambda k: o[i0 + k // 5] - p0
    pre = slice(i0 - 12, i0); post = slice(i0, i0 + 12)
    ret5 = c - o                                   # retorno intra-barra: la ventana previa [-60,0) no incluye la barra del evento
    rv_pre = np.std(ret5[i0 - 12:i0]); rv_post = np.std(ret5[i0:i0 + 12])
    atr_pre = np.mean(h[i0 - 14:i0] - l[i0 - 14:i0])
    out = dict(p0=p0, ret_pre60=p0 - o[i0 - 12], ret_pre15=p0 - o[i0 - 3], atr_m5_pre=atr_pre,
               ret_5=r(5), ret_15=r(15), ret_30=r(30), ret_60=r(60), ret_240=(o[i0 + 48] - p0) if full240 else np.nan,
               range_pre30=h[i0 - 6:i0].max() - l[i0 - 6:i0].min(),
               range_post30=h[i0:i0 + 6].max() - l[i0:i0 + 6].min(),
               mfe_up30=h[i0:i0 + 6].max() - p0, mae_dn30=p0 - l[i0:i0 + 6].min(),
               rv_pre60=rv_pre, rv_post60=rv_post, rv_ratio=rv_post / rv_pre if rv_pre > 0 else np.nan,
               spread_T=float(np.mean(sp[i0:i0 + 2])), spread_pre=float(np.mean(sp[i0 - 12:i0 - 2])))
    out["cont_15_60"] = np.sign(out["ret_15"]) * (out["ret_60"] - out["ret_15"])
    out["rev_flag"] = float(out["cont_15_60"] < 0)
    return out


def main():
    c = calendar()
    m = m5()
    pos = {t: i for i, t in enumerate(m.time)}
    event_days = set(c.utc.dt.normalize())
    rows = []
    for _, e in c.iterrows():
        if e.utc >= pd.Timestamp("2026-11-01") or e.utc < m.time.iloc[0] + pd.Timedelta(hours=2):
            continue
        x = metrics(m, e.utc, pos)
        if x is None:
            continue
        ctrl = []
        for wk in (-14, -7, 7, 14):
            tc = e.utc + pd.Timedelta(days=wk)
            if tc.normalize() in event_days:
                continue
            y = metrics(m, tc, pos)
            if y is not None:
                ctrl.append(y)
        cm = {f"ctrl_{k}": np.mean([abs(y[k]) if k.startswith("ret") else y[k] for y in ctrl]) if ctrl else np.nan for k in ("ret_15", "ret_60", "range_post30", "rv_ratio", "spread_T")}
        rows.append(dict(event=e.event, ref_month=e.ref, date_local=e.date_local, time_local=e.time_local, tz=e.tz, dst_us=e.dst, utc=e.utc, split=split_of(e.utc),
                         n_controls=len(ctrl), consensus="NO_DISPONIBLE (sin fuente verificable)", surprise="NO_CALCULADA", **x, **cm))
    E = pd.DataFrame(rows)
    E["range_ratio"] = E.range_post30 / E.ctrl_range_post30
    E["abs_ret15_ratio"] = E.ret_15.abs() / E.ctrl_ret_15
    E["spread_ratio"] = E.spread_T / E.ctrl_spread_T
    E.to_csv(RES / "V10_MACRO_EVENTS.csv", index=False)

    # resumen por tipo y comprobacion de marca de tiempo (pico de rango en la ranura T)
    S = []
    for ev, g in E.groupby("event"):
        t_rr = (np.log(g.range_ratio.clip(lower=1e-3))).mean() / (np.log(g.range_ratio.clip(lower=1e-3)).std(ddof=1) / np.sqrt(len(g)))
        S.append(dict(event=ev, n=len(g), mediana_rango30_USD=round(g.range_post30.median(), 2), mediana_rango30_ctrl=round(g.ctrl_range_post30.median(), 2),
                      razon_rango_media_geom=round(float(np.exp(np.log(g.range_ratio.clip(lower=1e-3)).mean())), 2), t_log_razon=round(float(t_rr), 2),
                      mediana_abs_ret15=round(g.ret_15.abs().median(), 2), mediana_abs_ret15_ctrl=round(g.ctrl_ret_15.median(), 2),
                      razon_vol_post_pre_mediana=round(g.rv_ratio.median(), 2), razon_spread_mediana=round(g.spread_ratio.median(), 2),
                      p_continuacion_15_60=round(float((g.cont_15_60 > 0).mean()), 3), p_reversion_15_60=round(float((g.cont_15_60 < 0).mean()), 3),
                      mediana_cont_15_60_USD=round(g.cont_15_60.median(), 2), media_ret_signed_0_240=round(g.ret_240.mean(), 2),
                      t_ret240=round(g.ret_240.mean() / (g.ret_240.std(ddof=1) / np.sqrt(g.ret_240.count())), 2)))
    # marca de tiempo: ranura de 5 min con mayor rango medio en [-30,+30] min, por regimen de horario de verano
    chk = []
    for (ev, dst), g in E.groupby(["event", "dst_us"]):
        prof = np.zeros(13); k = 0
        for t in g.utc:
            i0 = pos.get(t)
            if i0 is None or i0 < 6 or i0 + 7 >= len(m):
                continue
            prof += (m.high.values[i0 - 6:i0 + 7] - m.low.values[i0 - 6:i0 + 7]); k += 1
        if k:
            chk.append(dict(event=ev, dst_us=dst, n=k, ranura_max_rango_min_respecto_T=int((np.argmax(prof) - 6) * 5), utc_hora_evento=g.utc.dt.strftime("%H:%M").iloc[0]))
    pd.DataFrame(S).to_csv(RES / "V10_MACRO_SUMMARY.csv", index=False)
    pd.DataFrame(chk).to_csv(RES / "V10_MACRO_TIMESTAMP_CHECK.csv", index=False)
    print(pd.DataFrame(S).T.to_string()); print(pd.DataFrame(chk).to_string())
    return E


def provenance():
    rows = []
    src = {"DFII10": "tasa real 10a (TIPS)", "DGS10": "rendimiento nominal Tesoro 10a", "T10YIE": "inflacion implicita 10a (breakeven)", "DTWEXBGS": "indice dolar amplio nominal", "VIXCLS": "VIX"}
    for sid, desc in src.items():
        p = DATA / "v10" / f"fred_{sid}.csv"
        d = pd.read_csv(p)
        rows.append(dict(fuente=f"FRED {sid}", descripcion=desc, url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=2023-10-01&coed=2026-10-31",
                         acceso="WebFetch (la maquina local no alcanza fred.stlouisfed.org: timeouts); CSV bruto guardado tal cual", archivo=str(p.relative_to(ROOT)), sha256=sha256(p),
                         filas=len(d), primera=d.iloc[0, 0], ultima=d.iloc[-1, 0], revisiones="serie de mercado, no revisada; se usa con retardo de 2 dias de calendario (publicacion D+1 tarde)",
                         consenso="n/a", verificacion="cabecera/forma del CSV y ultima fecha 2026-10-30"))
    rows += [
        dict(fuente="BLS Employment Situation (NFP) - fechas", descripcion="fecha de publicacion = codigo de fecha del enlace de archivo; 08:30 ET",
             url="https://www.bls.gov/bls/news-release/empsit.htm", acceso="WebFetch (bls.gov directo da 403 al script local); extraccion por resumidor", archivo="research/v10_macro.py::NFP",
             sha256="n/a", filas=len(NFP), primera=min(NFP), ultima=max(NFP), revisiones="solo fechas (no el valor); 2025-10 no publicado (cierre federal) y 2025-09/11 retrasados",
             consenso="NO_DISPONIBLE", verificacion="todas las fechas son dias laborables; el pico de volatilidad cae en la ranura T segun V10_MACRO_TIMESTAMP_CHECK.csv"),
        dict(fuente="BLS CPI - fechas", descripcion="fecha de publicacion = codigo de fecha del enlace de archivo; 08:30 ET", url="https://www.bls.gov/bls/news-release/cpi.htm",
             acceso="WebFetch; extraccion por resumidor", archivo="research/v10_macro.py::CPI", sha256="n/a", filas=len(CPI), primera=min(CPI), ultima=max(CPI),
             revisiones="solo fechas; 2025-10 no publicado", consenso="NO_DISPONIBLE", verificacion="dias laborables; comprobacion de ranura de volatilidad"),
        dict(fuente="Federal Reserve FOMC", descripcion="ultimo dia de reunion, declaracion 14:00 ET", url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
             acceso="descarga directa (HTML guardado)", archivo="data/raw/v10/fomccalendars.html", sha256=sha256(DATA / "v10" / "fomccalendars.html"), filas=len(FOMC), primera=min(FOMC), ultima=max(FOMC),
             revisiones="n/a", consenso="NO_DISPONIBLE", verificacion="fechas contrastadas con los rangos 'mes d-d' del HTML"),
        dict(fuente="ALFRED / FRED API (vintages, revisiones, consenso)", descripcion="valores publicados por vintage", url="https://alfred.stlouisfed.org/", acceso="NO ACCESIBLE desde el equipo local (timeouts / reset)",
             archivo="", sha256="", filas=0, primera="", ultima="", revisiones="no se usaron valores de NFP/CPI: no se calculan sorpresas ni se usan datos revisados", consenso="NO_DISPONIBLE", verificacion="estado: F (datos insuficientes)"),
    ]
    P = pd.DataFrame(rows); P.to_csv(RES / "V10_MACRO_DATA_PROVENANCE.csv", index=False); return P


if __name__ == "__main__":
    provenance(); main()


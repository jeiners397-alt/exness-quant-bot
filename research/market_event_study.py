"""Estudio de eventos multimercado sobre barras M15 reales del terminal aislado (solo lectura). Definiciones matematicas reproducibles:
 E1_SWEEP   : high[t] > PDH + 0.1*ATR y close[t] < PDH  (corto)  /  low[t] < PDL - 0.1*ATR y close[t] > PDL (largo)      -> reversion
 E2_BREAKOUT: close[t] > max(high[t-48..t-1]) con rango[t] >= ATR (largo) / simetrico (corto)                           -> continuacion
 E3_ZFADE   : z=(close-SMA50)/sd50 ; z <= -2.5 largo / z >= 2.5 corto                                                    -> reversion a la media
 E4_ZCONT   : mismo evento que E3 con direccion opuesta (continuacion)  [control de direccion]
Retorno posterior desde la APERTURA de la barra t+1, en unidades de ATR14(t), a 4/8/16 barras, neto de spread (spread de la barra de entrada).
Control: mismo numero de barras aleatorias con la MISMA distribucion horaria y direccion aleatoria, 500 sorteos -> p unilateral del retorno neto medio.
NO se afirma nada sobre ordenes institucionales: son regularidades estadisticas de precio."""
from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LAB = Path(r"C:\REMIX_MT5_LAB\terminal")
OUT = ROOT / "research" / "EVENT_STUDY_RESULTS.csv"
HORIZONS = (4, 8, 16)
rng = np.random.default_rng(20261109)


def atr(df, n=14):
    pc = df.close.shift(1)
    tr = pd.concat([df.high - df.low, (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def events(df):
    a = atr(df)
    day = df.time.dt.floor("D")
    dh = df.groupby(day).high.max(); dl = df.groupby(day).low.min()
    pdh = day.map(dh.shift(1).reindex(dh.index).rename(None).to_dict() if False else dict(zip(dh.index[1:], dh.values[:-1])))
    pdl = day.map(dict(zip(dl.index[1:], dl.values[:-1])))
    ev = {}
    d1 = np.zeros(len(df), int)
    d1[((df.high > pdh + 0.1 * a) & (df.close < pdh)).values] = -1
    d1[((df.low < pdl - 0.1 * a) & (df.close > pdl)).values] = 1
    ev["E1_SWEEP"] = d1
    hh = df.high.shift(1).rolling(48).max(); ll = df.low.shift(1).rolling(48).min()
    rngb = df.high - df.low
    d2 = np.zeros(len(df), int)
    d2[((df.close > hh) & (rngb >= a)).values] = 1
    d2[((df.close < ll) & (rngb >= a)).values] = -1
    ev["E2_BREAKOUT"] = d2
    z = (df.close - df.close.rolling(50).mean()) / df.close.rolling(50).std(ddof=0)
    d3 = np.zeros(len(df), int)
    d3[(z <= -2.5).values] = 1
    d3[(z >= 2.5).values] = -1
    ev["E3_ZFADE"] = d3
    ev["E4_ZCONT"] = -d3
    return ev, a


def fwd(df, a, idx, dirs, h, point, ext=False):
    """retorno firmado a h barras desde open[t+1], MFE/MAE firmados dentro de h barras, todo en ATR; coste = spread de la barra de entrada."""
    o = df.open.values; hi = df.high.values; lo = df.low.values; cl = df.close.values; sp = df.spread.values * point
    n = len(df)
    ok = idx + h + 1 < n
    idx, dirs = idx[ok], dirs[ok]
    ent = o[idx + 1]
    ex = cl[idx + h]
    ar = a.values[idx]
    good = ar > 0
    idx, dirs, ent, ex, ar = idx[good], dirs[good], ent[good], ex[good], ar[good]
    gross = dirs * (ex - ent) / ar
    cost = sp[idx + 1] / ar + 0.0
    if not ext:
        return gross, gross - cost, None, None, idx
    mfe = np.array([(dirs[k] * ((hi[i + 1:i + h + 1].max() if dirs[k] > 0 else lo[i + 1:i + h + 1].min()) - ent[k])) / ar[k] for k, i in enumerate(idx)])
    mae = np.array([(dirs[k] * ((lo[i + 1:i + h + 1].min() if dirs[k] > 0 else hi[i + 1:i + h + 1].max()) - ent[k])) / ar[k] for k, i in enumerate(idx)])
    return gross, gross - cost, mfe, mae, idx


def run(symbols):
    assert mt5.initialize(path=str(LAB / "terminal64.exe"), portable=True), mt5.last_error()
    rows, ntests = [], 0
    for sym in symbols:
        info = mt5.symbol_info(sym)
        if info is None:
            print("sin simbolo", sym); continue
        mt5.symbol_select(sym, True)
        r = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M15, datetime(2024, 1, 1), datetime(2026, 11, 1))
        if r is None or len(r) < 5000:
            print(sym, "historial M15 insuficiente", None if r is None else len(r)); continue
        df = pd.DataFrame(r); df["time"] = pd.to_datetime(df.time, unit="s")
        first = df.time.iloc[0]
        ev, a = events(df)
        hours = df.time.dt.hour.values
        for name, d in ev.items():
            idx_all = np.flatnonzero(d != 0)
            if len(idx_all) < 30:
                rows.append(dict(symbol=sym, event=name, horizon="", n=len(idx_all), note="n<30: no se evalua", first_bar=first)); continue
            for h in HORIZONS:
                g, net, mfe, mae, idx = fwd(df, a, idx_all, d[idx_all], h, info.point, ext=True)
                n = len(net)
                if n < 30: continue
                ntests += 1
                t = net.mean() / (net.std(ddof=1) / np.sqrt(n)) if net.std() > 0 else 0.0
                # control: mismas horas, direccion aleatoria
                cm = []
                pool_by_h = {hh: np.flatnonzero(hours == hh) for hh in np.unique(hours[idx])}
                for _ in range(500):
                    pick = np.concatenate([rng.choice(pool_by_h[hh], size=int((hours[idx] == hh).sum())) for hh in pool_by_h])
                    dd = rng.choice([-1, 1], size=len(pick))
                    _, nn, _, _, _ = fwd(df, a, pick, dd, h, info.point)
                    cm.append(nn.mean())
                cm = np.array(cm)
                rows.append(dict(symbol=sym, event=name, horizon=h, n=n, mean_gross_ATR=round(float(g.mean()), 4), mean_net_ATR=round(float(net.mean()), 4), t_net=round(float(t), 2),
                                 control_mean_net=round(float(cm.mean()), 4), p_control=round(float((cm >= net.mean()).mean()), 3), mean_MFE_ATR=round(float(mfe.mean()), 3),
                                 mean_MAE_ATR=round(float(mae.mean()), 3), p_continuation=round(float((g > 0).mean()), 3), first_bar=first.strftime("%Y-%m-%d"), note=""))
        print(sym, "ok", len(df), "barras", flush=True)
    mt5.shutdown()
    for r in rows:
        r["tests_total"] = ntests
        r["bonferroni_t_threshold"] = round(float(np.sqrt(2 * np.log(max(ntests, 2)))), 2)
    keys = ["symbol", "event", "horizon", "n", "mean_gross_ATR", "mean_net_ATR", "t_net", "control_mean_net", "p_control", "mean_MFE_ATR", "mean_MAE_ATR", "p_continuation",
            "first_bar", "note", "tests_total", "bonferroni_t_threshold"]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); [w.writerow({k: r.get(k, "") for k in keys}) for r in rows]
    print(len(rows), "filas;", ntests, "pruebas")


if __name__ == "__main__":
    run(sys.argv[1:])

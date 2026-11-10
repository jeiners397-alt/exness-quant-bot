"""V8 Lote A - referencia Python de la hipotesis V7 XAUUSDm H1 E02_SWEEP_96 *inverted*.

Definicion EXACTA recuperada del codigo de V7 (research/v7_event_study.py::ev_sweep_96):
  senal en la vela i cerrada: high_i > max(high[i-96..i-1]) + 0.1*ATR_i  Y  close_i < ese maximo  (pico que CIERRA DENTRO)
  (simetrico en minimos).  Variante 'primary' = reversion (corto tras pico al alza); 'inverted' = largo (continuacion del pico).
  => NO es 'ruptura con cierre fuera' como se describio en los informes V7: es un pico (sweep) que cierra de vuelta dentro,
     operado en la direccion del pico. La variante B (cierre fuera, E03-like con N=96) se prueba aparte, declarada como hipotesis distinta.
Entrada: apertura de la vela i+1 (mercado). SL = 1 ATR_i, TP = RR*ATR_i, salida temporal al cierre de la vela i+40,
empate SL/TP en la misma vela => SL. Coste = spread medio de la vela de entrada / ATR_i (en R). Enfriamiento 12 velas.
Salida: results/v8/xau_h1_reference_trades.csv  y  research/V8_XAU_H1_PARITY.csv (parte Python).
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ["V7_TF"] = "H1"
import numpy as np
import pandas as pd

from research import v7_event_study as V

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "v8"
OUT.mkdir(parents=True, exist_ok=True)
SYM = "XAUUSDm"
MAXH = 40


def signals(d: pd.DataFrame, variant: str = "A_V7_SWEEP_INV", n: int = 96):
    """Devuelve (idx, dir) ya deduplicados (enfriamiento 12 velas)."""
    if variant == "A_V7_SWEEP_INV":
        idx, dr, _ = V.ev_sweep_96(d)
        idx, dr, _ = V.dedupe(idx, dr, None)
        return idx, -dr                              # invertido = continuacion del pico
    if variant == "B_CLOSE_OUTSIDE":                  # cierre fuera del nivel de n velas (primera vela que cierra fuera)
        c = d.close.values
        ph = d.high.rolling(n).max().shift(1).values; pl = d.low.rolling(n).min().shift(1).values
        up = (c > ph) & np.r_[False, c[:-1] <= ph[:-1]]; dn = (c < pl) & np.r_[False, c[:-1] >= pl[:-1]]
        idx = np.where(up | dn)[0]; dr = np.where(up, 1, -1)[up | dn]
        idx, dr, _ = V.dedupe(idx, dr, None)
        return idx, dr
    raise ValueError(variant)


def trades(d: pd.DataFrame, idx, dr, rr: float, sl_atr: float = 1.0) -> pd.DataFrame:
    o, h, l, c, a, sp, t = (d[k].values for k in ("open", "high", "low", "close", "atr", "spr", "time"))
    rows = []
    for i, s in zip(idx, dr):
        if i + 1 + MAXH >= len(d) or np.isnan(a[i]) or a[i] <= 0:
            continue
        e = o[i + 1]; at = a[i]; sl = e - s * sl_atr * at; tp = e + s * rr * sl_atr * at
        ex_i, ex_p, why = i + MAXH, c[i + MAXH], "TIME"
        for j in range(i + 1, i + MAXH + 1):
            hit_sl = (l[j] <= sl) if s > 0 else (h[j] >= sl)
            hit_tp = (h[j] >= tp) if s > 0 else (l[j] <= tp)
            if hit_sl:
                ex_i, ex_p, why = j, sl, "SL"; break
            if hit_tp:
                ex_i, ex_p, why = j, tp, "TP"; break
        gross = s * (ex_p - e) / (sl_atr * at)
        cost = sp[i + 1] / (sl_atr * at)
        rows.append(dict(signal_time=t[i], entry_time=t[i + 1], dir=int(s), entry=e, sl=sl, tp=tp, atr=at, exit_time=t[ex_i], exit_price=ex_p, reason=why,
                         R_gross=gross, cost_R=cost, R_net=gross - cost, spread_entry=sp[i + 1]))
    return pd.DataFrame(rows)


def main():
    d = V.load(SYM)
    res = []
    for var in ("A_V7_SWEEP_INV", "B_CLOSE_OUTSIDE"):
        idx, dr = signals(d, var)
        for rr in (1.5, 3.0):
            T = trades(d, idx, dr, rr)
            T.insert(0, "variant", var); T.insert(1, "rr", rr)
            T.to_csv(OUT / f"xau_h1_reference_{var}_rr{rr}.csv", index=False)
            for name, m in (("IS", T.entry_time < V.SPLIT), ("OOS", T.entry_time >= V.SPLIT), ("ALL", T.entry_time > "1900")):
                x = T[m]
                t_, _ = V.tstat(x.R_net) if len(x) > 2 else (np.nan, np.nan)
                res.append(dict(variant=var, rr=rr, split=name, n=len(x), expR_net=round(x.R_net.mean(), 4), expR_gross=round(x.R_gross.mean(), 4), t=round(t_, 2),
                                win_rate=round((x.R_net > 0).mean(), 3), cost_R=round(x.cost_R.mean(), 4), sum_R=round(x.R_net.sum(), 2)))
    R = pd.DataFrame(res)
    R.to_csv(OUT / "xau_h1_reference_summary.csv", index=False)
    print(R.to_string())


if __name__ == "__main__":
    main()

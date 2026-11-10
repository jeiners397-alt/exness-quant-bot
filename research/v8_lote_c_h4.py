"""V8 Lote C (verificacion) - referencia Python de XAUUSDm H4 A1_BREAKOUT20 (primera vela que cierra fuera del rango de 20 velas, continuacion, enfriamiento 6)
+ sensibilidad de parametros (ventana, SL, RR) y estabilidad anual/direccion. Pista de clase C del lote B; las ejecuciones oficiales ya existen (runs 012/013)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from research import v8_htf_event_study as H
from research import v8_xau_h1_reference as R1

V = H.V
OUT = R1.OUT


def signals_n(d: pd.DataFrame, n: int):
    c = d.close.values
    hh = d.high.rolling(n).max().shift(1).values; ll = d.low.rolling(n).min().shift(1).values
    up, dn = H._up_dn(c, hh, ll)
    idx = np.where(up | dn)[0]; dr = np.where(up, 1, -1)[up | dn]
    keep = idx > 60
    idx, dr, _ = V.dedupe(idx[keep], dr[keep], None)
    return idx, dr


def main():
    d = H.load_htf("XAUUSDm", "H4")
    idx, dr = signals_n(d, 20)
    for rr in (2.0, 3.0):
        T = R1.trades(d, idx, dr, rr); T.insert(0, "variant", "H4A1"); T.insert(1, "rr", rr)
        T.to_csv(OUT / f"xau_h1_reference_H4A1_rr{rr}.csv", index=False)
        print("ref H4A1", rr, len(T), round(T.R_net.mean(), 4))
    rows = []
    # sensibilidad (cada celda cuenta en el registro de pruebas): ventana x SL(ATR) x RR
    for n in (10, 15, 20, 30, 40, 55):
        ix, dd = signals_n(d, n)
        for sl in (0.75, 1.0, 1.5):
            for rr in (1.5, 2.0, 3.0):
                T = R1.trades(d, ix, dd, rr, sl_atr=sl)
                is_, oos = T[T.entry_time < V.SPLIT], T[T.entry_time >= V.SPLIT]
                t_all, _ = V.tstat(T.R_net)
                rows.append(dict(tf="H4", symbol="XAUUSDm", window=n, sl_atr=sl, rr=rr, n=len(T), expR_net=round(T.R_net.mean(), 4), t=round(t_all, 2), expR_IS=round(is_.R_net.mean(), 4), n_IS=len(is_),
                                 expR_OOS=round(oos.R_net.mean(), 4), n_OOS=len(oos), pf_R=round(T.R_net[T.R_net > 0].sum() / -T.R_net[T.R_net < 0].sum(), 3), sum_R=round(T.R_net.sum(), 1)))
    S = pd.DataFrame(rows)
    S["es_referencia_prefijada"] = (S.window == 20) & (S.sl_atr == 1.0)
    S.to_csv(OUT.parent.parent / "research" / "V8_H4_SENSITIVITY.csv", index=False)
    print(S.pivot_table(index=["window", "sl_atr"], columns="rr", values="expR_net").round(3).to_string())
    print("fraccion de celdas con expR>0:", round((S.expR_net > 0).mean(), 3), " con t>=2:", round((S.t >= 2).mean(), 3), " n celdas", len(S))


if __name__ == "__main__":
    main()


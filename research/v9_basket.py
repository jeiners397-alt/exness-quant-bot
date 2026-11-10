"""V9 Fases 10/12/13 - posiciones multiples, gestion por cesta y cobertura (hedging): simulador barra a barra sobre las MISMAS senales, cuenta compartida de 3000 USD, lote 0.01 (1 USD por 1 USD de precio).
Costes: spread real de la vela de entrada por posicion (la cobertura paga un segundo spread). SL/TP evaluados con barras (SL gana empates). La equidad incluye PnL flotante al cierre de cada vela.
Politicas: individual (referencia), una_posicion, max3, cierre_en_opuesta, cobertura_perdedora (abre la contraria al llegar a -0.7R; el par se cierra por tiempo), cesta_sin_SL (TP/SL conjunto, sin SL individual),
cesta_con_SL (SL individual + TP conjunto). Ninguna usa martingala ni aumenta el lote tras perder.
Senales: (1) XAU H4 baseline congelada (breakout 20, cooldown 6, SL 1 ATR, TP 2R, 40 velas); (2) el 'mejor' scalping M5 XAU por t_DEV (G_SESSION_ORB) solo como contraste (sin ventaja bruta)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from research import v8_htf_event_study as H
from research import v8_lote_c_h4 as C4
from research import v9_scalp_study as S

V = S.V
CAP = 3000.0
LOT_USD = 1.0            # 0.01 lote x 100 oz
LEV = 500.0


def simulate(d, sig, pol: str, rr=2.0, sl_atr=1.0, hold=40, btp=2.0, bsl=-3.0):
    o, h, l, c, a, sp = (d[k].values for k in ("open", "high", "low", "close", "atr", "spr"))
    sig = dict((int(i), int(s)) for i, s in sig)
    pos, closed = [], []
    eq_real = 0.0
    dd_peak, max_dd, worst_float = CAP, 0.0, 0.0
    conc, maxconc, maxmargin = [], 0, 0.0
    first = min(sig) + 1; last = len(d) - 1

    def close(p, px, j, why):
        nonlocal eq_real
        pnl = p["dir"] * (px - p["entry"]) * LOT_USD - p["cost"]
        eq_real += pnl; closed.append(dict(pnl=pnl, R=pnl / (p["atr"] * sl_atr * LOT_USD), why=why, bars=j - p["bar"], hedged=p["hedged"])); p["alive"] = False

    for j in range(first, last):
        # nuevas entradas (senal en j-1, entrada en apertura de j)
        if (j - 1) in sig:
            s = sig[j - 1]; alive = [p for p in pos if p["alive"]]
            ok = True
            if pol == "una_posicion" and alive: ok = False
            if pol == "max3" and len(alive) >= 3: ok = False
            if pol == "cierre_en_opuesta":
                for p in alive:
                    if p["dir"] == -s: close(p, o[j], j, "OPPOSITE")
            if ok and a[j - 1] > 0:
                at = a[j - 1]
                pos.append(dict(dir=s, entry=o[j], atr=at, sl=o[j] - s * sl_atr * at, tp=o[j] + s * rr * sl_atr * at, bar=j, cost=sp[j] * LOT_USD, alive=True, hedged=False, pair=None))
        # salidas individuales
        for p in pos:
            if not p["alive"] or p["bar"] > j:
                continue
            ind = pol not in ("cesta_sin_SL",) and not p["hedged"]
            if ind:
                hit_sl = (l[j] <= p["sl"]) if p["dir"] > 0 else (h[j] >= p["sl"])
                hit_tp = (pol != "cesta_con_SL") and ((h[j] >= p["tp"]) if p["dir"] > 0 else (l[j] <= p["tp"]))
                if hit_sl: close(p, p["sl"], j, "SL"); continue
                if hit_tp: close(p, p["tp"], j, "TP"); continue
            if j - p["bar"] + 1 >= hold:
                close(p, c[j], j, "TIME")
        alive = [p for p in pos if p["alive"]]
        # cobertura del perdedor
        if pol == "cobertura_perdedora":
            for p in alive:
                if not p["hedged"] and p["bar"] <= j and p["dir"] * (c[j] - p["entry"]) / p["atr"] <= -0.7:
                    p["hedged"] = True
                    pos.append(dict(dir=-p["dir"], entry=c[j], atr=p["atr"], sl=0, tp=0, bar=p["bar"], cost=sp[j] * LOT_USD, alive=True, hedged=True, pair=id(p)))
            alive = [p for p in pos if p["alive"]]
        # cesta
        if pol in ("cesta_sin_SL", "cesta_con_SL") and alive:
            Rtot = sum(p["dir"] * (c[j] - p["entry"]) / p["atr"] for p in alive)
            if Rtot >= btp or Rtot <= bsl:
                for p in alive: close(p, c[j], j, "BASKET_TP" if Rtot >= btp else "BASKET_SL")
                alive = []
        # equidad
        flo = sum(p["dir"] * (c[j] - p["entry"]) * LOT_USD for p in alive if p["bar"] <= j)
        eq = CAP + eq_real + flo
        dd_peak = max(dd_peak, eq); max_dd = max(max_dd, (dd_peak - eq) / dd_peak); worst_float = min(worst_float, flo)
        conc.append(len(alive)); maxconc = max(maxconc, len(alive)); maxmargin = max(maxmargin, len(alive) * 0.01 * 100 * c[j] / LEV)
        if len(pos) > 4000: pos = [p for p in pos if p["alive"]]
    for p in [p for p in pos if p["alive"]]:
        close(p, c[last], last, "END")
    X = pd.DataFrame(closed)
    gp, gl = X.pnl[X.pnl > 0].sum(), -X.pnl[X.pnl < 0].sum()
    still_open_pct = 0.0
    return dict(policy=pol, n_closed=len(X), net_usd=round(float(X.pnl.sum()), 1), pf=round(float(gp / gl), 3) if gl > 0 else np.nan, expR=round(float(X.R.mean()), 4), win_pct=round(float((X.pnl > 0).mean() * 100), 1),
                max_equity_dd_pct_incl_floating=round(max_dd * 100, 2), worst_floating_usd=round(worst_float, 1), mean_concurrent=round(float(np.mean(conc)), 2), max_concurrent=maxconc, max_margin_usd=round(maxmargin, 1),
                max_margin_pct_eq=round(maxmargin / CAP * 100, 2), hedged_positions=int(X.hedged.sum()), cost_usd=round(float(X.pnl.sum() - (X.pnl + 0).sum()), 1))


def main():
    rows = []
    V.COOL = 6                                          # enfriamiento de la baseline H4 (v9_scalp_study lo fija en 10 al importarse)
    d4 = H.load_htf("XAUUSDm", "H4"); i4, r4 = C4.signals_n(d4, 20); assert 240 <= len(i4) <= 250, len(i4)
    sets = {"XAU_H4_BASELINE(2R)": (d4, list(zip(i4, r4)), 2.0, 40)}
    V.HZ = S.CFG["M5"]["HZ"]; V.MAXH = S.CFG["M5"]["MAXH"]
    d5 = S.load("XAUUSDm", "M5"); V.COOL = 10
    i5, r5 = S.families(d5, "M5")["G_SESSION_ORB"]; ok = i5 > 100; i5, r5, _ = V.dedupe(i5[ok], r5[ok], None)
    sets["XAU_M5_G_SESSION_ORB(1.5R,contraste)"] = (d5, list(zip(i5, r5)), 1.5, 12)
    i5b, r5b = S.families(d5, "M5")["B_BREAKOUT"]; ok = i5b > 100; i5b, r5b, _ = V.dedupe(i5b[ok], r5b[ok], None)
    sets["XAU_M5_B_BREAKOUT(1.5R,contraste)"] = (d5, list(zip(i5b, r5b)), 1.5, 12)
    for name, (d, sig, rr, hold) in sets.items():
        for pol in ("individual", "una_posicion", "max3", "cierre_en_opuesta", "cobertura_perdedora", "cesta_sin_SL", "cesta_con_SL"):
            r = simulate(d, sig, pol, rr=rr, hold=hold, btp=rr, bsl=-3.0)
            rows.append(dict(senales=name, n_signals=len(sig), rr=rr, hold_bars=hold, **r)); print(name, pol, r["net_usd"], r["pf"], r["max_equity_dd_pct_incl_floating"], flush=True)
    B = pd.DataFrame(rows)
    B["nota"] = "retrospectivo, mismo historico; cesta_sin_SL puede ocultar perdidas flotantes: ver max_equity_dd_pct_incl_floating y worst_floating_usd. Politicas no ajustadas por parametros (btp=RR, bsl=-3R prefijados)"
    B[~B.policy.isin(["cobertura_perdedora", "cierre_en_opuesta"])].to_csv(ROOT_RES / "V9_BASKET_TRADING.csv", index=False)
    B[B.policy.isin(["individual", "cobertura_perdedora", "cierre_en_opuesta", "una_posicion"])].to_csv(ROOT_RES / "V9_HEDGING_ANALYSIS.csv", index=False)


ROOT_RES = S.ROOT / "research"

if __name__ == "__main__":
    main()



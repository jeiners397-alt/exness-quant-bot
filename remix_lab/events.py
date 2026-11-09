"""Fase E — estudio de eventos de tres barreras (probabilidades de alcanzar +kR antes de -1R) con costes de spread incluidos en los precios.
Entrada: apertura de la barra siguiente a la senal (largo al ask = open+spread; corto al bid = open). SL = `sl_dist` (precio). Horizonte en barras.
Orden intrabarra DESCONOCIDO con barras: si SL y TP caen en la misma barra se informan DOS cotas: conservadora (pierde) y optimista (gana).
Las barras no permiten fijar el orden; los ticks reales (solo 2026) se usan aparte para verificar la cota. Salto (gap) por encima del SL: la perdida se registra al open.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PT = 1e-5
KS = (0.5, 1.0, 1.5, 2.0, 3.0)


def barrier_events(df: pd.DataFrame, d: np.ndarray, sl_dist: np.ndarray, horizon: int, ks=KS, min_gap: int = 0):
    """Devuelve DataFrame con una fila por evento: idx, dir, risk, y por cada k: R_cons_k, R_opt_k, amb_k (1 si ambiguo), bars_k (barras hasta el resultado)."""
    n = len(df)
    sig = np.flatnonzero((d != 0) & np.isfinite(sl_dist) & (sl_dist > 0))
    sig = sig[sig < n - 2]
    if min_gap and len(sig):
        keep, last = [], -10**9
        for i in sig:
            if i - last >= min_gap:
                keep.append(i); last = i
        sig = np.array(keep, int)
    if len(sig) == 0:
        return pd.DataFrame()
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    spr = df["spread"].to_numpy(float) * PT
    H = horizon
    ix = sig[:, None] + 1 + np.arange(H)[None, :]                       # barras de la operacion
    valid = ix < n
    ixc = np.minimum(ix, n - 1)
    dd = d[sig].astype(float)[:, None]
    risk = sl_dist[sig][:, None]
    j = sig + 1
    entry = np.where(d[sig] == 1, o[j] + spr[j], o[j])[:, None]
    # extremos en espacio "ganancia": long usa bid (low/high), short usa ask (= precio + spread)
    hi = np.where(dd == 1, h[ixc], -(l[ixc] + spr[ixc]))                # maxima ganancia posible dentro de la barra (precio * dir)
    lo = np.where(dd == 1, l[ixc], -(h[ixc] + spr[ixc]))                # peor excursion
    base = np.where(dd == 1, entry, -entry)
    best_R = (hi - base) / risk
    worst_R = (lo - base) / risk
    best_R = np.where(valid, best_R, -np.inf); worst_R = np.where(valid, worst_R, np.inf)
    sl_hit = worst_R <= -1.0
    first_sl = np.where(sl_hit.any(1), sl_hit.argmax(1), H + 1)
    # R al cierre del ultimo bar valido (timeout): salida a bid (largo) / ask (corto)
    last_valid = valid.sum(1) - 1
    li = ixc[np.arange(len(sig)), last_valid]
    exit_px = np.where(d[sig] == 1, c[li], c[li] + spr[li])
    r_timeout = (exit_px - entry[:, 0]) * d[sig] / risk[:, 0]
    # perdida al abrir con salto
    sl_bar_idx = ixc[np.arange(len(sig)), np.minimum(first_sl, H - 1)]
    open_exit = np.where(d[sig] == 1, o[sl_bar_idx], o[sl_bar_idx] + spr[sl_bar_idx])
    r_gap = (open_exit - entry[:, 0]) * d[sig] / risk[:, 0]
    loss_R = np.where(np.isfinite(r_gap), np.minimum(-1.0, r_gap), -1.0)
    out = {"idx": sig, "dir": d[sig], "risk": risk[:, 0], "cost_R": (spr[j] / risk[:, 0])}
    for k in ks:
        tp_hit = best_R >= k
        first_tp = np.where(tp_hit.any(1), tp_hit.argmax(1), H + 1)
        tp_first = first_tp < first_sl
        sl_first = first_sl < first_tp
        both = (first_tp == first_sl) & (first_tp <= H)
        cons = np.where(tp_first, k, np.where(sl_first | both, loss_R, r_timeout))
        opt = np.where(tp_first | both, k, np.where(sl_first, loss_R, r_timeout))
        out[f"Rc_{k}"] = cons; out[f"Ro_{k}"] = opt
        out[f"amb_{k}"] = both.astype(int)
        out[f"bars_{k}"] = np.where(tp_first | both, first_tp, np.where(sl_first, first_sl, H)) + 1
        out[f"win_{k}"] = tp_first.astype(int)
    out["mfe_R"] = np.where(np.isfinite(best_R), best_R, -np.inf).max(1)
    out["mae_R"] = -np.where(np.isfinite(worst_R), worst_R, np.inf).min(1)
    return pd.DataFrame(out)


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; hw = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - hw, c + hw)

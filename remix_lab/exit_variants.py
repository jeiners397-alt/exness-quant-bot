"""Repeticion de salidas sobre ENTRADAS FIJAS (las 335 oficiales de S01). Una modificacion por variante; entradas, SL inicial y TP inicial identicos.
Resolucion: barras M15 (bid; ask = bid + spread de barra). Convencion CONSERVADORA intrabarra:
  - SL se evalua antes que TP dentro de la misma barra;
  - cualquier cambio de gestion (BE, trailing, parcial) se decide con los extremos de una barra y entra en vigor desde la SIGUIENTE barra
    (nunca se asume que el stop movido ya existia dentro de la barra que lo activo);
  - gaps: salida al open si el open ya supera el stop.
Esto subestima algo a BE/trailing (la barra de activacion no puede stoppear) y NO sustituye a la repeticion con ticks.
Resultado en R sobre el riesgo inicial del trade (SL = rango x1). Costes: spread de barra (compra ask / venta bid); slippage en stops = parametro.
"""
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

PT = 1e-5


@dataclass
class Variant:
    vid: str
    desc: str
    be_trigger_R: float = 0.0          # >0 activa break-even
    be_buffer_px: float = 0.0          # SL de BE = entrada + dir*buffer
    trail_mode: str = ""               # "", "atr", "struct"
    trail_act_R: float = 1.0
    trail_atr_mult: float = 2.0
    struct_n: int = 4
    exit_hour: int = 17
    max_dur_h: float = 0.0
    nocont_bars: int = 0               # falta de continuacion: si tras N barras MFE < nocont_R -> salir
    nocont_R: float = 0.25
    partial_R: float = 0.0             # cierra 50% en +partial_R (solo si lotes >= 0.02)
    slip_pts: float = 0.0              # slippage adverso en salidas por stop (puntos)


def prep_bars(m15: pd.DataFrame) -> pd.DataFrame:
    m = m15.copy().reset_index(drop=True)
    tr = np.maximum(m.high - m.low, np.maximum((m.high - m.close.shift()).abs(), (m.low - m.close.shift()).abs()))
    m["atr"] = tr.rolling(14).mean().shift(1)     # conocido al open de la barra
    return m


def simulate(tr, bars: pd.DataFrame, idx_by_time: dict, v: Variant) -> dict:
    d, e, risk = int(tr.dir), float(tr.entry), float(tr.sl_dist)
    lots = float(tr.lots)
    sl = e - d * risk
    tp = e + d * 1.5 * risk
    o_time = tr.open_time
    i0 = idx_by_time[o_time.floor("15min")]
    mfe = 0.0
    parts = []          # (fraccion de volumen, movimiento de precio con signo)
    rem = 1.0
    partial_done = False
    be_done = False
    for i in range(i0, len(bars)):
        b = bars.iloc[i]
        t = b.time
        spr = b.spread * PT
        o, h, l, c = b.open, b.high, b.low, b.close
        first = i == i0
        # cierres por tiempo (a la apertura de la barra)
        if not first:
            tmo = (t.hour >= v.exit_hour) or (v.max_dur_h > 0 and (t - o_time).total_seconds() / 3600 >= v.max_dur_h)
            if v.nocont_bars and (i - i0) == v.nocont_bars and mfe < v.nocont_R * risk:
                tmo = True
            if tmo:
                px = o if d == 1 else o + spr
                parts.append((rem, d * (px - e))); rem = 0; reason = "TIME"; break
        # stops / objetivos con niveles vigentes (SL primero)
        slip = v.slip_pts * PT
        if d == 1:
            hit_sl = l <= sl
            hit_tp = h >= tp
            sl_px = min(sl, o) - slip
        else:
            hit_sl = (h + spr) >= sl
            hit_tp = (l + spr) <= tp
            sl_px = max(sl, o + spr) + slip
        if hit_sl:
            parts.append((rem, d * (sl_px - e))); rem = 0
            reason = "SL" if (sl == e - d * risk) else "SL_MOVED"; break
        if hit_tp:
            parts.append((rem, 1.5 * risk)); rem = 0; reason = "TP"; break
        # actualizar MFE y gestion (efecto desde la siguiente barra)
        fav = (h - e) if d == 1 else (e - (l + spr))
        mfe = max(mfe, fav)
        if v.partial_R and not partial_done and lots >= 0.02 and mfe >= v.partial_R * risk:
            parts.append((0.5 if lots * 0.5 >= 0.01 else 0.0, v.partial_R * risk)); rem -= parts[-1][0]; partial_done = True
        if v.be_trigger_R and not be_done and mfe >= v.be_trigger_R * risk:
            new = e + d * v.be_buffer_px
            sl = max(sl, new) if d == 1 else min(sl, new); be_done = True
        if v.trail_mode and mfe >= v.trail_act_R * risk:
            if v.trail_mode == "atr" and not np.isnan(b.atr):
                if d == 1:
                    cand = (h) - v.trail_atr_mult * b.atr; sl = max(sl, cand)
                else:
                    cand = (l + spr) + v.trail_atr_mult * b.atr; sl = min(sl, cand)
            elif v.trail_mode == "struct" and i - v.struct_n + 1 >= i0:
                w = bars.iloc[i - v.struct_n + 1:i + 1]
                if d == 1:
                    sl = max(sl, w.low.min())
                else:
                    sl = min(sl, (w.high + w.spread * PT).max())
    else:
        reason = "FIN_DATOS"; parts.append((rem, 0.0)); rem = 0
    if rem > 1e-9:
        parts.append((rem, 0.0))
    R = sum(f * mv for f, mv in parts) / risk
    return {"R": R, "reason": reason, "mfe_R_bar": mfe / risk, "partial": partial_done}


def run_variant(trades: pd.DataFrame, bars: pd.DataFrame, v: Variant) -> pd.DataFrame:
    idx = {t: i for i, t in enumerate(bars.time)}
    out = [simulate(tr, bars, idx, v) for tr in trades.itertuples()]
    o = pd.DataFrame(out)
    o["vid"] = v.vid
    o["open_time"] = trades.open_time.values
    o["dir"] = trades.dir.values
    return o


VARIANTS = [
    Variant("V0", "original (17h, SL=rango, TP=1.5R)"),
    Variant("V1a", "BE a +0.5R (SL=entrada)", be_trigger_R=0.5),
    Variant("V1b", "BE a +1.0R (SL=entrada)", be_trigger_R=1.0),
    Variant("V2a", "Trailing ATR14 x1.5, activa +1R", trail_mode="atr", trail_act_R=1.0, trail_atr_mult=1.5),
    Variant("V2b", "Trailing ATR14 x2.5, activa +1R", trail_mode="atr", trail_act_R=1.0, trail_atr_mult=2.5),
    Variant("V3", "Trailing estructural (min/max ultimas 4 barras confirmadas), activa +1R", trail_mode="struct", trail_act_R=1.0, struct_n=4),
    Variant("V4a", "Cierre de sesion 13h", exit_hour=13),
    Variant("V4b", "Cierre de sesion 15h", exit_hour=15),
    Variant("V4c", "Duracion maxima 4h", max_dur_h=4.0),
    Variant("V4d", "Sin continuacion: a las 6 barras (1.5h) si MFE<0.25R, salir", nocont_bars=6, nocont_R=0.25),
    Variant("V5", "Parcial 50% a +1R (solo lotes>=0.02), resto con SL/TP originales", partial_R=1.0),
]

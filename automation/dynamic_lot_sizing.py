"""Lotaje dinamico: limitado por (a) margen disponible del simbolo, (b) riesgo al SL (control independiente) y (c) especificaciones del
instrumento. El 0,01 es el minimo PREFERIDO, no un maximo: el sistema puede usar mas si el presupuesto y el riesgo lo permiten.
Nunca se redondea hacia arriba ni se supera ningun limite: si el minimo valido no cabe, se RECHAZA."""
from __future__ import annotations

import math
from dataclasses import dataclass

from automation.margin_allocator import MarginAllocator
from automation.sl_risk_calculator import evaluate
from automation.symbol_specifications import SymbolSpec, margin_for, loss_at_sl_for


@dataclass(frozen=True)
class LotDecision:
    symbol: str
    lots: float
    approved: bool
    reason: str
    margin: float
    margin_budget_remaining: float
    loss_at_sl: float
    risk_pct: float
    lots_by_margin: float
    lots_by_risk: float
    lots_by_volume_limit: float


def size(spec: SymbolSpec, alloc: MarginAllocator, entry: float, sl: float, is_buy: bool, risk_pct_max: float = 0.5,
         equity: float | None = None, mt5=None, open_volume: float = 0.0, tp: float | None = None) -> LotDecision:
    """Calcula el lote. risk_pct_max es el limite de perdida al SL (independiente del 5 % de margen)."""
    eq = equity if equity is not None else alloc.equity
    avail = alloc.available_for(spec.name)
    # margen y perdida por 1 lote (lineales en el volumen para los modos soportados; se re-verifica con el volumen final)
    m1 = margin_for(mt5, spec, 1.0, entry, is_buy)
    l1 = loss_at_sl_for(mt5, spec, 1.0, entry, sl, is_buy)
    lots_m = alloc_floor(spec, avail / m1) if m1 > 0 else 0.0
    lots_r = alloc_floor(spec, (eq * risk_pct_max / 100.0) / l1) if l1 > 0 else 0.0
    cap_vol = math.inf if spec.volume_limit <= 0 else max(0.0, spec.volume_limit - open_volume)
    lots_v = spec.normalize_down(cap_vol) if math.isfinite(cap_vol) else math.inf
    lots = min(lots_m, lots_r, lots_v, spec.volume_max)
    lots = spec.normalize_down(lots) if math.isfinite(lots) else 0.0
    lm = lots_m; lr = lots_r; lv = lots_v if math.isfinite(lots_v) else -1.0

    def reject(why: str, margin=0.0, loss=0.0):
        return LotDecision(spec.name, 0.0, False, why, margin, alloc.remaining(spec.name), loss, 0.0, lm, lr, lv)

    if lots < spec.volume_min - 1e-12:
        if lots_m < spec.volume_min:
            return reject(f"minimo valido {spec.volume_min} lotes excede el margen disponible ({avail:.2f})")
        if lots_r < spec.volume_min:
            return reject(f"minimo valido {spec.volume_min} lotes excede el riesgo permitido ({risk_pct_max}% de {eq:.0f})")
        return reject("limite de volumen del simbolo")
    margin = margin_for(mt5, spec, lots, entry, is_buy)
    dec = alloc.check(spec.name, margin)
    if not dec.approved:                       # re-verificacion con el volumen final (no lineal / redondeos del broker)
        return reject(dec.reason, margin)
    rep = evaluate(spec, lots, entry, sl, tp, eq, is_buy, mt5)
    if rep.risk_pct_equity > risk_pct_max + 1e-9:
        return reject(f"riesgo {rep.risk_pct_equity:.3f}% > {risk_pct_max}%", margin, rep.loss_at_sl)
    return LotDecision(spec.name, lots, True, "OK", margin, dec.symbol_remaining - margin, rep.loss_at_sl, rep.risk_pct_equity, lm, lr, lv)


def alloc_floor(spec: SymbolSpec, lots: float) -> float:
    """Piso al paso de volumen SIN aplicar el minimo (un resultado < min se interpreta como 'no cabe')."""
    if lots <= 0 or not math.isfinite(lots):
        return 0.0
    return round(math.floor(lots / spec.volume_step + 1e-9) * spec.volume_step, 8)

"""Riesgo al Stop Loss (perdida monetaria), INDEPENDIENTE del margen.

Usa OrderCalcProfit/order_calc_profit del broker cuando hay conexion; si no, el modelo tick_value. Registra tambien un recargo
estimado por gap/deslizamiento (no sustituye a la medicion real)."""
from __future__ import annotations

from dataclasses import dataclass

from automation.symbol_specifications import SymbolSpec, loss_at_sl_for


@dataclass(frozen=True)
class RiskReport:
    loss_at_sl: float            # moneda de cuenta, positiva
    risk_pct_equity: float
    potential_profit: float
    reward_risk: float
    slippage_extra: float        # recargo estimado por deslizamiento/gap (modelo)
    loss_with_slippage: float


def sl_from_structure(is_buy: bool, entry: float, swing_extreme: float, buffer: float) -> float:
    """SL estructural: detras del extremo relevante (+buffer). Devuelve el precio de SL."""
    return swing_extreme - buffer if is_buy else swing_extreme + buffer


def sl_from_atr(is_buy: bool, entry: float, atr: float, mult: float) -> float:
    return entry - mult * atr if is_buy else entry + mult * atr


def sl_by_regime(is_buy: bool, entry: float, atr: float, atr_percentile: float, base_mult: float = 1.5) -> float:
    """SL adaptado al regimen: en volatilidad alta (percentil>0.8) se amplia el multiplicador, en baja (<0.2) se reduce; nunca se acerca a < 1 ATR."""
    mult = base_mult * (1.25 if atr_percentile > 0.8 else 0.85 if atr_percentile < 0.2 else 1.0)
    return sl_from_atr(is_buy, entry, atr, max(1.0, mult))


def evaluate(spec: SymbolSpec, lots: float, entry: float, sl: float, tp: float | None, equity: float, is_buy: bool,
             mt5=None, slippage_points: float = 0.0) -> RiskReport:
    if sl is None or sl <= 0:
        raise ValueError("SL obligatorio antes de aprobar una entrada")
    if (is_buy and sl >= entry) or ((not is_buy) and sl <= entry):
        raise ValueError("SL del lado equivocado")
    loss = loss_at_sl_for(mt5, spec, lots, entry, sl, is_buy)
    prof = loss_at_sl_for(mt5, spec, lots, entry, tp, is_buy) if tp else 0.0
    extra = (slippage_points * spec.point / spec.tick_size) * spec.tick_value * lots if slippage_points else 0.0
    return RiskReport(loss, 100.0 * loss / equity, prof, (prof / loss) if loss > 0 and prof else 0.0, extra, loss + extra)

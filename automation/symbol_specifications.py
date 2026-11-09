"""Especificaciones reales de instrumentos (SYMBOL_VOLUME_*, contrato, tick, modo de calculo).

Solo lectura: usa mt5.symbol_info() / mt5.order_calc_margin() / mt5.order_calc_profit(). NUNCA mt5.order_send().
Para pruebas sinteticas existen `SymbolSpec.synthetic(...)` y modelos de margen/beneficio aproximados (marcados como MODELO,
no sustituyen a OrderCalcMargin en el broker)."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

PREFERRED_MIN_LOT = 0.01          # minimo PREFERIDO. No es un minimo obligatorio ni un maximo.

# SYMBOL_CALC_MODE_*
CALC_FOREX, CALC_FUTURES, CALC_CFD, CALC_CFDINDEX, CALC_CFDLEVERAGE = 0, 1, 2, 3, 4

PRIORITY_BASES = {
    "forex": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
    "metals": ["XAUUSD", "XAGUSD"],
    "crypto": ["BTCUSD", "ETHUSD"],
    "indices": ["US30", "US500", "USTEC", "NAS100", "SPX500", "DJ30", "USA500", "USA30", "USATEC"],
}


@dataclass(frozen=True)
class SymbolSpec:
    name: str
    volume_min: float
    volume_max: float
    volume_step: float
    volume_limit: float            # 0 = sin limite agregado
    contract_size: float
    tick_size: float
    tick_value: float              # en moneda de la cuenta
    calc_mode: int
    digits: int
    point: float
    currency_profit: str = "USD"
    currency_base: str = ""
    spread_points: float = 0.0
    leverage: float = 200.0        # solo para el modelo sintetico

    # ---------- construccion ----------
    @classmethod
    def from_mt5(cls, mt5, name: str, leverage: float = 200.0) -> "SymbolSpec":
        mt5.symbol_select(name, True)
        i = mt5.symbol_info(name)
        if i is None:
            raise ValueError(f"symbol_info({name}) devolvio None: {mt5.last_error()}")
        return cls(name=name, volume_min=i.volume_min, volume_max=i.volume_max, volume_step=i.volume_step,
                   volume_limit=getattr(i, "volume_limit", 0.0), contract_size=i.trade_contract_size,
                   tick_size=i.trade_tick_size, tick_value=i.trade_tick_value, calc_mode=i.trade_calc_mode,
                   digits=i.digits, point=i.point, currency_profit=i.currency_profit, currency_base=i.currency_base,
                   spread_points=float(i.spread), leverage=leverage)

    @classmethod
    def synthetic(cls, name: str, **kw) -> "SymbolSpec":
        d = dict(currency_base="EUR", volume_min=0.01, volume_max=100.0, volume_step=0.01, volume_limit=0.0, contract_size=100000.0, tick_size=0.00001,
                 tick_value=1.0, calc_mode=CALC_FOREX, digits=5, point=0.00001)
        d.update(kw)
        return cls(name=name, **d)

    def as_dict(self) -> dict:
        return asdict(self)

    # ---------- volumen ----------
    @property
    def effective_min_lot(self) -> float:
        """Minimo operativo real: respeta el broker; 0,01 es solo el minimo PREFERIDO cuando el broker lo permite."""
        return self.volume_min

    def normalize_down(self, lots: float) -> float:
        """Redondea HACIA ABAJO al paso de volumen (nunca hacia arriba: eso podria superar los limites)."""
        if lots <= 0:
            return 0.0
        steps = math.floor(lots / self.volume_step + 1e-9)
        v = round(steps * self.volume_step, 8)
        return min(v, self.volume_max)

    def is_valid_volume(self, lots: float) -> bool:
        if lots < self.volume_min - 1e-12 or lots > self.volume_max + 1e-12:
            return False
        k = (lots - self.volume_min) / self.volume_step
        return abs(k - round(k)) < 1e-6

    # ---------- modelos (sinteticos) ----------
    def model_margin(self, lots: float, price: float, fx_to_account: float = 1.0) -> float:
        """MODELO de margen en moneda de la cuenta (fx_to_account convierte la moneda de margen a la cuenta).
        FOREX: lots*contract/leverage (moneda base); CFD/indices/cripto: lots*contract*price/leverage. En produccion usar OrderCalcMargin."""
        if self.calc_mode == CALC_FOREX:
            base_px = 1.0 if self.currency_base in ("USD", "") else price      # margen en moneda base -> USD (cotizadas en USD)
            return lots * self.contract_size / self.leverage * base_px * fx_to_account
        return lots * self.contract_size * price / self.leverage * fx_to_account

    def model_loss_at_sl(self, lots: float, sl_distance_price: float) -> float:
        """Perdida en moneda de la cuenta al SL: ticks recorridos * tick_value * lotes (formula oficial de MT5 para tick_value)."""
        return (sl_distance_price / self.tick_size) * self.tick_value * lots


def margin_for(mt5, spec: SymbolSpec, lots: float, price: float, is_buy: bool = True) -> float:
    """Margen de una orden nueva: OrderCalcMargin del broker (si mt5 dado) o el modelo."""
    if mt5 is not None:
        m = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL, spec.name, lots, price)
        if m is None:
            raise RuntimeError(f"order_calc_margin fallo: {mt5.last_error()}")
        if float(m) > 0:
            return float(m)
        # Cuenta con apalancamiento ilimitado (demo Exness: 2e9) => el broker devuelve 0. Se usa el modelo con spec.leverage (apalancamiento del probador).
    return spec.model_margin(lots, price)
    return spec.model_margin(lots, price)


def loss_at_sl_for(mt5, spec: SymbolSpec, lots: float, entry: float, sl: float, is_buy: bool = True) -> float:
    """Perdida monetaria (positiva) al SL: order_calc_profit del broker o el modelo."""
    if mt5 is not None:
        p = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL, spec.name, lots, entry, sl)
        if p is None:
            raise RuntimeError(f"order_calc_profit fallo: {mt5.last_error()}")
        return abs(float(p))
    return spec.model_loss_at_sl(lots, abs(entry - sl))


def classify(name: str) -> str:
    n = name.upper()
    for cls_, bases in PRIORITY_BASES.items():
        for b in bases:
            if n.startswith(b):
                return cls_
    return "other"


def discover(mt5) -> list[dict]:
    """Descubre instrumentos del terminal con los nombres EXACTOS de MT5 (sin inventar sufijos) y marca los prioritarios."""
    out = []
    for s in mt5.symbols_get() or []:
        c = classify(s.name)
        if c != "other":
            out.append({"name": s.name, "class": c, "visible": bool(s.visible), "volume_min": s.volume_min, "volume_step": s.volume_step,
                        "volume_max": s.volume_max, "contract_size": s.trade_contract_size, "calc_mode": s.trade_calc_mode})
    return sorted(out, key=lambda r: (r["class"], r["name"]))

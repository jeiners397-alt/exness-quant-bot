"""Gestor de posiciones simulado: une controlador + tamanio + riesgo. Util para analizar trades de un backtest bajo las reglas de margen.
SOLO SIMULACION: ningun metodo envia ordenes al broker."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from automation.margin_allocator import MarginAllocator
from automation.multi_position_controller import MultiPositionController
from automation.symbol_specifications import SymbolSpec


@dataclass
class PositionManager:
    spec: SymbolSpec
    equity: float = 3000.0
    margin_pct: float = 5.0
    risk_pct: float = 0.5
    mode: str = "HEDGING"
    log: list = field(default_factory=list)

    def __post_init__(self):
        self.alloc = MarginAllocator(equity=self.equity, allocation_percent=self.margin_pct)
        self.ctl = MultiPositionController(self.alloc, self.mode)

    def replay(self, signals: pd.DataFrame) -> pd.DataFrame:
        """signals: columnas time_open,time_close,is_buy,entry,sl,tp. Reproduce apertura/cierre cronologicos y registra aprobaciones."""
        ev = []
        for i, r in signals.iterrows():
            ev.append((r.time_open, 1, i)); ev.append((r.time_close, 0, i))
        ev.sort()
        open_t = {}
        for t, kind, i in ev:
            r = signals.loc[i]
            if kind == 1:
                dec, tk = self.ctl.request_entry(self.spec, bool(r.is_buy), r.entry, r.sl, r.get("tp"), self.risk_pct)
                if tk:
                    open_t[i] = tk
                self.log.append(dict(time=t, idx=i, approved=dec.approved, reason=dec.reason, lots=dec.lots, margin=dec.margin,
                                     loss_at_sl=dec.loss_at_sl, risk_pct=dec.risk_pct, symbol_margin_used=self.alloc.used(self.spec.name),
                                     n_open=len(self.ctl.positions)))
            elif i in open_t:
                self.ctl.close(open_t.pop(i))
        return pd.DataFrame(self.log)

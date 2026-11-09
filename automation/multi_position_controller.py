"""Controlador de posiciones simultaneas (hedging / netting) con margen agregado y riesgo independiente. SIMULACION: no envia ordenes."""
from __future__ import annotations

from dataclasses import dataclass, field

from automation.dynamic_lot_sizing import LotDecision, size
from automation.margin_allocator import MarginAllocator
from automation.symbol_specifications import SymbolSpec


@dataclass
class Position:
    ticket: int
    symbol: str
    is_buy: bool
    lots: float
    entry: float
    sl: float
    tp: float | None
    margin: float
    risk_money: float
    magic: int = 0
    strategy: str = ""


@dataclass
class MultiPositionController:
    alloc: MarginAllocator
    mode: str = "HEDGING"                 # HEDGING | NETTING
    max_total_risk_pct: float = 3.0       # riesgo agregado al SL (control independiente)
    positions: dict = field(default_factory=dict)
    pending: dict = field(default_factory=dict)
    _t: int = 1000

    # ---- consultas ----
    def open_volume(self, symbol: str) -> float:
        return sum(p.lots for p in self.positions.values() if p.symbol == symbol)

    def total_risk_money(self) -> float:
        return sum(p.risk_money for p in self.positions.values())

    def symbol_margin(self, symbol: str) -> float:
        return self.alloc.used(symbol)

    # ---- apertura simulada ----
    def request_entry(self, spec: SymbolSpec, is_buy: bool, entry: float, sl: float, tp: float | None, risk_pct: float,
                      magic: int = 0, strategy: str = "", mt5=None, as_pending: bool = False) -> tuple[LotDecision, int | None]:
        if self.mode == "NETTING" and any(p.symbol == spec.name and p.is_buy != is_buy for p in self.positions.values()):
            return _reject(spec, "netting: la orden contraria reduciria/cerraria la posicion neta; no se simula como posicion independiente"), None
        dec = size(spec, self.alloc, entry, sl, is_buy, risk_pct, mt5=mt5, open_volume=self.open_volume(spec.name), tp=tp)
        if not dec.approved:
            return dec, None
        if self.total_risk_money() + dec.loss_at_sl > self.alloc.equity * self.max_total_risk_pct / 100.0 + 1e-9:
            return _reject(spec, f"riesgo agregado al SL superaria {self.max_total_risk_pct}% de la equidad", dec.margin, dec.loss_at_sl), None
        d, rid = self.alloc.reserve(spec.name, dec.margin)
        if rid is None:
            return _reject(spec, d.reason, dec.margin), None
        self._t += 1
        t = self._t
        if as_pending:
            self.alloc.commit(rid, "PENDING", f"P{t}")
            self.pending[t] = Position(t, spec.name, is_buy, dec.lots, entry, sl, tp, dec.margin, dec.loss_at_sl, magic, strategy)
            return dec, t
        self.alloc.commit(rid, "POSITION", f"T{t}")
        if self.mode == "NETTING":
            same = next((p for p in self.positions.values() if p.symbol == spec.name), None)
            if same:                                         # la posicion neta se promedia; un solo SL real
                tot = same.lots + dec.lots
                same.entry = (same.entry * same.lots + entry * dec.lots) / tot
                same.lots, same.margin, same.risk_money = tot, same.margin + dec.margin, same.risk_money + dec.loss_at_sl
                same.sl = sl
                self.alloc.release(f"T{t}"); self.alloc.add("POSITION", spec.name, dec.margin, f"T{same.ticket}x{t}")
                return dec, same.ticket
        self.positions[t] = Position(t, spec.name, is_buy, dec.lots, entry, sl, tp, dec.margin, dec.loss_at_sl, magic, strategy)
        return dec, t

    def fill_pending(self, ticket: int) -> None:
        p = self.pending.pop(ticket)
        self.positions[ticket] = p
        self.alloc.release(f"P{ticket}"); self.alloc.add("POSITION", p.symbol, p.margin, f"T{ticket}")

    def cancel_pending(self, ticket: int) -> None:
        self.pending.pop(ticket, None); self.alloc.release(f"P{ticket}")

    def close(self, ticket: int) -> None:
        p = self.positions.pop(ticket)
        self.alloc.items = [c for c in self.alloc.items if not (c.symbol == p.symbol and c.ref.startswith(f"T{ticket}"))]

    def reconcile(self, broker_positions: list[dict]) -> list[str]:
        """Compara el registro virtual con las posiciones reales del broker (ticket, symbol, volume). Devuelve diferencias."""
        diffs = []
        mine = {p.ticket: p for p in self.positions.values()}
        theirs = {b["ticket"]: b for b in broker_positions}
        for t in mine.keys() - theirs.keys():
            diffs.append(f"ticket {t} solo en registro virtual")
        for t in theirs.keys() - mine.keys():
            diffs.append(f"ticket {t} solo en broker")
        for t in mine.keys() & theirs.keys():
            if abs(mine[t].lots - theirs[t]["volume"]) > 1e-9:
                diffs.append(f"ticket {t}: volumen {mine[t].lots} vs broker {theirs[t]['volume']}")
        return diffs


def _reject(spec, why, margin=0.0, loss=0.0) -> LotDecision:
    return LotDecision(spec.name, 0.0, False, why, margin, 0.0, loss, 0.0, 0.0, 0.0, 0.0)

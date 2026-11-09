"""Asignacion de MARGEN por simbolo (5 % de la equidad por defecto). El 5 % es margen comprometido, NO riesgo de perdida.

Controlador centralizado con reservas para que dos solicitudes concurrentes no reserven dos veces el mismo margen.
No hay descuento por cobertura (hedge): el margen de cada posicion/orden pendiente cuenta completo."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Commitment:
    kind: str            # POSITION | PENDING | RESERVATION
    symbol: str
    margin: float
    ref: str = ""        # ticket / id de reserva


@dataclass
class Decision:
    approved: bool
    reason: str
    symbol_budget: float
    symbol_used: float
    symbol_remaining: float
    global_used: float
    global_limit: float


@dataclass
class MarginAllocator:
    equity: float = 3000.0
    allocation_percent: float = 5.0          # por simbolo
    global_percent: float = 15.0             # limite global configurable (correlacionados)
    scope: str = "PER_SYMBOL"
    reference: str = "ACCOUNT_EQUITY"
    strict: bool = True
    check_open_positions: bool = True
    check_pending_orders: bool = True
    items: list = field(default_factory=list)
    _seq: int = 0

    # ---- presupuesto ----
    def budget(self, symbol: str | None = None) -> float:
        return self.equity * self.allocation_percent / 100.0

    @property
    def global_limit(self) -> float:
        return self.equity * self.global_percent / 100.0

    def used(self, symbol: str) -> float:
        tot = 0.0
        for c in self.items:
            if c.symbol != symbol:
                continue
            if c.kind == "POSITION" and not self.check_open_positions:
                continue
            if c.kind == "PENDING" and not self.check_pending_orders:
                continue
            tot += c.margin
        return tot

    def global_used(self) -> float:
        return sum(c.margin for c in self.items)

    def remaining(self, symbol: str) -> float:
        return max(0.0, self.budget(symbol) - self.used(symbol))

    def remaining_global(self) -> float:
        return max(0.0, self.global_limit - self.global_used())

    def available_for(self, symbol: str) -> float:
        """Margen que aun puede comprometerse en `symbol` (minimo entre presupuesto del simbolo y limite global)."""
        return min(self.remaining(symbol), self.remaining_global())

    # ---- decisiones ----
    def check(self, symbol: str, new_margin: float) -> Decision:
        b, u, g = self.budget(symbol), self.used(symbol), self.global_used()
        ok, why = True, "OK"
        if new_margin < 0:
            ok, why = False, "margen negativo"
        elif u + new_margin > b + 1e-9:
            ok, why = False, f"supera el presupuesto del simbolo ({u + new_margin:.2f} > {b:.2f})"
        elif g + new_margin > self.global_limit + 1e-9:
            ok, why = False, f"supera el limite global ({g + new_margin:.2f} > {self.global_limit:.2f})"
        return Decision(ok, why, b, u, max(0.0, b - u), g, self.global_limit)

    def reserve(self, symbol: str, margin: float) -> tuple[Decision, str | None]:
        d = self.check(symbol, margin)
        if not d.approved:
            return d, None
        self._seq += 1
        rid = f"RSV{self._seq}"
        self.items.append(Commitment("RESERVATION", symbol, margin, rid))
        return d, rid

    def commit(self, rid: str, kind: str = "POSITION", ref: str | None = None) -> None:
        for c in self.items:
            if c.ref == rid and c.kind == "RESERVATION":
                c.kind, c.ref = kind, ref or rid
                return
        raise KeyError(rid)

    def release(self, ref: str) -> None:
        self.items = [c for c in self.items if c.ref != ref]

    def add(self, kind: str, symbol: str, margin: float, ref: str) -> None:
        self.items.append(Commitment(kind, symbol, margin, ref))

    def set_equity(self, equity: float) -> None:
        self.equity = equity

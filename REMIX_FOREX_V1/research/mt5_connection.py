"""REMIX FOREX V1: auditoría local y de solo lectura de una sesión MT5.

No contiene llamadas para colocar, editar ni cerrar órdenes. Ejecutar en Windows
con el terminal MetaTrader 5 instalado y una cuenta demo ya iniciada.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PAIRS = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD")


def read_account_mode(mt5: Any, account: Any) -> str:
    """Usar trade_mode del bróker, no deducir demo por el texto del servidor."""
    mode = getattr(account, "trade_mode", None)
    demo = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
    real = getattr(mt5, "ACCOUNT_TRADE_MODE_REAL", None)
    contest = getattr(mt5, "ACCOUNT_TRADE_MODE_CONTEST", None)
    if mode == demo and demo is not None:
        return "DEMO"
    if mode == real and real is not None:
        return "REAL"
    if mode == contest and contest is not None:
        return "CONTEST"
    return "DESCONOCIDO"


def choose_symbols(symbols: list[Any], roots: tuple[str, ...] = PAIRS) -> dict[str, list[str]]:
    """Sólo devuelve coincidencias, sin asumir el sufijo de un tipo de cuenta."""
    names = sorted({str(s.name) for s in symbols if getattr(s, "name", None)})
    result: dict[str, list[str]] = {}
    for root in roots:
        exact = [n for n in names if n == root]
        suffix = [n for n in names if n.startswith(root) and n != root]
        result[root] = exact + suffix[:12]
    return result


def symbol_snapshot(mt5: Any, name: str, currency: str) -> dict[str, Any]:
    item = mt5.symbol_info(name)
    if item is None:
        return {"symbol": name, "error": "Símbolo no disponible"}
    tick = mt5.symbol_info_tick(name)
    bid = getattr(tick, "bid", None) if tick else None
    ask = getattr(tick, "ask", None) if tick else None
    point = getattr(item, "point", 0)
    # El spread del último tick es orientativo; puede ser antiguo o faltar en fin de semana.
    spread_points = round((ask - bid) / point, 3) if (bid and ask and point and ask >= bid) else None
    vol_min = getattr(item, "volume_min", None)
    margin_buy = None
    if vol_min and ask and hasattr(mt5, "order_calc_margin"):
        margin_buy = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, name, vol_min, ask)
    return {
        "symbol": name,
        "visible_in_marketwatch": bool(getattr(item, "visible", False)),
        "bid": bid, "ask": ask, "tick_time_utc": datetime.fromtimestamp(tick.time, timezone.utc).isoformat() if tick and tick.time else None,
        "spread_points_live": spread_points,
        "spread_points_broker": getattr(item, "spread", None),
        "point": point,
        "digits": getattr(item, "digits", None),
        "volume_min": vol_min,
        "volume_max": getattr(item, "volume_max", None),
        "volume_step": getattr(item, "volume_step", None),
        "trade_contract_size": getattr(item, "trade_contract_size", None),
        "trade_tick_size": getattr(item, "trade_tick_size", None),
        "trade_tick_value": getattr(item, "trade_tick_value", None),
        "trade_tick_value_profit": getattr(item, "trade_tick_value_profit", None),
        "trade_tick_value_loss": getattr(item, "trade_tick_value_loss", None),
        "margin_initial_contract": getattr(item, "margin_initial", None),
        "estimated_margin_min_buy": margin_buy,
        "estimated_margin_currency": currency,
        "margin_note": "La estimación no incorpora posiciones u órdenes existentes; puede ser nula si el mercado está cerrado.",
    }


def audit(mt5: Any, terminal: str | None = None) -> dict[str, Any]:
    init_ok = mt5.initialize(path=terminal) if terminal else mt5.initialize()
    if not init_ok:
        raise RuntimeError(f"No se pudo conectar al terminal MT5: {mt5.last_error()}")
    try:
        terminal_info = mt5.terminal_info()
        account = mt5.account_info()
        if terminal_info is None or account is None:
            raise RuntimeError(f"Terminal o cuenta sin información: {mt5.last_error()}")
        symbols = mt5.symbols_get()
        if symbols is None:
            raise RuntimeError(f"No se pudo consultar el catálogo de símbolos: {mt5.last_error()}")
        candidates = choose_symbols(list(symbols))
        # Una coincidencia por raíz permite empezar; se muestran alternativas para verificar sufijos.
        selected = [variants[0] for variants in candidates.values() if variants]
        mode = read_account_mode(mt5, account)
        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "read_only": True, "orders_submitted": 0,
            "terminal": {
                "connected": bool(getattr(terminal_info, "connected", False)),
                "trade_allowed_terminal": bool(getattr(terminal_info, "trade_allowed", False)),
                "build": getattr(terminal_info, "build", None),
            },
            "account": {
                # No guardar account.login: un ID privado no es necesario para el diagnóstico.
                "trade_mode": mode,
                "server": getattr(account, "server", None),
                "company": getattr(account, "company", None),
                "currency": getattr(account, "currency", None),
                "balance": getattr(account, "balance", None),
                "equity": getattr(account, "equity", None),
                "margin": getattr(account, "margin", None),
                "margin_free": getattr(account, "margin_free", None),
                "margin_level": getattr(account, "margin_level", None),
                "leverage": getattr(account, "leverage", None),
                "margin_mode": getattr(account, "margin_mode", None),
            },
            "symbols_total": len(symbols),
            "symbols_candidates": candidates,
            "symbols_sample": [symbol_snapshot(mt5, x, str(getattr(account, "currency", ""))) for x in selected],
            "warnings": ([] if mode == "DEMO" else ["No se ha verificado una cuenta DEMO: no continuar a ejecución automatizada."]),
        }
    finally:
        mt5.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 0 MT5 — inspección de solo lectura")
    parser.add_argument("--terminal", default=None, help="Ruta completa del terminal64.exe si hay más de un MT5")
    parser.add_argument("--output", default="reports/diagnostico_mt5.json", help="Ruta local del reporte")
    args = parser.parse_args()
    try:
        import MetaTrader5 as mt5  # paquete oficial, disponible principalmente en Windows
    except ImportError:
        print("ERROR: Falta MetaTrader5. En Windows: py -m pip install -r requirements.txt", file=sys.stderr)
        return 2
    try:
        result = audit(mt5, args.terminal)
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"[OK] Reporte (sin número de cuenta ni contraseñas): {path.resolve()}")
        print(json.dumps({"terminal": result["terminal"], "account": result["account"],
                          "symbols_candidates": result["symbols_candidates"], "warnings": result["warnings"]},
                         indent=2, ensure_ascii=False))
        return 0 if result["account"]["trade_mode"] == "DEMO" else 3
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

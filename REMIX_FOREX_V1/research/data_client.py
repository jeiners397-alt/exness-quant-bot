"""Extracción reproducible de velas MT5, sin órdenes y con fechas UTC."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

FIELDS = ("time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume")
TIMEFRAME_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60}


def normalize_bars(rows: Any, end_utc: datetime, period_minutes: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Descarta la vela en curso; verifica orden, OHLC, unicidad y huecos."""
    if end_utc.utcoffset() != timedelta(0):
        raise ValueError("end_utc debe estar en UTC")
    cutoff_ts = int(end_utc.timestamp()) // (period_minutes * 60) * (period_minutes * 60)
    items = []
    for row in rows:
        source = dict(zip(FIELDS, row)) if not hasattr(row, "dtype") else {k: row[k].item() for k in FIELDS}
        row_time = int(source["time"])
        if row_time >= cutoff_ts:
            continue
        if row_time % (period_minutes * 60):
            raise ValueError(f"Vela fuera de alineación temporal: {row_time}")
        if source["high"] < max(source["open"], source["close"], source["low"]) or source["low"] > min(source["open"], source["close"], source["high"]):
            raise ValueError(f"OHLC inconsistente: {row_time}")
        if min(source["open"], source["high"], source["low"], source["close"]) <= 0:
            raise ValueError(f"Precio no positivo: {row_time}")
        items.append({"time_utc": datetime.fromtimestamp(row_time, timezone.utc).isoformat(), **{k: source[k] for k in FIELDS if k != "time"}})
    timestamps = [int(datetime.fromisoformat(row["time_utc"]).timestamp()) for row in items]
    if timestamps != sorted(set(timestamps)):
        raise ValueError("Velas duplicadas o desordenadas; datos rechazados")
    intervals = [b - a for a, b in zip(timestamps, timestamps[1:])]
    gaps = [d for d in intervals if d > period_minutes * 60]
    quality = {
        "bars": len(items), "first_utc": items[0]["time_utc"] if items else None,
        "last_utc": items[-1]["time_utc"] if items else None,
        "gap_intervals": len(gaps),
        "max_gap_minutes": max(gaps) / 60 if gaps else 0,
        "note": "Huecos pueden ser fines de semana, festivos o pérdida de históricos; requieren inspección.",
    }
    return items, quality


def extract(mt5: Any, symbol: str, tf_label: str, days: int, terminal: str | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not symbol or days <= 0 or days > 1095 or tf_label not in TIMEFRAME_MINUTES:
        raise ValueError("Parámetros inválidos; días entre 1 y 1095")
    ok = mt5.initialize(path=terminal) if terminal else mt5.initialize()
    if not ok:
        raise RuntimeError(f"No se pudo abrir MT5: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None:
            raise RuntimeError(f"No se pudo comprobar la cuenta: {mt5.last_error()}")
        if getattr(account, "trade_mode", None) != mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise RuntimeError("Fase 0 restringida a una cuenta DEMO")
        if mt5.symbol_info(symbol) is None:
            raise RuntimeError(f"El símbolo {symbol} no está disponible; revisar sufijo en diagnóstico")
        tf_enum = getattr(mt5, f"TIMEFRAME_{tf_label}")
        stop = datetime.now(timezone.utc)
        start = stop - timedelta(days=days)
        rates = mt5.copy_rates_range(symbol, tf_enum, start, stop)
        if rates is None:
            raise RuntimeError(f"copy_rates_range falló: {mt5.last_error()}")
        items, quality = normalize_bars(rates, stop, TIMEFRAME_MINUTES[tf_label])
        return items, {
            "symbol": symbol, "timeframe": tf_label, "days_requested": days,
            "requested_from_utc": start.isoformat(), "requested_to_utc": stop.isoformat(),
            "source": "MetaTrader 5 conectado al bróker", "orders_submitted": 0,
            "quality": quality,
            "warning": "Histórico sujeto a disponibilidad del bróker y Máx. barras en gráfico. Spread de barra no equivale a ejecución tick a tick.",
        }
    finally:
        mt5.shutdown()


def save_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["time_utc"] + list(FIELDS[1:]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="FASE 0 — descarga de OHLCV desde MetaTrader 5 (solo lectura)")
    parser.add_argument("--terminal", help="Ruta a terminal64.exe", default=None)
    parser.add_argument("--symbol", default="EURUSDm")
    parser.add_argument("--timeframe", choices=sorted(TIMEFRAME_MINUTES), default="M5")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--output", default="reports/EURUSDm_M5.csv")
    args = parser.parse_args()
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("ERROR: Instala MetaTrader5 en Windows con requirements.txt", file=sys.stderr)
        return 2
    try:
        rows, metadata = extract(mt5, args.symbol, args.timeframe, args.days, args.terminal)
        if not rows:
            raise RuntimeError("MT5 devolvió cero barras cerradas; revisar rango, símbolo o Max. barras")
        dst = Path(args.output)
        save_csv(rows, dst)
        sidecar = dst.with_suffix(".metadata.json")
        sidecar.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"csv": str(dst.resolve()), "metadata": str(sidecar.resolve()),
                          "quality": metadata["quality"]}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

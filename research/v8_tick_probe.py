"""V8 Fase 9 - disponibilidad de ticks reales del bróker (SOLO LECTURA de historial; sin ordenes). Muestras de 1 hora, una por mes, en XAUUSDm.
Verifica: n ticks, bid/ask validos, duplicados, saltos de tiempo > 60 s, cambios de spread. Cache local: data/raw/v8_ticks/ (no se sube a Drive/GitHub)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "raw" / "v8_ticks"
CACHE.mkdir(parents=True, exist_ok=True)


def main():
    if not mt5.initialize(path=r"C:\REMIX_MT5_LAB\terminal\terminal64.exe", portable=True):
        print("ERROR_DATOS: no inicializa la instancia aislada", mt5.last_error()); return
    sym = "XAUUSDm"; mt5.symbol_select(sym, True)
    rows = []
    for y in (2024, 2025, 2026):
        for m in range(1, 13):
            if (y, m) > (2026, 10):
                break
            f = CACHE / f"{sym}_{y}{m:02d}_w3_1400.csv"
            if f.exists():
                T = pd.read_csv(f, parse_dates=["time"]); src = "cache"
            else:
                day = [d for d in range(15, 29) if datetime(y, m, d).weekday() == 2][0]          # un miercoles de mitad/finales de mes
                a, b = datetime(y, m, day, 14, 0, tzinfo=timezone.utc), datetime(y, m, day, 15, 0, tzinfo=timezone.utc)
                t = mt5.copy_ticks_range(sym, a, b, mt5.COPY_TICKS_ALL)
                if t is None or len(t) == 0:
                    rows.append(dict(symbol=sym, month=f"{y}-{m:02d}", sample_hour_utc=str(a), n_ticks=0, estado="ERROR_DATOS(sin ticks)", mt5_last_error=str(mt5.last_error()))); continue
                T = pd.DataFrame(t); T["time"] = pd.to_datetime(T.time_msc, unit="ms"); T.to_csv(f, index=False); src = "broker"; print(y, m, "descargado", len(T), flush=True)
            spr = (T.ask - T.bid)
            gaps = T.time.diff().dt.total_seconds()
            rows.append(dict(symbol=sym, month=f"{y}-{m:02d}", sample_hour_utc=str(T.time.iloc[0].floor("h")), n_ticks=len(T), fuente=src, first=str(T.time.iloc[0]), last=str(T.time.iloc[-1]),
                             bid_ask_invalid=int(((T.bid <= 0) | (T.ask <= 0) | (T.ask < T.bid)).sum()), duplicated_time_msc=int(T.time_msc.duplicated().sum()), max_gap_s=round(float(gaps.max()), 1),
                             spread_min=round(float(spr.min()), 3), spread_med=round(float(spr.median()), 3), spread_max=round(float(spr.max()), 3), spread_changes=int((spr.diff().abs() > 0).sum()),
                             estado="OK"))
    mt5.shutdown()
    D = pd.DataFrame(rows)
    D.to_csv(ROOT / "research" / "V8_TICK_AVAILABILITY.csv", index=False)
    print(D[["month", "n_ticks", "estado", "bid_ask_invalid", "duplicated_time_msc", "max_gap_s", "spread_med"]].to_string())


if __name__ == "__main__":
    main()


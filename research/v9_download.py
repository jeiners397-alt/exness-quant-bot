"""V9 - descarga SEGMENTADA y con CACHE de barras M1/M5 (solo lectura del historial, instancia aislada). Un fichero por simbolo-TF-mes en data/raw/v9/cache.
Nunca solicita datos >= 2026-11-01 (reserva prospectiva). No se rellenan huecos ni se inventan barras."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "raw" / "v9"
C = D / "cache"
C.mkdir(parents=True, exist_ok=True)
PLAN = {"XAUUSDm": ["M1", "M5"], "EURUSDm": ["M5"], "GBPUSDm": ["M5"], "USTECm": ["M5"]}
TFC = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5}
END = datetime(2026, 11, 1, tzinfo=timezone.utc)


def months():
    y, m = 2024, 1
    while (y, m) < (2026, 11):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def main(syms):
    if not mt5.initialize(path=r"C:\REMIX_MT5_LAB\terminal\terminal64.exe", portable=True):
        print("ERROR_DATOS init", mt5.last_error()); return
    info = json.load(open(D / "download_info.json")) if (D / "download_info.json").exists() else {}
    for s in syms:
        mt5.symbol_select(s, True)
        i = mt5.symbol_info(s)
        info[s] = info.get(s, {}) | dict(point=i.point, digits=i.digits, min_lot=i.volume_min, step=i.volume_step, contract=i.trade_contract_size, tick_value=i.trade_tick_value, tick_size=i.trade_tick_size)
        for tf in PLAN[s]:
            mt5.copy_rates_from_pos(s, TFC[tf], 0, 1000)                      # fuerza sincronizacion
            for y, m in months():
                f = C / f"{s}_{tf}_{y}{m:02d}.csv"
                if f.exists():
                    continue
                a = datetime(y, m, 1, tzinfo=timezone.utc)
                b = min(datetime(y + (m == 12), 1 if m == 12 else m + 1, 1, tzinfo=timezone.utc), END)
                r = None
                for _ in range(3):
                    r = mt5.copy_rates_range(s, TFC[tf], a, b)
                    if r is not None and len(r) > 0:
                        break
                if r is None or len(r) == 0:
                    print(s, tf, y, m, "SIN DATOS", mt5.last_error(), flush=True); continue
                df = pd.DataFrame(r); df["time"] = pd.to_datetime(df.time, unit="s")
                df = df[df.time < "2026-11-01"]
                if len(df) == 0:
                    print(s, tf, y, m, "VACIO tras filtro", flush=True); continue
                df.to_csv(f, index=False)
                print(s, tf, y, m, len(df), flush=True)
            parts = sorted(C.glob(f"{s}_{tf}_*.csv"))
            if parts:
                a = pd.concat([pd.read_csv(p, parse_dates=["time"]) for p in parts]).drop_duplicates("time").sort_values("time")
                a.to_csv(D / f"{s}_{tf}.csv", index=False)
                info[s][f"{tf}_bars"] = len(a); info[s][f"{tf}_first"] = str(a.time.iloc[0]); info[s][f"{tf}_last"] = str(a.time.iloc[-1])
    mt5.shutdown()
    json.dump(info, open(D / "download_info.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1:] or list(PLAN))



"""Actualiza solo la cobertura historica (M5/M15) de los simbolos evaluados en EXNESS_MARKET_UNIVERSE.csv (sin repetir el inventario completo)."""
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
F = ROOT / "research" / "EXNESS_MARKET_UNIVERSE.csv"
d = pd.read_csv(F)
assert mt5.initialize(path=r"C:\REMIX_MT5_LAB\terminal\terminal64.exe", portable=True)
now = datetime.utcnow()
for i, r in d[d.history_coverage_evaluated == True].iterrows():
    iss = []
    mt5.symbol_select(r.symbol, True)
    for tf_name, tf in (("M5", mt5.TIMEFRAME_M5), ("M15", mt5.TIMEFRAME_M15)):
        # el terminal limita a 100000 barras por consulta: se pide M15 desde 2024-01-01 (~70k) y M5 desde 2025-07-01; "first" = primera barra DISPONIBLE dentro de esa ventana
        mt5.copy_rates_from_pos(r.symbol, tf, 0, 10)          # fuerza la sincronizacion del simbolo/marco antes de pedir el rango
        rates = mt5.copy_rates_range(r.symbol, tf, datetime(2024, 1, 1) if tf_name == "M15" else datetime(2026, 1, 1), datetime(2026, 11, 1))
        if rates is None:
            print(r.symbol, tf_name, mt5.last_error())
        if rates is None or len(rates) == 0:
            d.loc[i, [f"{tf_name}_bars", f"{tf_name}_first", f"{tf_name}_last"]] = [0, "", ""]
            iss.append(f"sin historial {tf_name}")
            continue
        d.loc[i, f"{tf_name}_bars"] = len(rates)
        d.loc[i, f"{tf_name}_first"] = datetime.utcfromtimestamp(rates[0]["time"]).strftime("%Y-%m-%d")
        d.loc[i, f"{tf_name}_last"] = datetime.utcfromtimestamp(rates[-1]["time"]).strftime("%Y-%m-%d")
        if (now - datetime.utcfromtimestamp(rates[-1]["time"])).days > 10:
            iss.append(f"{tf_name} desactualizado")
        if (rates["spread"] == 0).mean() > 0.5:
            iss.append(f"{tf_name} spread=0 en >50% barras")
        if tf_name == "M15" and datetime.utcfromtimestamp(rates[0]["time"]) > datetime(2024, 1, 15):
            iss.append("historial M15 empieza despues de 2024-01-15")
    d.loc[i, "issues"] = "; ".join(iss) if iss else ""
mt5.shutdown()
d.to_csv(F, index=False)
e = d[d.history_coverage_evaluated == True]
print(e[["symbol", "category", "M5_bars", "M5_first", "M15_bars", "M15_first", "M15_last", "issues"]].to_string())

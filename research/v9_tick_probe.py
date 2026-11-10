"""V9 Fase 15 - sonda SEGMENTADA de ticks reales (solo lectura), cada muestra en un SUBPROCESO con limite de tiempo (V8: copy_ticks_range se colgaba).
Muestras: 5 minutos de un miercoles 14:00 UTC por trimestre, XAUUSDm. Cache local CSV en data/raw/v9/ticks (no se re-descarga). Sin sustitutos si falla: ERROR_DATOS."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "raw" / "v9" / "ticks"
CACHE.mkdir(parents=True, exist_ok=True)
TIMEOUT = 100
CHILD = r'''
import sys, MetaTrader5 as mt5
from datetime import datetime, timezone
import pandas as pd
a=datetime.fromisoformat(sys.argv[1]).replace(tzinfo=timezone.utc); b=datetime.fromisoformat(sys.argv[2]).replace(tzinfo=timezone.utc)
mt5.initialize(path=r"C:\REMIX_MT5_LAB\terminal\terminal64.exe", portable=True); mt5.symbol_select("XAUUSDm", True)
t=mt5.copy_ticks_range("XAUUSDm", a, b, mt5.COPY_TICKS_ALL)
n=0 if t is None else len(t)
if n:
    d=pd.DataFrame(t); d["time"]=pd.to_datetime(d.time_msc, unit="ms"); d.to_csv(sys.argv[3], index=False)
print("N", n, mt5.last_error()); mt5.shutdown()
'''


def main():
    rows = []
    for ds in ("2024-02-14", "2024-05-15", "2024-08-14", "2024-11-13", "2025-02-12", "2025-05-14", "2025-08-13", "2025-11-12", "2026-02-11", "2026-05-13", "2026-08-12", "2026-10-28"):
        a, b = f"{ds}T14:00:00", f"{ds}T14:05:00"
        f = CACHE / f"XAUUSDm_{ds}_1400_5m.csv"
        if f.exists():
            src, n, why = "cache", len(pd.read_csv(f)), ""
        else:
            try:
                r = subprocess.run([sys.executable, "-c", CHILD, a, b, str(f)], capture_output=True, text=True, timeout=TIMEOUT)
                n = int(r.stdout.split("N")[-1].split()[0]) if "N" in r.stdout else 0; src, why = "broker", r.stdout.strip()[-80:]
            except subprocess.TimeoutExpired:
                n, src, why = 0, "broker", f"TIMEOUT>{TIMEOUT}s (proceso aislado terminado)"
                import subprocess as sp
                sp.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | ? { $_.ExecutablePath -like 'C:\\REMIX_MT5_LAB\\*' } | % { Stop-Process -Id $_.ProcessId -Force }"], capture_output=True)
        row = dict(symbol="XAUUSDm", sample=f"{a}..{b} UTC", fuente=src, n_ticks=n, estado="OK" if n > 0 else "ERROR_DATOS", detalle=why)
        if n > 0:
            T = pd.read_csv(f, parse_dates=["time"]); spr = T.ask - T.bid
            row.update(bid_ask_invalid=int(((T.bid <= 0) | (T.ask < T.bid)).sum()), dup_time_msc=int(T.time_msc.duplicated().sum()), max_gap_s=round(float(T.time.diff().dt.total_seconds().max()), 1),
                       spread_med=round(float(spr.median()), 3), spread_max=round(float(spr.max()), 3), spread_changes=int((spr.diff().abs() > 0).sum()))
        rows.append(row); print(row, flush=True)
    pd.DataFrame(rows).to_csv(ROOT / "research" / "V9_TICK_AVAILABILITY.csv", index=False)


if __name__ == "__main__":
    main()

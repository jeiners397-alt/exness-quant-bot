"""Descarga (solo lectura) de historia ANTERIOR a 2025 para EURUSDm: muestra retrospectiva no inspeccionada hasta ahora.
Guarda en data/raw/hist/ (no sobrescribe data/raw/*). Aborta si la cuenta no es DEMO."""
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import MetaTrader5 as mt5  # noqa: E402
import pandas as pd  # noqa: E402
from remix_lab import data_engine as de  # noqa: E402

assert de.connect()
assert mt5.account_info().trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO, "cuenta no demo"
out = ROOT / "data" / "raw" / "hist"
out.mkdir(parents=True, exist_ok=True)
sym = "EURUSDm"
mt5.symbol_select(sym, True)
for tf, start in (("H1", datetime(2010, 1, 1, tzinfo=timezone.utc)), ("M15", datetime(2018, 1, 1, tzinfo=timezone.utc))):
    df = de.fetch_rates(sym, tf, start, datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc), chunk_days=60)
    df.to_csv(out / f"{sym}_{tf}_pre2025.csv", index=False)
    if len(df):
        print(tf, len(df), df.time.min(), df.time.max(), "spread med/min/max", df.spread.median(), df.spread.min(), df.spread.max(), "dups", int(df.time.duplicated().sum()))
    else:
        print(tf, "sin datos")
mt5.shutdown()

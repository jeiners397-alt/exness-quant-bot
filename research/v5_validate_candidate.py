"""Validacion temporal del unico candidato positivo (F1 SWEEP_REV, ETHUSDm M15) con parametros CONGELADOS: ejecuciones por anio y una con ticks reales (2026).
Los periodos ya fueron vistos en el escaneo inicial: NO son fuera de muestra independiente; sirven para estabilidad temporal. Solo Strategy Tester."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation.multi_market_batch_runner import FROZEN, TF_PARAMS, _record, _rows  # noqa: E402
from automation.run_mt5_test import run_id, run_test  # noqa: E402

CASES = [("2024.01.01", "2024.12.31", "ohlc_1m", "val2024"), ("2025.01.01", "2025.12.31", "ohlc_1m", "val2025"), ("2026.01.01", "2026.11.01", "ohlc_1m", "val2026"),
         ("2026.01.01", "2026.11.01", "real_ticks", "val2026_realticks")]
sym, cat, tf = "ETHUSDm", "CRYPTO", "M15"
for fd, td, model, tag in CASES:
    lab = f"F1_SWEEP_REV_{tag}"
    if any(r["strategy"] == lab and r["symbol"] == sym for r in _rows()):
        continue
    inputs = dict(FROZEN, Family=1, EnableTrading="true", MagicNumber=20260501, **TF_PARAMS[tf])
    rid = run_id(sym, tf, lab, len(_rows()) + 1)
    meta = run_test(rid=rid, expert="REMIX\\REMIX_V5_GENERIC", symbol=sym, period=tf, from_date=fd, to_date=td, inputs=inputs, strategy=lab, deposit=3000.0, leverage=500,
                    model=model, timeout=3000, ea_version="V5 validacion")
    _record(meta, cat, tf, lab, sym)

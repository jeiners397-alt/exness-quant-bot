"""Sensibilidad del limite de riesgo al SL (RiskPercent) con F2 M15 en 3 mercados; el margen 5 % se mantiene. Solo Strategy Tester."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation.multi_market_batch_runner import FROZEN, TF_PARAMS, _record, _rows  # noqa: E402
from automation.run_mt5_test import run_id, run_test  # noqa: E402

SYMS = {"EURUSDm": "FOREX_MAJOR", "XAUUSDm": "GOLD", "US30m": "INDEX_US"}
for risk in (0.25, 1.0, 2.0):
    for sym, cat in SYMS.items():
        lab = f"F2_DONCHIAN_BO_risk{risk}"
        if any(r["strategy"] == lab and r["symbol"] == sym for r in _rows()):
            continue
        inputs = dict(FROZEN, Family=2, EnableTrading="true", MagicNumber=20260501, **TF_PARAMS["M15"])
        inputs["RiskPercent"] = risk
        rid = run_id(sym, "M15", lab.replace(".", "p"), len(_rows()) + 1)
        meta = run_test(rid=rid, expert="REMIX\\REMIX_V5_GENERIC", symbol=sym, period="M15", from_date="2024.01.01", to_date="2026.11.01", inputs=inputs, strategy=lab,
                        deposit=3000.0, leverage=500, model="ohlc_1m", timeout=2400, ea_version="V5 sensibilidad riesgo")
        _record(meta, cat, "M15", lab, sym)

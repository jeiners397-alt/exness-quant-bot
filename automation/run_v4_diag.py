"""Compila REMIX_EURUSD_V4 y ejecuta el diagnostico de margen/multiposicion en el Strategy Tester aislado para uno o varios simbolos."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation.autonomous_lab import run_mt5_experiment  # noqa: E402

INPUTS = dict(Module=1, EnableTrading="true", MagicNumber=20260401, MarginPct=5.0, GlobalMarginPct=15.0, RiskPercent=0.5, MaxTotalRiskPct=5.0,
              CheckPendingOrders="true", AllowMultiple="true", MaxPositions=20, DiagEveryBars=3, DiagMaxHoldBars=60, DiagRR=1.5, DiagPendingEvery=4,
              ATR_N=14, SL_ATR_Mult=1.5, SL_StructLookback=10, SL_StructBufATR=0.1, SL_MinATR=0.7, SL_MaxATR=3.0)

if __name__ == "__main__":
    for sym in sys.argv[1:] or ["EURUSDm"]:
        m = run_mt5_experiment(ea_src=ROOT / "mql5" / "REMIX_EURUSD_V4.mq5", expert="REMIX\\REMIX_EURUSD_V4", symbol=sym, period="M15",
                               strategy="V4_DIAG_MULTI", inputs=dict(INPUTS), from_date="2025.06.02", to_date="2025.09.01", deposit=3000.0, leverage=500,
                               model="ohlc_1m", timeout=900)
        print(sym, m.get("status"), m.get("detail"), json.dumps(m.get("parsed", {}) and {k: m["parsed"][k] for k in ("total_net_profit", "total_trades", "profit_factor", "equity_dd_max_pct")}))

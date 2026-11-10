"""V8 - ejecuta backtests oficiales del EA REMIX_V8_XAU_BREAKOUT en el Strategy Tester aislado.
Uso: python -m research.v8_lote_a_run <variant 0|1> <rr> <model ohlc_1m|every_tick|real_ticks> [tag] [period=H4] [symbol=XAUUSDm] [Input=valor ...]
Solo Strategy Tester; periodo 2024-01-01 -> 2026-10-31 (la reserva posterior a 2026-11-01 no se toca)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from automation.autonomous_lab import run_mt5_experiment

ROOT = Path(__file__).resolve().parent.parent


def main():
    variant, rr, model = int(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
    tag = sys.argv[4] if len(sys.argv) > 4 else f"V8A{variant}_RR{rr}_{model}"
    extra = dict(a.split("=", 1) for a in sys.argv[5:])
    period, symbol = extra.pop("period", "H1"), extra.pop("symbol", "XAUUSDm")
    inputs = dict(EnableTrading="true", Variant=variant, RR=rr, FixedLot=0.01, RiskPctCap=3.0, RunTag=tag, **extra)
    m = run_mt5_experiment(ea_src=ROOT / "mql5" / "REMIX_V8_XAU_BREAKOUT.mq5", expert="REMIX\\REMIX_V8_XAU_BREAKOUT", symbol=symbol, period=period,
                           strategy=f"V8_XAU_BREAKOUT_{tag}", inputs=inputs, from_date="2024.01.01", to_date="2026.10.31", deposit=3000.0, leverage=500, model=model, timeout=3000)
    print(json.dumps({k: v for k, v in m.items() if k != "parsed"}, default=str, indent=1)[:1800])
    print(json.dumps(m.get("parsed", {}), default=str)[:1500])


if __name__ == "__main__":
    main()

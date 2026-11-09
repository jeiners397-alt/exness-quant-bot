import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation.compile_ea import compile_ea  # noqa: E402
from automation.mt5_market_scanner import run_scan  # noqa: E402
from automation.multi_market_batch_runner import FROZEN, TF_PARAMS  # noqa: E402

c = compile_ea(ROOT / "mql5" / "REMIX_V5_GENERIC.mq5")
assert c["ok"]
syms = ["EURUSDm", "GBPUSDm", "XAUUSDm", "US30m"]
inputs = dict(FROZEN, Family=2, EnableTrading="true", MagicNumber=20260501, **TF_PARAMS["M15"])
r = run_scan("SCAN_PROBE_F2_M15", syms, "REMIX\\REMIX_V5_GENERIC", inputs, "M15", "2026.01.02", "2026.03.01", timeout=900)
print(json.dumps({k: v for k, v in r.items() if k != "tester_log_tail"}, indent=1, default=str))
print("\n".join(r["tester_log_tail"][-15:]))

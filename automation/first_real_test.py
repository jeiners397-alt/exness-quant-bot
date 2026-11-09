"""Primera prueba automatica real: V3 modulo A (H1) en EURUSDm, via instancia aislada. Solo Strategy Tester."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation.compile_ea import compile_ea  # noqa: E402
from automation.run_mt5_test import run_id, run_test  # noqa: E402


def load_set(p: Path) -> dict:
    d = {}
    for l in p.read_text(encoding="utf-16").splitlines():
        if "=" in l and not l.startswith((";", "#")):
            k, v = l.split("=", 1); d[k.strip()] = v.strip()
    return d


if __name__ == "__main__":
    c = compile_ea(ROOT / "mql5" / "REMIX_EURUSD_V3.mq5")
    assert c["ok"], c
    inputs = load_set(ROOT / "mql5" / "sets" / "V3_A_H1_PD_struct.set")
    rid = run_id("EURUSDm", "H1", "V3_A_PD_STRUCT", 1)
    meta = run_test(rid=rid, expert="REMIX\\REMIX_EURUSD_V3", symbol="EURUSDm", period="H1", from_date="2025.01.01", to_date="2026.11.01",
                    inputs=inputs, strategy="V3_A_PD_STRUCT", deposit=3000.0, leverage=500, model="ohlc_1m", timeout=2400,
                    ea_version="V3 sha " + c["sha256_src"][:12])
    print(json.dumps({k: v for k, v in meta.items() if k != "inputs"}, indent=1, default=str))

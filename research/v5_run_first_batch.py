import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation.multi_market_batch_runner import run_batch  # noqa: E402

SYMS = {"EURUSDm": "FOREX_MAJOR", "GBPUSDm": "FOREX_MAJOR", "USDJPYm": "FOREX_MAJOR", "AUDUSDm": "FOREX_MAJOR", "XAUUSDm": "GOLD", "XAGUSDm": "SILVER",
        "US30m": "INDEX_US", "US500m": "INDEX_US", "USTECm": "INDEX_US", "BTCUSDm": "CRYPTO", "ETHUSDm": "CRYPTO"}
if __name__ == "__main__":
    fams = sys.argv[1].split(",") if len(sys.argv) > 1 else ["F2_DONCHIAN_BO", "F1_SWEEP_REV", "F3_ZSCORE_REV"]
    tfs = sys.argv[2].split(",") if len(sys.argv) > 2 else ["M15", "M5"]
    run_batch(SYMS, fams, tfs, "2024.01.01", "2026.11.01", timeout=2400)

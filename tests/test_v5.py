import re
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation.multi_market_batch_runner import COLS, FAMILIES, classify  # noqa: E402

SRC = (ROOT / "mql5" / "REMIX_V5_GENERIC.mq5").read_text(encoding="utf-8-sig")


def test_v5_ea_is_generic_and_safe():
    assert "EURUSD" not in re.sub(r"//.*", "", SRC) and "_Symbol" in SRC and "_Period" in SRC
    assert re.search(r"input ENUM_FAMILY Family\s*=\s*FAM_NONE", SRC) and re.search(r"input bool\s+EnableTrading\s*=\s*false", SRC)
    assert "OrderSend(" not in SRC and "MQL_TESTER" in SRC and "ACCOUNT_TRADE_MODE_REAL" in SRC and "martingal" not in SRC.lower()
    funcs, name, cur = {}, None, []
    for line in SRC.splitlines():
        m = re.match(r"^(?:void|bool|double|int|string)\s+(\w+)\s*\(", line)
        if m:
            if name: funcs[name] = "\n".join(cur)
            name, cur = m.group(1), [line]
        elif name:
            cur.append(line)
    funcs[name] = "\n".join(cur)
    for fn, body in funcs.items():
        if re.search(r"trade\.(Buy|Sell|PositionClose|PositionModify)\(", body):
            assert fn in {"OpenTrade", "CloseOld"} and "TradingAllowed()" in body, fn
    assert "pip" not in re.sub(r"//.*", "", SRC).lower()              # sin supuestos de pip de Forex en el codigo (comentarios aparte)


def test_scanner_uses_official_optimization_3_and_fallback_documented():
    s = (ROOT / "automation" / "mt5_market_scanner.py").read_text(encoding="utf-8")
    assert "Optimization=3" in s and "metatrader5.com/en/terminal/help/start_advanced/start" in s and "metodo alternativo" in s.lower()


def test_classifier_rules():
    assert classify(0, None, 0, "", "SIN_OPERACIONES", 100)[0] == "D"
    assert classify(10, 2.0, 50, 0.1, "OK", 100)[0] == "B"            # pocas operaciones: nunca A
    assert classify(500, 1.5, 300, 0.1, "OK", 100)[0] == "B"          # positivo en una ejecucion: nunca A sin validacion
    assert classify(500, 0.9, -300, -0.1, "OK", 100)[0] == "C"
    assert classify(0, None, None, "", "TIMEOUT", None)[0] == "E"
    assert set(FAMILIES) == {"F1_SWEEP_REV", "F2_DONCHIAN_BO", "F3_ZSCORE_REV"}


M = ROOT / "research" / "MULTI_MARKET_STRATEGY_MATRIX.csv"


@pytest.mark.skipif(not M.exists(), reason="matriz local")
def test_matrix_integrity():
    m = pd.read_csv(M)
    assert list(m.columns) == COLS and m.run_id.is_unique
    assert not (m["class"] == "A").any()                                # ninguna estrategia se promueve sin validacion independiente
    ok = m[m.status == "OK"]
    assert (ok.period_in_log == "PERIOD_" + ok.timeframe).all() and (ok.symbol_in_log == ok.symbol).all()
    assert (m.capital == 3000.0).all()
    assert set(m.timeframe) <= {"M5", "M15"}

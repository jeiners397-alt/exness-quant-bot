"""Pruebas estaticas de seguridad del EA V2 (sin MT5): defaults desactivados, puerta de trading, SL obligatorio, sin martingala."""
import re
from pathlib import Path

SRC = (Path(__file__).resolve().parent.parent / "mql5" / "REMIX_EURUSD_V2.mq5").read_text(encoding="utf-8")


def functions():
    out, cur, name = {}, [], None
    for line in SRC.splitlines():
        m = re.match(r"^(?:void|bool|double|int|string|ENUM_TIMEFRAMES)\s+(\w+)\s*\(", line)
        if m:
            if name:
                out[name] = "\n".join(cur)
            name, cur = m.group(1), [line]
        elif name:
            cur.append(line)
    if name:
        out[name] = "\n".join(cur)
    return out


def test_defaults_disable_trading():
    assert re.search(r"input ENUM_V2_MODULE Module\s*=\s*MOD_NONE", SRC)
    assert re.search(r"input bool\s+EnableTrading\s*=\s*false", SRC)
    assert re.search(r"input bool\s+RequireTimeframe\s*=\s*true", SRC)


def test_tester_only_and_not_real_account():
    f = functions()
    assert "MQL_TESTER" in f["TradingAllowed"] and "ACCOUNT_TRADE_MODE_REAL" in f["TradingAllowed"] and "EnableTrading" in f["TradingAllowed"]
    assert "INIT_FAILED" in f["OnInit"] and "MQL_TESTER" in f["OnInit"]


def test_trade_calls_only_in_guarded_functions():
    f = functions()
    calls = re.compile(r"trade\.(Buy|Sell|PositionClose|PositionModify)\(|OrderSend|OrderSendAsync|CTrade\s*\w*\.\w*Order")
    allowed = {"OpenTrade", "ClosePosition", "ModifySL"}
    for name, body in f.items():
        if calls.search(body):
            assert name in allowed, f"llamada de trading fuera de funciones protegidas: {name}"
            assert "TradingAllowed()" in body, f"{name} sin TradingAllowed()"
    assert "OrderSend(" not in SRC and "OrderSendAsync" not in SRC


def test_stop_loss_mandatory_and_no_martingale():
    assert "SKIP_NO_SL" in functions()["OpenTrade"]
    low = SRC.lower()
    for bad in ("martingal", "lots *= ", "lots = lots *", "double_lot", "recover"):
        assert bad not in low
    assert "SizingPolicy == SIZE_STRICT" in functions()["CalcLots"]


def test_only_eurusd_and_defaults_documented():
    assert 'StringFind(_Symbol, "EURUSD") != 0' in SRC
    assert "NINGUN MODULO TIENE VENTAJA" in SRC

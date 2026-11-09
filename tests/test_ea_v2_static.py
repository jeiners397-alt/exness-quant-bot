"""Pruebas estaticas de seguridad de los EA V2 y V2.1 (sin MT5): defaults desactivados, puerta de trading, SL obligatorio, sin martingala."""
import re
from pathlib import Path

import pytest

MQL = Path(__file__).resolve().parent.parent / "mql5"
NAMES = ["REMIX_EURUSD_V2.mq5", "REMIX_EURUSD_V2_1.mq5"]


def load(name):
    return (MQL / name).read_text(encoding="utf-8-sig")


def functions(src):
    out, cur, name = {}, [], None
    for line in src.splitlines():
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


@pytest.mark.parametrize("name", NAMES)
def test_defaults_disable_trading(name):
    src = load(name)
    assert re.search(r"input ENUM_V2_MODULE Module\s*=\s*MOD_NONE", src)
    assert re.search(r"input bool\s+EnableTrading\s*=\s*false", src)
    assert re.search(r"input bool\s+RequireTimeframe\s*=\s*true", src)


@pytest.mark.parametrize("name", NAMES)
def test_tester_only_and_not_real_account(name):
    f = functions(load(name))
    assert "MQL_TESTER" in f["TradingAllowed"] and "ACCOUNT_TRADE_MODE_REAL" in f["TradingAllowed"] and "EnableTrading" in f["TradingAllowed"]
    assert "INIT_FAILED" in f["OnInit"] and "MQL_TESTER" in f["OnInit"]


@pytest.mark.parametrize("name", NAMES)
def test_trade_calls_only_in_guarded_functions(name):
    src = load(name)
    f = functions(src)
    calls = re.compile(r"trade\.(Buy|Sell|PositionClose|PositionModify)\(|OrderSend|OrderSendAsync")
    allowed = {"OpenTrade", "ClosePosition", "ModifySL"}
    for fn, body in f.items():
        if calls.search(body):
            assert fn in allowed, f"llamada de trading fuera de funciones protegidas: {fn}"
            assert "TradingAllowed()" in body, f"{fn} sin TradingAllowed()"
    assert "OrderSend(" not in src and "OrderSendAsync" not in src


@pytest.mark.parametrize("name", NAMES)
def test_stop_loss_mandatory_and_no_martingale(name):
    src = load(name)
    assert "SKIP_NO_SL" in functions(src)["OpenTrade"]
    low = src.lower()
    for bad in ("martingal", "lots *= ", "lots = lots *", "double_lot", "recover"):
        assert bad not in low
    assert "SizingPolicy == SIZE_STRICT" in functions(src)["CalcLots"]


@pytest.mark.parametrize("name", NAMES)
def test_only_eurusd_and_disclaimer(name):
    src = load(name)
    assert 'StringFind(_Symbol, "EURUSD") != 0' in src
    assert "NINGUN MODULO TIENE VENTAJA" in src


def test_v21_fixes_present_and_l2_params_unchanged():
    v2, v21 = load(NAMES[0]), load(NAMES[1])
    assert "iBarShift(_Symbol, _Period, g_entry_bar" in v21 and "iBarShift" not in v2
    assert "PeriodSeconds(_Period)) >= g_max_bars" in v2                      # V2 intacto (comportamiento original conservado)
    for p in ("S05_SMA_N           = 50;", "S05_Z               = 2.0;", "S05_ADXMax          = 25.0;", "S05_SL_ATR          = 2.0;", "S05_MaxBars         = 18;"):
        assert p in v2 and p in v21
    assert "ExportBarDiag" in v21 and "RetryFailedClose" in v21 and re.search(r"input bool\s+RetryFailedClose\s*=\s*false", v21)

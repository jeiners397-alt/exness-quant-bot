import hashlib
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation.parse_mt5_report import parse_report  # noqa: E402

SRC = (ROOT / "mql5" / "REMIX_EURUSD_V4.mq5").read_text(encoding="utf-8-sig")


def test_v4_ea_safety_static():
    assert re.search(r"input ENUM_V4_MODULE Module\s*=\s*V4_NONE", SRC) and re.search(r"input bool\s+EnableTrading\s*=\s*false", SRC)
    assert "OrderSend(" not in SRC and "OrderSendAsync" not in SRC and "martingal" not in SRC.lower()
    assert "MQL_TESTER" in SRC and "ACCOUNT_TRADE_MODE_REAL" in SRC
    assert "MarginPct" in SRC and "OrderCalcMargin" in SRC and "OrderCalcProfit" in SRC and "CheckPendingOrders" in SRC
    # solo OpenTrade y CloseOld llaman a trade.*
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
        if re.search(r"trade\.(Buy|Sell|BuyLimit|SellLimit|PositionClose|PositionModify)\(", body):
            assert fn in {"OpenTrade", "CloseOld"} and "TradingAllowed()" in body, fn


def test_v4_never_rounds_volume_up():
    assert "MathFloor(v / step" in SRC and "MathCeil" not in SRC and "MathRound(lots" not in SRC


RUNS = ROOT / "results" / "v4_runs"


@pytest.mark.skipif(not RUNS.exists(), reason="informes oficiales locales no incluidos en el repositorio")
def test_parsed_official_reports_are_internally_consistent():
    import pandas as pd
    n = 0
    for d in RUNS.glob("RUN_*"):
        if not (d / "report.htm").exists():
            continue
        r = parse_report(d / "report.htm")
        t = parse_report(d / "report.htm", d)  # regenera trades.csv
        tr = pd.read_csv(d / "trades.csv")
        s = r["stats"]
        assert r["complete"] and abs((tr.profit + tr.commission.fillna(0) + tr.swap.fillna(0)).sum() - s["total_net_profit"]) < 0.02
        assert len(tr) == int(s["total_trades"])
        n += 1
    assert n >= 1

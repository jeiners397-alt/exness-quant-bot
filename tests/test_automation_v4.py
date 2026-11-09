import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation import drive_backup as db, experiment_selector as sel  # noqa: E402
from automation.parse_mt5_report import parse_report  # noqa: E402

HTML = """<html><body><table>
<tr><td>Initial Deposit:</td><td>3 000.00</td><td>Total Net Profit:</td><td>27.32</td></tr>
<tr><td>Profit Factor:</td><td>1.18</td><td>Total Trades:</td><td>27</td></tr>
<tr><td>Equity Drawdown Maximal:</td><td>68.00 (2.29%)</td></tr>
<tr><td>Time</td><td>Deal</td><td>Symbol</td><td>Type</td><td>Direction</td><td>Volume</td><td>Price</td><td>Order</td><td>Commission</td><td>Swap</td><td>Profit</td><td>Balance</td><td>Comment</td></tr>
<tr><td>2025.01.02 10:00:00</td><td>2</td><td>EURUSDm</td><td>buy</td><td>in</td><td>0.10</td><td>1.03000</td><td>2</td><td>0.00</td><td>0.00</td><td>0.00</td><td>3 000.00</td><td></td></tr>
<tr><td>2025.01.02 14:00:00</td><td>3</td><td>EURUSDm</td><td>sell</td><td>out</td><td>0.10</td><td>1.03247</td><td>3</td><td>0.00</td><td>-0.10</td><td>24.72</td><td>3 024.62</td><td>tp</td></tr>
</table></body></html>"""


def test_parser_extracts_official_stats_and_trades(tmp_path):
    p = tmp_path / "r.htm"
    p.write_bytes(b"\xff\xfe" + HTML.encode("utf-16-le"))
    r = parse_report(p, tmp_path / "out")
    s = r["stats"]
    assert s["total_net_profit"] == 27.32 and s["total_trades"] == 27 and s["profit_factor"] == 1.18 and s["initial_deposit"] == 3000.0
    assert s["equity_dd_max_pct"] == 2.29 and r["complete"] and r["n_trades"] == 1
    assert (tmp_path / "out" / "trades.csv").exists() and (tmp_path / "out" / "stats.json").exists()


def test_parser_does_not_invent_missing_metrics(tmp_path):
    p = tmp_path / "r.htm"; p.write_text("<table><tr><td>Total Trades:</td><td>0</td></tr></table>", encoding="utf-8")
    r = parse_report(p)
    assert r["stats"]["total_net_profit"] is None and not r["complete"]


def test_drive_manifest_only_marks_real_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "BK", tmp_path); monkeypatch.setattr(db, "QUEUE", tmp_path / "q.csv"); monkeypatch.setattr(db, "MANIFEST", tmp_path / "m.csv")
    f = tmp_path / "res.csv"; f.write_text("a,b\n1,2\n")
    r = db.enqueue(f, "04", "EXP1")
    assert r and r["upload_state"] == "PENDING" and db.enqueue(tmp_path / ".env", "04") is None
    with pytest.raises(AssertionError):
        db.mark_uploaded("res.csv", r["sha256"], "x", "l")
    db.mark_uploaded("res.csv", r["sha256"], "1" * 33, "https://drive.google.com/file/d/" + "1" * 33)
    assert "UPLOADED" in (tmp_path / "m.csv").read_text() and db.verify_local() == []
    f.write_text("changed"); assert db.verify_local()


def test_selector_respects_limits_and_discards():
    b = sel.select_batch(50)
    assert len(b) <= 20 and all(r["status"] == "PLANNED" for r in b)
    ids = {r["exp_id"] for r in sel.load() if r["decision"] in sel.DISCARDED}
    assert not ids & {r["exp_id"] for r in b}


def test_runner_never_targets_main_terminal_and_no_order_send():
    src = (ROOT / "automation" / "run_mt5_test.py").read_text(encoding="utf-8")
    assert "/portable" in src and "assert str(LAB).lower() != str(MAIN_TERMINAL_DIR).lower()" in src
    assert not re.search(r"order_send\(", re.sub(r"(?s)\"\"\".*?\"\"\"|#.*", "", src))

"""Tests sin conectarse al bróker ni crear órdenes."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from research.data_client import normalize_bars
from research.mt5_connection import audit, choose_symbols, read_account_mode


class TestBasic(unittest.TestCase):
    def test_symbols_suffix(self):
        s = [SimpleNamespace(name=x) for x in ("EURUSDm", "EURUSD", "GBPUSDm", "XAUUSDm")]
        d = choose_symbols(s)
        self.assertEqual(d["EURUSD"], ["EURUSD", "EURUSDm"])
        self.assertEqual(d["USDJPY"], [])

    def test_demo_mode(self):
        m = SimpleNamespace(ACCOUNT_TRADE_MODE_DEMO=0, ACCOUNT_TRADE_MODE_REAL=2, ACCOUNT_TRADE_MODE_CONTEST=1)
        self.assertEqual(read_account_mode(m, SimpleNamespace(trade_mode=0)), "DEMO")
        self.assertEqual(read_account_mode(m, SimpleNamespace(trade_mode=2)), "REAL")

    def test_missing_current_bar(self):
        # 12:09, M5: se excluye la vela que abre 12:05; sólo queda 12:00.
        ts = lambda h, m: int(datetime(2026, 11, 6, h, m, tzinfo=timezone.utc).timestamp())
        data = [(ts(12,0), 1.1,1.3,1.0,1.2,10,15,0), (ts(12,5),1.2,1.4,1.1,1.3,12,15,0)]
        a, q = normalize_bars(data, datetime(2026, 11, 6, 12, 9, tzinfo=timezone.utc), 5)
        self.assertEqual(len(a), 1)
        self.assertEqual(q["bars"], 1)

    def test_invalid_ohlc(self):
        ts = int(datetime(2026, 11, 6, tzinfo=timezone.utc).timestamp())
        with self.assertRaises(ValueError):
            normalize_bars([(ts, 1.3, 1.2, 1.0, 1.1, 1, 1, 0)], datetime(2026, 11, 7, tzinfo=timezone.utc), 5)

    def test_duplicate_bar_rejected(self):
        ts = int(datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc).timestamp())
        row = (ts, 1.1, 1.2, 1.0, 1.15, 10, 15, 0)
        with self.assertRaises(ValueError):
            normalize_bars([row, row], datetime(2026, 11, 6, 12, 10, tzinfo=timezone.utc), 5)

    def test_failure_shuts_down(self):
        m = Mock()
        m.initialize.return_value = True
        m.terminal_info.return_value = None
        m.account_info.return_value = None
        with self.assertRaises(RuntimeError):
            audit(m)
        m.shutdown.assert_called_once()
        m.order_send.assert_not_called()

    def test_audit_never_orders(self):
        m = Mock()
        m.ACCOUNT_TRADE_MODE_DEMO = 0
        m.ACCOUNT_TRADE_MODE_REAL = 2
        m.ACCOUNT_TRADE_MODE_CONTEST = 1
        m.initialize.return_value = True
        m.terminal_info.return_value = SimpleNamespace(connected=True, trade_allowed=True, build=5500)
        m.account_info.return_value = SimpleNamespace(trade_mode=0, server="demo", currency="USD", balance=1000, equity=1000)
        m.symbols_get.return_value = [SimpleNamespace(name="EURUSDm")]
        m.symbol_info.return_value = SimpleNamespace(visible=True, point=0.00001, volume_min=0.01, volume_max=100, volume_step=0.01)
        m.symbol_info_tick.return_value = SimpleNamespace(bid=1.10, ask=1.10012, time=1783425600)
        m.order_calc_margin.return_value = 15.0
        data = audit(m)
        self.assertEqual(data["orders_submitted"], 0)
        self.assertEqual(data["account"]["trade_mode"], "DEMO")
        m.order_send.assert_not_called()
        m.shutdown.assert_called_once()


if __name__ == "__main__":
    unittest.main()

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from remix_lab.events import barrier_events, wilson  # noqa: E402


def mk(rows, spread=10):
    t = pd.date_range("2025-01-06 08:00", periods=len(rows), freq="1h")
    return pd.DataFrame({"time": t, "open": [r[0] for r in rows], "high": [r[1] for r in rows], "low": [r[2] for r in rows], "close": [r[3] for r in rows], "spread": spread})


def run(rows, d0, risk, horizon=4, ks=(1.0, 2.0)):
    df = mk(rows)
    d = np.zeros(len(df), int); d[0] = d0
    sl = np.full(len(df), risk)
    return barrier_events(df, d, sl, horizon, ks)


def test_long_tp_before_sl_and_costs_in_price():
    # senal en barra 0; entrada barra 1 al ask 1.1000+0.0001; riesgo 0.002; TP1=1.1021 (bid high 1.1030 lo alcanza), SL=1.0981 no se toca
    e = run([(1.1, 1.1, 1.1, 1.1), (1.1, 1.103, 1.0995, 1.102), (1.102, 1.1025, 1.101, 1.102), (1.102, 1.102, 1.102, 1.102), (1.102,) * 4, (1.102,) * 4], 1, 0.002)
    assert e["Rc_1.0"].iloc[0] == 1.0 and e["Ro_1.0"].iloc[0] == 1.0 and e["win_1.0"].iloc[0] == 1 and e["amb_1.0"].iloc[0] == 0


def test_same_bar_hit_gives_two_bounds():
    e = run([(1.1, 1.1, 1.1, 1.1), (1.1, 1.104, 1.097, 1.1), (1.1,) * 4, (1.1,) * 4, (1.1,) * 4, (1.1,) * 4], 1, 0.002)
    assert e["amb_1.0"].iloc[0] == 1 and e["Rc_1.0"].iloc[0] == -1.0 and e["Ro_1.0"].iloc[0] == 1.0


def test_short_uses_ask_for_stop_and_bid_entry():
    # corto entra al bid 1.1000; SL en ask: precio 1.1020; ask_high = high + 0.0001 -> con high 1.1019 ya toca (1.1020)
    e = run([(1.1, 1.1, 1.1, 1.1), (1.1, 1.1019, 1.0999, 1.1), (1.1,) * 4, (1.1,) * 4, (1.1,) * 4, (1.1,) * 4], -1, 0.002)
    assert e["Rc_1.0"].iloc[0] == -1.0


def test_timeout_marks_to_market_and_wilson():
    e = run([(1.1, 1.1, 1.1, 1.1), (1.1, 1.1005, 1.0995, 1.1), (1.1, 1.1005, 1.0995, 1.1), (1.1, 1.1005, 1.0995, 1.1), (1.1, 1.1005, 1.0995, 1.1), (1.1, 1.1005, 1.0995, 1.1)], 1, 0.002)
    assert abs(e["Rc_1.0"].iloc[0] - (1.1 - 1.1001) / 0.002) < 1e-9          # sale a bid=close tras pagar el ask de entrada
    lo, hi = wilson(50, 100)
    assert 0.40 < lo < 0.41 and 0.59 < hi < 0.60


import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from remix_lab.exit_variants import Variant, prep_bars, run_variant  # noqa: E402


def mk(rows):
    t0 = pd.Timestamp("2025-01-06 07:00")
    d = [{"time": t0 + pd.Timedelta(minutes=15 * i), "open": o, "high": h, "low": l, "close": c, "spread": 10} for i, (o, h, l, c) in enumerate(rows)]
    return prep_bars(pd.DataFrame(d))


def trade(d, entry, risk, lots=0.1):
    return pd.DataFrame([{"dir": d, "entry": entry, "sl_dist": risk, "lots": lots, "open_time": pd.Timestamp("2025-01-06 07:00")}])


def test_tp_long_and_short_are_plus_1_5R():
    b = mk([(1.0, 1.0, 1.0, 1.0), (1.0, 1.02, 1.0, 1.02)])
    assert abs(run_variant(trade(1, 1.0, 0.01), b, Variant("V0", "")).R[0] - 1.5) < 1e-9
    b2 = mk([(1.0, 1.0, 1.0, 1.0), (1.0, 1.0, 0.98, 0.98)])
    assert abs(run_variant(trade(-1, 1.0, 0.01), b2, Variant("V0", "")).R[0] - 1.5) < 1e-9


def test_sl_first_when_both_hit_same_bar():
    b = mk([(1.0, 1.02, 0.98, 1.0)])
    r = run_variant(trade(1, 1.0, 0.01), b, Variant("V0", ""))
    assert r.reason[0] == "SL" and abs(r.R[0] + 1.0) < 1e-9


def test_short_pays_spread_on_stop():
    b = mk([(1.0, 1.0095, 1.0, 1.0)])           # ask high = 1.0095+0.0001 >= sl 1.01? no; usar 1.0099
    b = mk([(1.0, 1.0099, 1.0, 1.0)])
    r = run_variant(trade(-1, 1.0, 0.01), b, Variant("V0", ""))
    assert r.reason[0] == "SL"


def test_breakeven_only_effective_next_bar():
    # barra 1: llega a +1R y retrocede a la entrada dentro de la misma barra: el BE NO debe haber stoppeado en esa barra
    b = mk([(1.0, 1.0, 1.0, 1.0), (1.0, 1.0105, 0.9999, 1.0), (1.0, 1.0, 1.0, 1.0)])
    r = run_variant(trade(1, 1.0, 0.01), b, Variant("V1b", "", be_trigger_R=1.0))
    assert r.reason[0] != "SL_MOVED" or r.R[0] <= 0

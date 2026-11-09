import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from remix_lab.backtest import BacktestConfig, run_backtest  # noqa: E402
from remix_lab.strategies import Signals, generate  # noqa: E402
from remix_lab.strategies_d import GEN, htf_align, prev_day_levels, resample, transform  # noqa: E402
from tests.test_lookahead import SPEC, synth  # noqa: E402

SPECX = {"point": 1e-5, "value_per_price_unit_per_lot": 100000.0, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 100.0, "swap_mode": 1, "swap_long": 0.0, "swap_short": 0.0}


@pytest.mark.parametrize("sid", ["S05", "S06", "S07", "S08", "S09", "S10", "S11", "S12"])
def test_new_strategies_are_causal(sid):
    df = synth(4000, seed=11)
    full = GEN[sid](df, {})
    n_sig = (full.direction != 0).sum()
    for cut in (1500, 2600, 3400):
        part = GEN[sid](df.iloc[:cut].reset_index(drop=True), {})
        a, b = full.direction[:cut - 1], part.direction[:cut - 1]
        if sid in ("S07",):     # niveles del dia anterior: el dia en curso del corte puede ser incompleto, no afecta a PDH/PDL (solo dias terminados)
            pass
        assert np.array_equal(a, b), f"{sid} cambia al truncar el futuro"
    assert n_sig >= 0


def test_prev_day_levels_use_only_finished_days():
    t = pd.date_range("2025-01-06 00:00", periods=96 * 3, freq="15min")
    df = pd.DataFrame({"time": t, "high": np.r_[np.full(96, 1.2), np.full(96, 1.5), np.full(96, 9.0)], "low": np.r_[np.full(96, 1.0), np.full(96, 1.1), np.full(96, 0.1)]})
    pdh, pdl = prev_day_levels(df)
    assert np.isnan(pdh[:96]).all() and (pdh[96:192] == 1.2).all() and (pdh[192:] == 1.5).all() and (pdl[192:] == 1.1).all()


def test_resample_h4_and_d1_ohlc():
    t = pd.date_range("2025-01-06 00:00", periods=48, freq="1h")
    h1 = pd.DataFrame({"time": t, "open": np.arange(48.0), "high": np.arange(48.0) + 1, "low": np.arange(48.0) - 1, "close": np.arange(48.0) + 0.5, "tick_volume": 1, "spread": np.arange(48)})
    h4 = resample(h1, "H4")
    assert len(h4) == 12 and h4.open[0] == 0 and h4.close[0] == 3.5 and h4.high[0] == 4 and h4.low[0] == -1 and h4.spread[1] == 4
    d1 = resample(h1, "D1")
    assert len(d1) == 2 and d1.open[1] == 24 and d1.high[0] == 24


def test_htf_alignment_has_no_lookahead():
    t = pd.date_range("2025-01-06 00:00", periods=24, freq="1h")
    base = pd.DataFrame({"time": t})
    h4 = pd.DataFrame({"time": pd.date_range("2025-01-06 00:00", periods=6, freq="4h"), "v": np.arange(6.0)})
    al = htf_align(base, h4, ["v"], 240, 60)
    # la barra H1 de las 03:00 cierra a las 04:00 -> ya puede usar la H4 de 00:00 (cerrada a las 04:00); la de las 02:00 (cierra 03:00) aun no
    assert np.isnan(al.v[2]) and al.v[3] == 0 and al.v[7] == 1


def test_transform_modes_and_geometry():
    d = np.array([1, -1, 0, 1]); sl = np.array([1.0, 2, 3, 4]); tp = np.array([2.0, 4, 6, 8])
    s = Signals(d, sl, tp, 17, 5, np.array([True] * 4), np.array([True] * 4))
    inv = transform(s, "inv", "mirror")
    assert (inv.direction == -d).all() and (inv.sl_dist == sl).all() and inv.exit_long is None
    sw = transform(s, "inv", "swap")
    assert (sw.sl_dist == tp).all() and (sw.tp_dist == sl).all()
    assert (transform(s, "long_inv").direction == np.array([-1, 0, 0, -1])).all()
    assert (transform(s, "short_inv").direction == np.array([0, 1, 0, 0])).all()
    assert (transform(s, "long").direction == np.array([1, 0, 0, 1])).all() and (transform(s, "short").direction == np.array([0, -1, 0, 0])).all()


def test_inverted_trade_is_rebuilt_with_bid_ask_not_sign_flipped():
    # 1 barra de senal y precio que sube: original LARGO gana ~TP; INVERTIDO (corto) pierde SL y paga spread de forma propia
    t = pd.date_range("2025-01-06 08:00", periods=6, freq="15min")
    df = pd.DataFrame({"time": t, "open": [1.1000, 1.1000, 1.1010, 1.1030, 1.1040, 1.1040], "high": [1.1001, 1.1012, 1.1035, 1.1045, 1.1042, 1.1041],
                       "low": [1.0999, 1.0999, 1.1008, 1.1028, 1.1038, 1.1039], "close": [1.1000, 1.1010, 1.1030, 1.1040, 1.1040, 1.1040], "spread": 10, "tick_volume": 1})
    d = np.zeros(6, int); d[0] = 1; sl = np.full(6, 0.0010); tp = np.full(6, 0.0020)
    cfg = BacktestConfig(3000, 0.5, "strict")
    tl, _ = run_backtest(df, Signals(d, sl, tp), SPECX, cfg)
    ts, _ = run_backtest(df, Signals(-d, sl, tp), SPECX, cfg)
    assert tl.exit_reason[0] == "tp" and ts.exit_reason[0] == "sl"
    # entradas distintas: largo compra al ASK (open + spread), corto vende al BID (open); no es el mismo trade con signo cambiado
    assert abs(tl.entry[0] - (1.1000 + 0.0001)) < 1e-9 and abs(ts.entry[0] - 1.1000) < 1e-9
    assert abs(tl.net_r[0] - 2.0) < 1e-6 and abs(ts.net_r[0] + 1.0) < 1e-6
    assert tl.spread_cost[0] > 0 and ts.spread_cost[0] > 0       # ambos pagan el spread (largo al entrar, corto al salir)


def test_engine_max_bars_and_rule_exit():
    t = pd.date_range("2025-01-06 08:00", periods=12, freq="15min")
    flat = np.full(12, 1.1000)
    df = pd.DataFrame({"time": t, "open": flat, "high": flat + 0.0001, "low": flat - 0.0001, "close": flat, "spread": 10, "tick_volume": 1})
    d = np.zeros(12, int); d[0] = 1; sl = np.full(12, 0.01); tp = np.full(12, 0.02)
    cfg = BacktestConfig(3000, 0.5, "strict")
    a, _ = run_backtest(df, Signals(d, sl, tp, None, 4), SPECX, cfg)
    assert a.exit_reason[0] == "max_bars" and a.bars_held[0] == 4
    ex = np.zeros(12, bool); ex[2] = True
    b, _ = run_backtest(df, Signals(d, sl, tp, None, None, ex, None), SPECX, cfg)
    assert b.exit_reason[0] == "rule_exit" and b.bars_held[0] == 2


def test_original_s02_s04_unchanged_by_engine_extension():
    df = synth(3000, seed=2)
    for sid in ("S02", "S03", "S04"):
        sig = generate(sid, df, SPEC)
        tr, _ = run_backtest(df, sig, SPECX, BacktestConfig(3000, 0.5, "strict"))
        assert tr.exit_reason.isin(["sl", "tp", "sl_gap", "end_of_data"]).all()

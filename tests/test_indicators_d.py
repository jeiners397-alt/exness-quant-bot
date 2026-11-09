import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from remix_lab import indicators as ind  # noqa: E402
from tests.test_lookahead import synth  # noqa: E402


def test_rsi_bounds_extremes_and_recursion():
    up = pd.Series(np.arange(1, 40, dtype=float)); dn = up[::-1].reset_index(drop=True)
    assert ind.rsi(up, 2).dropna().iloc[-1] == 100.0
    assert abs(ind.rsi(dn, 2).dropna().iloc[-1]) < 1e-9
    c = synth(500).close
    r = ind.rsi(c, 14).dropna()
    assert (r >= 0).all() and (r <= 100).all()
    # recursion independiente de Wilder (semilla = primer valor, igual que el EMA del laboratorio)
    d = c.diff().to_numpy(); au = ad = 0.0; out = []
    for i in range(1, len(c)):
        u, w = max(d[i], 0), max(-d[i], 0)
        au = u if i == 1 else (au * 13 + u) / 14; ad = w if i == 1 else (ad * 13 + w) / 14
        out.append(100 - 100 / (1 + au / ad) if ad else 100.0)
    assert np.allclose(ind.rsi(c, 14).to_numpy()[20:], np.array(out)[19:], atol=1e-6)


def test_zscore_manual():
    c = pd.Series([1.0, 2, 3, 4, 10])
    z = ind.zscore(c, 5).iloc[-1]
    assert abs(z - (10 - c.mean()) / c.std(ddof=0)) < 1e-12


def test_ker_trend_vs_noise():
    trend = pd.Series(np.arange(50, dtype=float))
    zig = pd.Series([0.0, 1.0] * 25)
    assert abs(ind.ker(trend, 10).iloc[-1] - 1.0) < 1e-12
    assert ind.ker(zig, 10).iloc[-1] < 0.2


def test_choppiness_trend_low_range_high():
    n = 120
    t = np.arange(n, dtype=float)
    tr = pd.DataFrame({"high": t + 0.5, "low": t - 0.5, "close": t})
    rg = pd.DataFrame({"high": 1.5 + 0 * t, "low": 0.5 + 0 * t, "close": 1.0 + 0 * t})
    rg.loc[::2, "high"] = 2.0
    assert ind.choppiness(tr, 14).iloc[-1] < 38.2
    assert ind.choppiness(rg, 14).iloc[-1] > 61.8


def test_linreg_slope_exact():
    c = pd.Series(3.0 + 0.25 * np.arange(40))
    assert abs(ind.linreg_slope(c, 20).iloc[-1] - 0.25) < 1e-12


def test_vol_percentile_bounds_and_extreme():
    df = synth(800)
    p = ind.vol_percentile(df, 14, 200).dropna()
    assert (p > 0).all() and (p <= 1).all()


def test_hurst_orders_persistent_above_antipersistent():
    rng = np.random.default_rng(1)
    e = rng.normal(0, 1, 3000)
    def ar(phi):
        x = np.zeros(len(e))
        for i in range(1, len(e)):
            x[i] = phi * x[i - 1] + e[i]
        return pd.Series(100 + np.cumsum(x * 0.001))
    hp = ind.hurst_rs(ar(0.6), 128).dropna().mean()
    ha = ind.hurst_rs(ar(-0.6), 128).dropna().mean()
    assert hp > ha + 0.1


def test_vwap_proxy_manual_and_session_reset():
    t = pd.to_datetime(["2025-01-06 00:00", "2025-01-06 00:15", "2025-01-07 00:00"])
    df = pd.DataFrame({"time": t, "high": [2.0, 4.0, 5.0], "low": [0.0, 2.0, 5.0], "close": [1.0, 3.0, 5.0], "tick_volume": [10, 30, 7]})
    v = ind.session_vwap_proxy(df, 0)
    assert abs(v.iloc[0] - 1.0) < 1e-12 and abs(v.iloc[1] - (1 * 10 + 3 * 30) / 40) < 1e-12 and abs(v.iloc[2] - 5.0) < 1e-12


def test_all_new_indicators_are_causal():
    df = synth(1500)
    cut = 900
    for f in (lambda d: ind.rsi(d.close, 2), lambda d: ind.zscore(d.close, 50), lambda d: ind.ker(d.close, 10), lambda d: ind.choppiness(d, 14),
              lambda d: ind.linreg_slope(d.close, 20), lambda d: ind.vol_percentile(d, 14, 200), lambda d: ind.bb_width(d.close), lambda d: ind.session_vwap_proxy(d, 0)):
        a = f(df).iloc[:cut].to_numpy(); b = f(df.iloc[:cut]).to_numpy()
        assert np.allclose(a, b, equal_nan=True)

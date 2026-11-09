import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from remix_lab import indicators as ind, strategies as st  # noqa: E402
from remix_lab.backtest import BacktestConfig, compute_lots, run_backtest  # noqa: E402
from remix_lab.metrics import compute_metrics  # noqa: E402
from remix_lab.montecarlo import monte_carlo  # noqa: E402
from remix_lab.optimization import guard_in_sample  # noqa: E402
from remix_lab.experiments import HoldoutViolation  # noqa: E402
from remix_lab import load_config  # noqa: E402

SPEC = dict(symbol="T", point=0.00001, value_per_price_unit_per_lot=100000.0, volume_min=0.01, volume_step=0.01,
            volume_max=200.0, swap_mode=1, swap_long=-5.0, swap_short=0.0)


def synth(n=3000, seed=1, tf_min=15):
    rng = np.random.default_rng(seed)
    t = pd.date_range("2025-01-06", periods=n, freq=f"{tf_min}min")
    c = 1.10 + np.cumsum(rng.normal(0, 0.0004, n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.uniform(0, 0.0003, n)
    l = np.minimum(o, c) - rng.uniform(0, 0.0003, n)
    return pd.DataFrame(dict(time=t, open=o, high=h, low=l, close=c, tick_volume=1, spread=8, real_volume=0))


# ---------------- indicadores
def test_sma_ema_atr_known_values():
    s = pd.Series([1.0, 2, 3, 4, 5])
    assert ind.sma(s, 3).iloc[-1] == pytest.approx(4.0)
    e = ind.ema(pd.Series([1.0] * 10 + [2.0]), 3)
    assert e.iloc[-1] == pytest.approx(1.5)           # alpha=0.5
    df = pd.DataFrame(dict(high=[2, 3, 4.0], low=[1, 1.5, 3.0], close=[1.5, 2.5, 3.5]))
    assert ind.atr(df, 2).iloc[-1] == pytest.approx((1.5 + 1.5) / 2)   # TR = [1, 1.5, 1.5]


def test_bollinger_population_std():
    s = pd.Series([1.0, 2, 3, 4, 5])
    mid, up, lo = ind.bollinger(s, 5, 2.0)
    assert mid.iloc[-1] == 3.0 and up.iloc[-1] == pytest.approx(3 + 2 * np.sqrt(2))


def test_donchian_excludes_current_bar():
    df = pd.DataFrame(dict(high=[1, 2, 3, 10.0], low=[0, 0, 0, 0.0]))
    hh, _ = ind.donchian_prev(df, 3)
    assert hh.iloc[-1] == 3.0   # no incluye el 10 de la barra actual


# ---------------- sin look-ahead
@pytest.mark.parametrize("sid", ["S01", "S02", "S03", "S04"])
def test_no_lookahead_signals(sid):
    df = synth(3000)
    full = st.generate(sid, df, SPEC)
    cut = 2200
    part = st.generate(sid, df.iloc[:cut].reset_index(drop=True), SPEC)
    assert np.array_equal(full.direction[:cut - 1], part.direction[:cut - 1])
    a, b = full.sl_dist[:cut - 1], part.sl_dist[:cut - 1]
    assert np.allclose(a, b, equal_nan=True)


def test_s01_rule_hand_case():
    # un dia: rango asiatico 1.1000-1.1010, ruptura alcista a las 07:00
    t = pd.date_range("2025-01-07 00:00", "2025-01-07 12:00", freq="1h")
    n = len(t)
    df = pd.DataFrame(dict(time=t, open=1.1005, high=1.1010, low=1.1000, close=1.1005, tick_volume=1, spread=1, real_volume=0))
    df.loc[7, ["high", "close"]] = [1.1030, 1.1025]      # 07:00 cierra > RangeHigh
    s = st.generate("S01", df, SPEC)
    assert s.direction[7] == 1 and np.count_nonzero(s.direction) == 1
    assert s.sl_dist[7] == pytest.approx(0.0010)
    assert s.tp_dist[7] == pytest.approx(0.0015)


# ---------------- backtest / costes / sizing
def test_lots_strict_vs_minlot():
    lots, rp, rr, why = compute_lots(100, 0.5, 0.0020, SPEC, "strict")   # 20 pips; riesgo 0.5$ ; 0.01 lote = 2$
    assert why == "lote_minimo_excede_riesgo" and lots == 0
    lots, _, rr, why = compute_lots(100, 0.5, 0.0020, SPEC, "min_lot")
    assert lots == 0.01 and rr == pytest.approx(2.0) and why is None
    lots, *_ = compute_lots(10000, 0.5, 0.0020, SPEC, "strict")          # 50$ / 200$ por lote = 0.25
    assert lots == pytest.approx(0.25)


def test_backtest_tp_and_spread_cost():
    t = pd.date_range("2025-01-07 08:00", periods=4, freq="15min")
    df = pd.DataFrame(dict(time=t, open=[1.1, 1.1, 1.1, 1.1], high=[1.1, 1.1020, 1.1, 1.1], low=[1.1, 1.0995, 1.1, 1.1],
                           close=1.1, tick_volume=1, spread=10, real_volume=0))
    sig = st.Signals(np.array([1, 0, 0, 0]), np.full(4, 0.0010), np.full(4, 0.0015))
    tr, info = run_backtest(df, sig, SPEC, BacktestConfig(sizing_policy="ideal", use_swap=False))
    assert len(tr) == 1
    r = tr.iloc[0]
    assert r.entry == pytest.approx(1.1 + 0.0001)            # ask = open + 10 puntos
    assert r.exit_reason == "tp" and r.exit == pytest.approx(r.entry + 0.0015)
    assert r.net_r == pytest.approx(1.5)
    assert r.spread_cost > 0


def test_backtest_sl_first_when_both_hit():
    t = pd.date_range("2025-01-07 08:00", periods=3, freq="15min")
    df = pd.DataFrame(dict(time=t, open=1.1, high=[1.1, 1.1100, 1.1], low=[1.1, 1.0900, 1.1], close=1.1,
                           tick_volume=1, spread=0, real_volume=0))
    sig = st.Signals(np.array([1, 0, 0]), np.full(3, 0.001), np.full(3, 0.001))
    tr, _ = run_backtest(df, sig, SPEC, BacktestConfig(sizing_policy="ideal", use_swap=False))
    assert tr.iloc[0].exit_reason == "sl" and tr.iloc[0].net_r == pytest.approx(-1.0)


def test_short_pays_spread_on_exit():
    t = pd.date_range("2025-01-07 08:00", periods=3, freq="15min")
    df = pd.DataFrame(dict(time=t, open=1.1, high=[1.1, 1.1, 1.1], low=[1.1, 1.0980, 1.1], close=1.1,
                           tick_volume=1, spread=10, real_volume=0))
    sig = st.Signals(np.array([-1, 0, 0]), np.full(3, 0.0010), np.full(3, 0.0010))
    tr, _ = run_backtest(df, sig, SPEC, BacktestConfig(sizing_policy="ideal", use_swap=False))
    r = tr.iloc[0]
    assert r.entry == pytest.approx(1.1) and r.exit_reason == "tp"   # ask_low = 1.0981 <= tp 1.0990


def test_swap_triple_wednesday():
    from remix_lab.backtest import _swap_nights
    assert _swap_nights(pd.Timestamp("2025-01-08 10:00"), pd.Timestamp("2025-01-09 10:00")) == 3   # mie->jue
    # CORREGIDO (Fase paridad): el Tester cobra 1x la noche vie->sab y 0 sab/dom (evidencia: swap -0.11 en 2025-11-21 vie 16:00 -> lun)
    assert _swap_nights(pd.Timestamp("2025-01-10 10:00"), pd.Timestamp("2025-01-13 10:00")) == 1   # vie->lun
    assert _swap_nights(pd.Timestamp("2025-01-02 16:00"), pd.Timestamp("2025-01-05 22:06")) == 2   # jue 16:00 -> dom 22:06 (MT5: 2 noches, swap -0.22 con 0.02 lotes)
    assert _swap_nights(pd.Timestamp("2025-11-04 20:00"), pd.Timestamp("2025-11-07 20:00")) == 5   # mar,mie x3,jue (MT5: -0.84 con 0.03 lotes)


# ---------------- metricas / MC / holdout
def test_metrics_profit_factor_and_dd():
    tr = pd.DataFrame(dict(net_money=[2.0, -1.0, 3.0, -2.0], net_r=[2, -1, 3, -2.0], balance=[102, 101, 104, 102.0],
                           exit_time=pd.date_range("2025-01-01", periods=4, freq="D"), spread_cost=0.1, commission=0.0,
                           swap=0.0, slippage_cost=0.0, risk_real_pct=0.5))
    m = compute_metrics(tr, 100.0)
    assert m["profit_factor"] == pytest.approx(5 / 3) and m["win_rate"] == 50.0
    assert m["max_dd_money"] == pytest.approx(2.0) and m["expectancy_r"] == pytest.approx(0.5)


def test_montecarlo_reproducible_and_sane():
    r = np.r_[np.full(60, 1.0), np.full(40, -1.0)]
    a, b = monte_carlo(r, n_sims=500, seed=1), monte_carlo(r, n_sims=500, seed=1)
    assert a == b and a["return_pct_p50"] > 0 and a["prob_loss_pct"] < 50


def test_holdout_guard_blocks_future_data():
    cfg = load_config()
    df = pd.DataFrame(dict(time=pd.to_datetime(["2026-06-30 12:00", "2026-07-02 00:00"])))
    with pytest.raises(HoldoutViolation):
        guard_in_sample(df, cfg)
    guard_in_sample(df.iloc[:1], cfg)


# ---------------- seguridad estatica
def test_python_never_sends_orders():
    for p in list((ROOT / "remix_lab").glob("*.py")) + list((ROOT / "scripts").glob("*.py")):
        code = re.sub(r'"""[\s\S]*?"""|#.*', "", p.read_text(encoding="utf-8"))
        assert "order_send" not in code, p
        assert "password" not in code.lower() or "mt5.login" not in code, p


def test_ea_tester_guard_present():
    src = (ROOT / "mql5" / "REMIX_STRATEGY_RESEARCH_LAB_V1.mq5").read_text(encoding="utf-8")
    assert src.count("MQLInfoInteger(MQL_TESTER)") >= 2           # OnInit y antes de operar
    assert "INIT_FAILED" in src
    # toda llamada de trading debe estar en funciones protegidas por IsTesterEnvironment()
    for call in ("trade.Buy(", "trade.Sell(", "trade.PositionClose("):
        for m in re.finditer(re.escape(call), src):
            pre = src[max(0, m.start() - 1500):m.start()]
            assert "TradingAllowed()" in pre or "IsTesterEnvironment()" in pre, call

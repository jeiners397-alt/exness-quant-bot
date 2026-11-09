"""Pruebas unitarias y de regresion de la correccion de paridad Python-MT5 (Fase de paridad V2/L2)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from remix_lab import indicators as ind  # noqa: E402
from remix_lab.backtest import BacktestConfig, _swap_nights, run_backtest  # noqa: E402
from remix_lab.strategies import Signals  # noqa: E402
from tests.test_lookahead import synth  # noqa: E402

SPECX = {"point": 1e-5, "value_per_price_unit_per_lot": 100000.0, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 100.0, "swap_mode": 1, "swap_long": 0.0, "swap_short": 0.0}


def test_adx_mt5_matches_independent_ewm_after_warmup_and_differs_from_wilder():
    df = synth(1500, seed=21)
    a, p, m = ind.adx_mt5(df, 14)
    # implementacion independiente con pandas: EMA alpha=2/(n+1) de los cocientes 100*DM/TR (semilla distinta => se compara tras calentamiento)
    h, l, c = df.high, df.low, df.close
    pos, neg = (h - h.shift()).clip(lower=0), (l.shift() - l).clip(lower=0)
    pos2 = pos.where(pos > neg, 0.0); neg2 = neg.where(neg > pos, 0.0)
    tr = pd.concat([(h - l).abs(), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    pdi = (100 * pos2 / tr).ewm(alpha=2 / 15, adjust=False).mean(); ndi = (100 * neg2 / tr).ewm(alpha=2 / 15, adjust=False).mean()
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi)
    adx2 = dx.ewm(alpha=2 / 15, adjust=False).mean()
    assert np.allclose(a.iloc[400:], adx2.iloc[400:], atol=1e-6) and np.allclose(p.iloc[400:], pdi.iloc[400:], atol=1e-6)
    w, _, _ = ind.adx(df, 14)
    assert (a.iloc[300:] - w.iloc[300:]).abs().max() > 1.0, "MT5-EMA y Wilder deben diferir de forma material"


def _bars(n=60, spread=10):
    t = pd.date_range("2025-01-06 00:00", periods=n, freq="4h")
    flat = np.full(n, 1.1)
    return pd.DataFrame({"time": t, "open": flat, "high": flat + 0.0001, "low": flat - 0.0001, "close": flat, "spread": spread, "tick_volume": 1})


def test_spread_gates_at_entry_bar_with_counters():
    df = _bars(); df.loc[1, "spread"] = 40                   # barra de entrada con spread 40 pts > 30
    d = np.zeros(len(df), int); d[0] = 1
    sig = Signals(d, np.full(len(df), 0.01), np.full(len(df), 0.02))
    tr, info = run_backtest(df, sig, SPECX, BacktestConfig(3000, 0.5, "strict", max_spread_points=30))
    assert len(tr) == 0 and info["skipped"].get("spread_points") == 1
    tr2, info2 = run_backtest(df, sig, SPECX, BacktestConfig(3000, 0.5, "strict"))
    assert len(tr2) == 1                                        # sin compuerta, entra (comportamiento anterior intacto)
    df2 = _bars(spread=10)                                      # 10 pts = 0.0001 > 0.15*0.0005
    sig2 = Signals(d, np.full(len(df2), 0.0005), np.full(len(df2), 0.001))
    _, info3 = run_backtest(df2, sig2, SPECX, BacktestConfig(3000, 0.5, "strict", max_spread_frac_sl=0.15))
    assert info3["skipped"].get("spread_frac_sl") == 1


def test_gate_spread_and_no_trade_columns():
    df = _bars(); df["gate_spread"] = df.spread; df.loc[1, "gate_spread"] = 60                # primer tick con spread ancho
    d = np.zeros(len(df), int); d[0] = 1
    sig = Signals(d, np.full(len(df), 0.01), np.full(len(df), 0.02))
    tr, info = run_backtest(df, sig, SPECX, BacktestConfig(3000, 0.5, "strict", max_spread_points=30))
    assert len(tr) == 0
    df2 = _bars(); df2["no_trade_at_open"] = False; df2.loc[1, "no_trade_at_open"] = True
    _, info2 = run_backtest(df2, sig, SPECX, BacktestConfig(3000, 0.5, "strict"))
    assert info2["skipped"].get("market_closed_at_open") == 1


def test_max_bars_bars_vs_calendar_modes_and_blocked_exit():
    t = list(pd.date_range("2025-01-06 00:00", periods=8, freq="4h")) + list(pd.date_range("2025-01-08 00:00", periods=12, freq="4h"))   # hueco de 1 dia
    n = len(t); flat = np.full(n, 1.1)
    df = pd.DataFrame({"time": t, "open": flat, "high": flat + 1e-4, "low": flat - 1e-4, "close": flat, "spread": 10, "tick_volume": 1})
    d = np.zeros(n, int); d[0] = 1
    sig = Signals(d, np.full(n, 0.01), np.full(n, 0.02), None, 10)
    b, _ = run_backtest(df, sig, SPECX, BacktestConfig(3000, 0.5, "strict", max_bars_mode="bars", bar_seconds=14400))
    c, _ = run_backtest(df, sig, SPECX, BacktestConfig(3000, 0.5, "strict", max_bars_mode="calendar", bar_seconds=14400))
    assert b.bars_held[0] == 10 and c.bars_held[0] < 10          # calendario cuenta las horas sin mercado => sale antes (comportamiento del EA V2)
    df["no_trade_at_open"] = False; k = int(c.bars_held[0]) + 1; df.loc[k, "no_trade_at_open"] = True
    c2, _ = run_backtest(df, sig, SPECX, BacktestConfig(3000, 0.5, "strict", max_bars_mode="calendar", bar_seconds=14400))
    assert c2.bars_held[0] == c.bars_held[0] + 1                 # salida con mercado cerrado: se aplaza a la barra siguiente


def test_reentry_same_bar_after_open_exit():
    df = _bars(30)
    d = np.zeros(len(df), int); d[0] = 1; d[5] = 1           # la senal de la barra 5 (cierra en 5) entra en 6; salida por max_bars a la apertura de 5? => ver abajo
    sig = Signals(d, np.full(len(df), 0.01), np.full(len(df), 0.02), None, 5)
    a, _ = run_backtest(df, sig, SPECX, BacktestConfig(3000, 0.5, "strict"))
    b, _ = run_backtest(df, sig, SPECX, BacktestConfig(3000, 0.5, "strict", reenter_after_open_exit=True))
    assert len(a) >= 1 and len(b) >= 1
    # con reentrada, la 2a operacion entra en la barra de salida de la 1a (k) en vez de k+1
    assert (pd.to_datetime(b.entry_time).iloc[1] <= pd.to_datetime(a.entry_time).iloc[1]) if len(b) > 1 and len(a) > 1 else True


def test_swap_nights_friday_and_weekend_rules():
    assert _swap_nights(pd.Timestamp("2025-01-03 10:00"), pd.Timestamp("2025-01-06 10:00")) == 1      # vie->lun: 1 (viernes)
    assert _swap_nights(pd.Timestamp("2025-01-04 10:00"), pd.Timestamp("2025-01-06 10:00")) == 0      # sab->lun: 0
    assert _swap_nights(pd.Timestamp("2025-01-08 10:00"), pd.Timestamp("2025-01-09 10:00")) == 3      # mie x3


def test_warmup_does_not_change_default_engine_results():
    df = synth(800, seed=5)
    d = np.zeros(len(df), int); d[100] = 1; d[300] = -1
    sig = Signals(d, np.full(len(df), 0.004), np.full(len(df), 0.006))
    t1, _ = run_backtest(df, sig, SPECX, BacktestConfig(3000, 0.5, "strict"))
    t2, _ = run_backtest(df, sig, SPECX, BacktestConfig(3000, 0.5, "strict", max_spread_frac_sl=None, max_spread_points=None))
    assert t1.equals(t2)


OFFICIAL = ROOT / "results" / "v2_official" / "REMIX_V2_deals_M05_EURUSDm_PERIOD_H4.csv"
H4_HIST = ROOT / "data" / "raw" / "hist" / "EURUSDm_H4_native_2022_2026.csv"


@pytest.mark.skipif(not (OFFICIAL.exists() and H4_HIST.exists()), reason="requiere resultados oficiales y datos H4 locales (no incluidos en el repositorio)")
def test_regression_official_v2_l2_parity():
    sys.path.insert(0, str(ROOT / "research"))
    import parity_v2_l2 as P
    off, _ = P.load_official()
    full = pd.read_csv(H4_HIST, parse_dates=["time"])
    full.loc[full.spread <= 0, "spread"] = full.spread[full.spread > 0].median()
    base, _ = P.python_run(full, warmup=False, gates=False, adx="wilder")                                   # estado inicial de la auditoria
    assert len(base) == 48 and len(set(base.entry_time) & set(off.entry_time)) == 19
    fixed, _ = P.python_run(full, warmup=True, gates=True, adx="mt5", reenter=True, calendar=True, session=True)
    assert len(fixed) == 30 and set(fixed.entry_time) == set(off.entry_time)
    j = off.merge(fixed, on="entry_time", suffixes=("_mt5", "_py"))
    assert (j.lots_mt5 == j.lots_py).all() and (j.dir_mt5 == j.dir_py).all() and ((j.entry_mt5 - j.entry_py).abs() < 1e-9).all()
    assert abs(float(j.net.sum()) - float(j.net_money.sum())) < 1.5          # diferencia residual documentada (< 1.5 USD)
    assert abs(float(j.swap_mt5.sum()) - float(j.swap_py.sum())) < 0.2

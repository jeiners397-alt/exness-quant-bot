"""Pruebas V8: paridad Python-MT5, ausencia de clase A, coherencia del registro, seguridad del EA, reserva prospectiva intacta, formula de salidas."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "research"


def test_deliverables_exist():
    for f in ["V8_XAU_H1_PARITY.csv", "V8_XAU_H1_OFFICIAL_RESULTS.csv", "V8_H4_D1_EVENT_STUDY.csv", "V8_MARKET_REGIMES.csv", "V8_ENTRY_ANALYSIS.csv", "V8_EXIT_ANALYSIS.csv", "V8_TRANSACTION_COSTS.csv",
              "V8_STRATEGY_CANDIDATES.csv", "V8_FORWARD_RESULTS.csv", "V8_ROBUSTNESS_RESULTS.csv", "V8_EXPERIMENT_REGISTER.csv", "V8_DAILY_PROFITABILITY.csv"]:
        assert (R / f).exists() and (R / f).stat().st_size > 100, f


def test_parity_python_mt5_high_overlap_and_direction():
    P = pd.read_csv(R / "V8_XAU_H1_PARITY.csv")
    assert (P.signal_overlap_pct >= 95).all()
    assert (P.direction_agree_pct == 100).all()
    assert (P.exit_reason_agree_pct >= 97).all()


def test_no_class_A_and_multiplicity_consistent():
    Rb = pd.read_csv(R / "V8_ROBUSTNESS_RESULTS.csv")
    assert "A" not in set(Rb["class"])                            # no hay datos independientes
    N = int(Rb.N_tests.iloc[0])
    assert N == len(Rb)
    assert abs(Rb.t_star_multiplicity.iloc[0] - math.sqrt(2 * math.log(N))) < 0.01
    B = Rb[Rb["class"] == "B"]
    assert (B.t_is >= Rb.t_star_multiplicity.iloc[0]).all()       # si hubiera B, cumplen la correccion


def test_register_counts_cumulative():
    G = pd.read_csv(R / "V8_EXPERIMENT_REGISTER.csv")
    n_v8 = int((G.tipo != "backtest_oficial_MT5").sum())
    assert G.N_tests_V8.iloc[0] == n_v8
    assert G.N_tests_acumulado_V7_V8.iloc[0] == 2200 + n_v8
    assert (G.tipo == "backtest_oficial_MT5").sum() >= 9


def test_official_runs_no_claim_of_validation():
    O = pd.read_csv(R / "V8_XAU_H1_OFFICIAL_RESULTS.csv")
    assert (O.capital == 3000).all()
    assert O.period.str.endswith("2026-10-31").all()              # la reserva (>= 2026-11-01) no se usa
    assert (O.history_quality_pct[O.model.str.contains("reales")] < 50).all()   # ticks reales NO disponibles de forma completa


def test_ea_is_tester_only_and_has_no_martingale():
    src = (ROOT / "mql5" / "REMIX_V8_XAU_BREAKOUT.mq5").read_text(encoding="utf-8")
    assert "MQL_TESTER" in src and "ACCOUNT_TRADE_MODE_REAL" in src
    low = src.lower()
    assert "martingal" not in low.replace("sin martingala", "")
    assert "lot *= " not in low and "lot = lot *" not in low


def test_no_order_send_in_python_research():
    for f in R.glob("v8_*.py"):
        assert "order_send" not in f.read_text(encoding="utf-8"), f


def test_exit_R_formula_uses_risk_units():
    from research.v8_tables import sim_one
    n = 200
    t = pd.date_range("2025-01-01", periods=n, freq="h")
    c = np.full(n, 100.0); d = pd.DataFrame(dict(time=t, open=c, high=c + 0.5, low=c - 0.5, close=c, atr=np.full(n, 1.0), spr=np.zeros(n)))
    d.loc[11:, "high"] = 110.0                                    # TP alcanzado en la vela siguiente; SL no
    r = sim_one(d, 10, 1, "next_open", "SL1.5_TP3")               # SL 1.5 ATR, TP 3 ATR => 2R
    assert abs(r - 2.0) < 1e-9
    r = sim_one(d, 10, 1, "next_open", "TP3")                     # SL 1 ATR, TP 3 ATR => 3R
    assert abs(r - 3.0) < 1e-9


def test_holdout_untouched_in_event_data():
    from research import v8_htf_event_study as H
    for tf in ("H4", "D1"):
        d = H.load_htf("XAUUSDm", tf)
        assert d.time.max() < pd.Timestamp("2026-11-01")

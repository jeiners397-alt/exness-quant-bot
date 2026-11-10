"""Pruebas V9: preservacion de XAU H4, datos M1/M5 sin reserva prospectiva, clases, paridad, seguridad."""
from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "research"


def test_deliverables_exist():
    for f in ["V9_XAUUSD_MICROSTRUCTURE.csv", "V9_XAUUSD_SESSION_PROFILE.csv", "V9_XAUUSD_SPREAD_ANALYSIS.csv", "V9_ENTRY_PROBABILITIES.csv", "V9_MOMENTUM_ANALYSIS.csv", "V9_RANGE_SCALPING.csv",
              "V9_LIQUIDITY_SWEEPS.csv", "V9_BASKET_TRADING.csv", "V9_HEDGING_ANALYSIS.csv", "V9_STRATEGY_CANDIDATES.csv", "V9_MT5_OFFICIAL_RESULTS.csv", "V9_DAILY_PROFITABILITY.csv", "V9_ROBUSTNESS_RESULTS.csv",
              "V9_EXPERIMENT_REGISTER.csv", "V9_XAU_H4_BASELINE.csv", "V9_TICK_AVAILABILITY.csv"]:
        assert (R / f).exists() and (R / f).stat().st_size > 50, f


def test_xau_h4_baseline_frozen_and_unchanged():
    r = subprocess.run([sys.executable, "-m", "research.v9_preserve", "--verify"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    B = pd.read_csv(R / "V9_XAU_H4_BASELINE.csv")
    h4 = B[B.config.str.startswith("H4")]
    assert set(h4.p_Lookback) == {20} and set(h4.p_CooldownBars) == {6} and set(h4.p_SL_ATR) == {1.0}
    assert sorted(h4.net_profit) == [1622.79, 2172.77]


def test_scalping_data_excludes_holdout_and_is_complete():
    for tf, n in (("M1", 900000), ("M5", 190000)):
        d = pd.read_csv(ROOT / "data" / "raw" / "v9" / f"XAUUSDm_{tf}.csv", usecols=["time"], parse_dates=["time"])
        assert d.time.max() < pd.Timestamp("2026-11-01") and d.time.min() < pd.Timestamp("2024-01-05") and len(d) > n


def test_no_class_A_B_without_evidence_and_multiplicity_consistent():
    Rb = pd.read_csv(R / "V9_ROBUSTNESS_RESULTS.csv")
    N = int(Rb.N_tests.iloc[0]); assert N == len(Rb)
    assert abs(Rb.t_star.iloc[0] - math.sqrt(2 * math.log(N))) < 0.01
    ab = Rb[Rb["class"].isin(["A", "B"])]
    assert (ab.t_DEV >= Rb.t_star.iloc[0]).all() and (ab.expR_SEL > 0).all()
    A = Rb[Rb["class"] == "A"]
    assert (A.expR_VAL > 0).all() and (A.n_VAL >= 100).all()


def test_split_protocol_declared_and_non_overlapping():
    from research import v9_scalp_study as S
    spans = sorted(S.SPL.values())
    for (a1, b1), (a2, b2) in zip(spans, spans[1:]):
        assert b1 <= a2
    assert S.SPL["VAL"][1] == "2026-11-01"


def test_m5_parity():
    P = pd.read_csv(R / "V9_M5_PARITY.csv")
    assert P.signal_overlap_pct.iloc[0] >= 95 and P.direction_agree_pct.iloc[0] == 100


def test_no_order_send_and_cooldown_isolation():
    for f in R.glob("v9_*.py"):
        assert "order_send" not in f.read_text(encoding="utf-8"), f
    t = (ROOT / "research" / "v9_basket.py").read_text(encoding="utf-8")
    assert "V.COOL = 6" in t            # leccion V9: el enfriamiento de la baseline H4 se fija explicitamente


def test_basket_policies_use_no_martingale():
    t = (ROOT / "research" / "v9_basket.py").read_text(encoding="utf-8").lower()
    assert "martingal" in t and "lot_usd * " not in t.replace("lot_usd * 1", "")
    B = pd.read_csv(R / "V9_BASKET_TRADING.csv")
    assert {"individual", "cesta_sin_SL", "cesta_con_SL"} <= set(B.policy)
    assert "max_equity_dd_pct_incl_floating" in B.columns and "worst_floating_usd" in B.columns   # las perdidas flotantes no se ocultan

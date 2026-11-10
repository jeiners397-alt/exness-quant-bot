"""Pruebas de V10: entregables, integridad de la baseline congelada, calendario macro/horario de verano, reserva prospectiva intacta, coherencia del registro, motor de simulacion."""
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "research"; DOCS = ROOT / "docs"
CSV = ["XAU_H4_AUDIT", "XAU_H4_DIRECTIONAL_ANALYSIS", "XAU_H4_BENCHMARKS", "MOMENTUM_RESEARCH", "MACRO_EVENTS", "MACRO_DATA_PROVENANCE", "ECONOMIC_REGIMES", "VOLATILITY_REGIMES", "XAU_M15_EVENTS",
       "STRATEGY_CANDIDATES", "OFFICIAL_MT5_RESULTS", "EXPERIMENT_REGISTER", "ROBUSTNESS_RESULTS", "DAILY_PROFITABILITY"]
MD = ["V10_RESEARCH_REPORT", "V10_ECONOMIC_RESEARCH", "V10_XAU_H4_AUDIT", "V10_BENCHMARK_COMPARISON", "V10_FAILURE_ANALYSIS", "V10_VALIDATION_REPORT", "V10_PROFITABILITY_REPORT"]


def test_deliverables_exist():
    for n in CSV:
        p = RES / f"V10_{n}.csv"; assert p.exists() and p.stat().st_size > 100, p
    for n in MD:
        assert (DOCS / f"{n}.md").exists(), n


def test_frozen_baseline_unchanged():
    from research.v10_common import official_h4, sha256
    fr = json.load(open(ROOT / "results" / "v9" / "XAU_FROZEN.json"))
    assert sha256(ROOT / fr["ea_source"]) == fr["ea_sha256"]
    t = official_h4(3); assert len(t) == 248 and abs(t.pnl.sum() - 2172.77) < 0.02


def test_ea_log_reconciles_with_official():
    from research.v10_h4_audit import prep
    d, t = prep()
    assert len(t) == 248 and abs(t.pnl.sum() - 2172.77) < 0.02 and t.risk.notna().all()
    assert t.attrs["trades_csv_closetime_mismatch"] > 0           # hallazgo: el trades.csv cruza cierres de operaciones solapadas


def test_macro_calendar_dst_and_weekdays():
    from research.v10_macro import calendar, us_dst
    import datetime as dt
    c = calendar()
    assert (c.dow < 5).all()
    u = lambda ev, d: c[(c.event == ev) & (c.date_local == d)].utc.iloc[0]
    assert u("NFP", "2024-03-08") == pd.Timestamp("2024-03-08 13:30")      # antes del cambio de hora de EE.UU. (10-mar): EST, UTC-5
    assert u("CPI", "2024-03-12") == pd.Timestamp("2024-03-12 12:30")      # EDT, UTC-4
    assert u("NFP", "2024-11-01") == pd.Timestamp("2024-11-01 12:30")
    assert u("FOMC", "2024-11-07") == pd.Timestamp("2024-11-07 19:00")
    assert not us_dst(dt.date(2024, 3, 9)) and us_dst(dt.date(2024, 3, 11))


def test_macro_timestamp_check_peaks_at_event_slot():
    c = pd.read_csv(RES / "V10_MACRO_TIMESTAMP_CHECK.csv")
    assert (c.ranura_max_rango_min_respecto_T == 0).all()


def test_reserve_untouched():
    from research.v10_common import bars, m15, m5, RESERVE_START
    for d in (bars("H4"), bars("D1"), m15(), m5()):
        assert d.time.max() < RESERVE_START
    e = pd.read_csv(RES / "V10_MACRO_EVENTS.csv", parse_dates=["utc"]); assert e.utc.max() < RESERVE_START
    for sid in ("DFII10", "DGS10", "T10YIE", "DTWEXBGS", "VIXCLS"):
        f = pd.read_csv(ROOT / "data" / "raw" / "v10" / f"fred_{sid}.csv"); assert f.iloc[-1, 0] <= "2026-10-31"


def test_register_multiplicity_consistent():
    r = pd.read_csv(RES / "V10_EXPERIMENT_REGISTER.csv")
    n10 = int(r.N_V10_registrado.iloc[0]); N = int(r.N_acumulado_V7_V8_V9_V10.iloc[0])
    assert N == 3719 + n10 and abs(r.t_star_acumulado.iloc[0] - math.sqrt(2 * math.log(N))) < 0.01
    assert len(r) > 40 and set(r.clase) <= set("ABCDEFG")


def test_no_class_a_without_independent_validation():
    c = pd.read_csv(RES / "V10_STRATEGY_CANDIDATES.csv"); assert "A" not in set(c.clase)
    m = pd.read_csv(RES / "V10_MOMENTUM_RESEARCH.csv")
    # B solo si coherente y |t|>=2 (regla prefijada); ninguna prueba alcanza t*
    tstar = math.sqrt(2 * math.log(3805)); assert (m[m.clase == "A"].t_hac.abs() >= tstar).all()


def test_dsr_decreases_with_trials():
    from research.v10_h4_audit import dsr
    R = np.random.default_rng(1).normal(0.2, 1.0, 300)
    a, b = dsr(R, 10, 0.01)["dsr"], dsr(R, 3000, 0.01)["dsr"]; assert a > b


def test_sim_engine_matches_v8_reference():
    from research.v10_common import bars, R1
    from research.v10_h4_audit import Sim
    from research import v8_lote_c_h4 as C4
    d = bars("H4"); idx, dr = C4.signals_n(d, 20); S = Sim(d)
    ref = pd.read_csv(ROOT / "results" / "v8" / "xau_h1_reference_H4A1_rr3.0.csv")
    R, _, _, ok = S.many(idx, dr)
    assert len(R) == len(ref) and abs(R.sum() - ref.R_net.sum()) < 1e-6


def test_m15_parity_with_mt5():
    p = pd.read_csv(RES / "V10_M15_PARITY.csv").iloc[0]
    assert p.signal_overlap_pct >= 95 and p.direction_agree_pct >= 99


def test_no_order_send_or_secrets_in_v10_code():
    for f in RES.glob("v10_*.py"):
        s = f.read_text(encoding="utf8")
        assert "order_send" not in s and not re.search(r"(password|api[_-]?key|token\s*=)", s, re.I), f


def test_daily_profitability_consistent_with_v9_definition():
    d = pd.read_csv(RES / "V10_DAILY_PROFITABILITY.csv")
    h4 = d[d.config.str.contains("TP3R")].iloc[0]
    assert abs(h4.mean_daily_pct_trading_day - 0.0702) < 0.002          # misma definicion que V9 (retorno diario sobre balance previo, dias lun-vie)
    assert d[d.config.str.contains("M5|V9M5B")].iloc[0].net_usd < 0

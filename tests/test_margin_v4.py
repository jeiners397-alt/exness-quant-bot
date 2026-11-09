"""Pruebas V4: minimo 0,01, margen 5 % por simbolo, multiples posiciones, pendientes, SL dinamico, riesgo != margen, netting/hedging."""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation.dynamic_lot_sizing import size  # noqa: E402
from automation.margin_allocator import MarginAllocator  # noqa: E402
from automation.multi_position_controller import MultiPositionController  # noqa: E402
from automation.sl_risk_calculator import evaluate, sl_by_regime, sl_from_atr, sl_from_structure  # noqa: E402
from automation.symbol_specifications import PREFERRED_MIN_LOT, SymbolSpec, CALC_CFD  # noqa: E402

EUR = SymbolSpec.synthetic("EURUSDm", leverage=200)
XAU = SymbolSpec.synthetic("XAUUSDm", contract_size=100.0, tick_size=0.01, tick_value=1.0, calc_mode=CALC_CFD, digits=2, point=0.01, volume_min=0.01, volume_step=0.01)
BTC = SymbolSpec.synthetic("BTCUSDm", contract_size=1.0, tick_size=0.01, tick_value=0.01, calc_mode=CALC_CFD, digits=2, point=0.01, volume_min=0.01, volume_step=0.01, leverage=100)
IDX = SymbolSpec.synthetic("US30m", contract_size=1.0, tick_size=0.1, tick_value=0.1, calc_mode=CALC_CFD, digits=1, point=0.1, volume_min=0.1, volume_step=0.1)


def test_preferred_min_is_001_not_010():
    assert PREFERRED_MIN_LOT == 0.01
    a = MarginAllocator(3000, 5)
    d = size(EUR, a, 1.10, 1.0990, True, risk_pct_max=0.5)           # SL 10 pips
    assert d.approved and d.lots >= 0.01 and d.lots != 0.10 or d.lots > 0
    src = (ROOT / "automation" / "dynamic_lot_sizing.py").read_text(encoding="utf-8")
    assert not re.search(r"0\.10\b.*min|min.*0\.10\b", src.lower())


def test_lot_respects_broker_spec_and_never_rounds_up():
    spec = SymbolSpec.synthetic("X", volume_min=0.10, volume_step=0.10)
    assert spec.normalize_down(0.19) == 0.10 and spec.normalize_down(0.05) == 0.0
    a = MarginAllocator(3000, 5)
    d = size(spec, a, 1.10, 1.0990, True, risk_pct_max=0.5)
    assert d.lots % 0.10 < 1e-9 or abs(d.lots % 0.10 - 0.10) < 1e-9
    # el minimo del broker (0,10) no cabe en un riesgo diminuto -> rechazo, sin redondear hacia arriba
    d2 = size(spec, MarginAllocator(100, 5), 1.10, 1.0900, True, risk_pct_max=0.5)
    assert not d2.approved and d2.lots == 0


def test_margin_cap_5pct_never_exceeded_and_multiple_positions_allowed():
    a = MarginAllocator(3000, 5, global_percent=50)
    ctl = MultiPositionController(a, "HEDGING", max_total_risk_pct=50)
    n_ok = 0
    for _ in range(40):
        d, t = ctl.request_entry(EUR, True, 1.10, 1.0950, 1.11, risk_pct=1.0)
        n_ok += bool(t)
        assert a.used("EURUSDm") <= 150.0 + 1e-9
    assert n_ok >= 2                                                    # se admiten varias a la vez mientras haya presupuesto
    # se llego al tope: la siguiente se rechaza por margen
    d, t = ctl.request_entry(EUR, True, 1.10, 1.0950, 1.11, risk_pct=1.0)
    assert t is None and not d.approved


def test_example_from_order_150_budget_40_50_45():
    a = MarginAllocator(3000, 5)
    for k, m in enumerate((40, 50, 45)):
        a.add("POSITION", "EURUSDm", m, f"T{k}")
    assert a.used("EURUSDm") == 135 and a.remaining("EURUSDm") == 15
    assert a.check("EURUSDm", 14.9).approved and not a.check("EURUSDm", 15.1).approved


def test_pending_orders_count_and_toggle():
    a = MarginAllocator(3000, 5)
    a.add("PENDING", "EURUSDm", 140, "P1")
    assert not a.check("EURUSDm", 20).approved
    a2 = MarginAllocator(3000, 5, check_pending_orders=False)
    a2.add("PENDING", "EURUSDm", 140, "P1")
    assert a2.check("EURUSDm", 20).approved


def test_reservation_prevents_double_booking():
    a = MarginAllocator(3000, 5)
    d1, r1 = a.reserve("EURUSDm", 100)
    d2, r2 = a.reserve("EURUSDm", 100)
    assert r1 and r2 is None


@pytest.mark.parametrize("spec,entry,sl", [(EUR, 1.10, 1.095), (XAU, 2400.0, 2390.0), (BTC, 60000.0, 59000.0), (IDX, 40000.0, 39900.0)])
def test_works_across_instruments(spec, entry, sl):
    a = MarginAllocator(3000, 5)
    d = size(spec, a, entry, sl, True, risk_pct_max=0.5)
    if d.approved:
        assert d.margin <= 150.0 + 1e-9 and d.loss_at_sl <= 3000 * 0.005 + 1e-9 and spec.is_valid_volume(d.lots)
    else:
        assert d.lots == 0 and d.reason


def test_risk_is_independent_from_margin():
    a = MarginAllocator(3000, 5)
    # SL muy lejano: el riesgo limita el lote aunque el margen sea minimo
    d_far = size(EUR, a, 1.10, 1.05, True, risk_pct_max=0.5)
    d_near = size(EUR, MarginAllocator(3000, 5), 1.10, 1.0990, True, risk_pct_max=0.5)
    assert d_far.lots < d_near.lots
    assert d_far.risk_pct <= 0.5 + 1e-9 and d_far.margin < 150
    assert d_far.lots_by_risk < d_far.lots_by_margin                    # lo que manda es el riesgo, no el margen


def test_risk_limit_rejects_even_if_margin_is_tiny():
    # minimo 0,10 lotes con SL de 500 pips excede el 0,5 % de riesgo aunque el margen sea pequeno
    spec = SymbolSpec.synthetic("Y", volume_min=0.10, volume_step=0.10)
    d = size(spec, MarginAllocator(3000, 5), 1.10, 1.05, True, risk_pct_max=0.5)
    assert not d.approved and "riesgo" in d.reason


def test_dynamic_sl_variants_and_validation():
    e = 1.1000
    assert sl_from_structure(True, e, 1.0980, 0.0002) < 1.0980 and sl_from_structure(False, e, 1.1020, 0.0002) > 1.1020
    assert sl_from_atr(True, e, 0.0010, 1.5) == pytest.approx(1.0985)
    assert sl_by_regime(True, e, 0.001, 0.9) < sl_by_regime(True, e, 0.001, 0.5) < sl_by_regime(True, e, 0.001, 0.1)
    with pytest.raises(ValueError):
        evaluate(EUR, 0.1, e, None, None, 3000, True)
    with pytest.raises(ValueError):
        evaluate(EUR, 0.1, e, 1.2, None, 3000, True)


def test_loss_formula_eurusd():
    r = evaluate(EUR, 0.10, 1.10, 1.09, 1.12, 3000, True)             # 100 pips, 0,1 lote = 100 USD
    assert r.loss_at_sl == pytest.approx(100.0, rel=1e-6) and r.risk_pct_equity == pytest.approx(100 / 3000 * 100)
    assert r.reward_risk == pytest.approx(2.0)


def test_netting_vs_hedging():
    h = MultiPositionController(MarginAllocator(3000, 5, global_percent=50), "HEDGING", 50)
    _, t1 = h.request_entry(EUR, True, 1.10, 1.095, 1.11, 0.5)
    _, t2 = h.request_entry(EUR, False, 1.10, 1.105, 1.09, 0.5)
    assert t1 and t2 and t1 != t2 and len(h.positions) == 2
    n = MultiPositionController(MarginAllocator(3000, 5, global_percent=50), "NETTING", 50)
    _, a = n.request_entry(EUR, True, 1.10, 1.095, 1.11, 0.5)
    _, b = n.request_entry(EUR, True, 1.101, 1.095, 1.11, 0.5)
    assert a and b == a and len(n.positions) == 1                      # posicion neta unica
    d, c = n.request_entry(EUR, False, 1.10, 1.105, 1.09, 0.5)
    assert c is None and not d.approved


def test_reconcile_detects_differences():
    c = MultiPositionController(MarginAllocator(3000, 5, global_percent=50))
    _, t = c.request_entry(EUR, True, 1.10, 1.095, 1.11, 0.5)
    assert c.reconcile([{"ticket": t, "volume": c.positions[t].lots}]) == []
    assert c.reconcile([]) and c.reconcile([{"ticket": t, "volume": 9.9}])


def test_global_limit_blocks_correlated_exposure():
    a = MarginAllocator(3000, 5, global_percent=8)                     # 240 USD global, 150 por simbolo
    ctl = MultiPositionController(a, "HEDGING", 50)
    for _ in range(30):
        ctl.request_entry(EUR, True, 1.10, 1.0950, 1.11, 1.0)
        ctl.request_entry(XAU, True, 2400.0, 2390.0, 2420.0, 1.0)
        assert a.global_used() <= 240.0 + 1e-9


def test_automation_code_has_no_order_send():
    for f in (ROOT / "automation").glob("*.py"):
        code = re.sub(r'(?s)""".*?"""|#.*', "", f.read_text(encoding="utf-8"))
        assert "order_send(" not in code, f.name

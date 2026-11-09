"""Pruebas de REMIX V3: reglas A/B, causalidad, EA V3 (seguridad estatica) y no modificacion de V1/V2/V2.1."""
import hashlib
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab.v3 import gen_a, gen_b, session_levels  # noqa: E402
from tests.test_lookahead import synth  # noqa: E402


def bars(rows, start="2025-01-07 05:00", freq="1h", spread=8):
    t = pd.date_range(start, periods=len(rows), freq=freq)
    return pd.DataFrame({"time": t, "open": [r[0] for r in rows], "high": [r[1] for r in rows], "low": [r[2] for r in rows], "close": [r[3] for r in rows], "spread": spread, "tick_volume": 100})


def test_session_levels_only_after_asia_session_and_no_future_data():
    n = 30
    t = pd.date_range("2025-01-07 00:00", periods=n, freq="1h")
    df = pd.DataFrame({"time": t, "open": 1.1, "high": 1.1 + np.arange(n) * 1e-4, "low": 1.1 - np.arange(n) * 1e-4, "close": 1.1, "spread": 8, "tick_volume": 1})
    ah, al = session_levels(df)
    assert np.isnan(ah[:7]).all() and np.isnan(al[:7]).all()
    assert abs(ah[7] - (1.1 + 6e-4)) < 1e-12 and abs(al[7] - (1.1 - 6e-4)) < 1e-12        # max/min de las barras 0..6 del dia
    assert np.allclose(ah[7:24], ah[7])                                                    # constante durante el resto del dia (barras posteriores no lo modifican)


def _flat(n, base=1.1):
    return [(base, base + 0.0004, base - 0.0004, base)] * n


def test_false_breakout_short_rule_and_structural_sl():
    # 40 barras planas de 2 dias para PDH; luego, al dia siguiente 09:00, barrida del PDH y cierre dentro
    day1 = bars([(1.1, 1.1020, 1.0980, 1.1)] * 24, start="2025-01-06 00:00")                  # lunes: PDH = 1.1020
    day2 = bars([(1.1, 1.1004, 1.0996, 1.1)] * 9 + [(1.1015, 1.1032, 1.1010, 1.1012)] + [(1.1, 1.1004, 1.0996, 1.1)] * 5, start="2025-01-07 00:00")   # barra 09:00: high 1.1032 > PDH, close 1.1012 < PDH
    df = pd.concat([day1, day2], ignore_index=True)
    sig = gen_a(df, dict(levels="PD", confirm="1", sl_mode="struct", min_depth_atr=0.0))
    i = int(np.flatnonzero(sig.direction == -1)[0])
    assert df.time.iloc[i] == pd.Timestamp("2025-01-07 09:00")
    atr_i = pd.Series(np.maximum(df.high - df.low, 0)).rolling(14).mean().iloc[i]                  # ATR aproximado solo para orden de magnitud
    expected_sl = 1.1032 + 0.1 * float(__import__("remix_lab.indicators", fromlist=["x"]).atr(df, 14).iloc[i]) - 1.1012
    assert abs(sig.sl_dist[i] - expected_sl) < 1e-9 and abs(sig.tp_dist[i] - 1.5 * expected_sl) < 1e-9
    assert sig.time_exit_hour == 20 and atr_i > 0


@pytest.mark.parametrize("fam,params", [("A", dict(levels="PD")), ("A", dict(levels="ASIA", confirm="2")), ("B", dict(k=1.2, ker_on=True)), ("B", dict(mode="squeeze", ker_on=False))])
def test_a_b_do_not_use_future_bars(fam, params):
    df = synth(4000, seed=17)
    df["time"] = pd.date_range("2025-01-06 00:00", periods=len(df), freq="15min")
    fn = gen_a if fam == "A" else gen_b
    full = fn(df, params)
    for cut in (1500, 2600, 3300):
        part = fn(df.iloc[:cut].reset_index(drop=True), params)
        assert np.array_equal(full.direction[:cut - 1], part.direction[:cut - 1]), f"{fam} {params}: la senal cambia al truncar el futuro"


def test_volatility_momentum_impulse_rule():
    rows = [(1.1, 1.1004, 1.0996, 1.1)] * 30 + [(1.1000, 1.1030, 1.0998, 1.1028)] + [(1.1, 1.1004, 1.0996, 1.1)] * 3     # barra grande alcista (rango 32 pts, cuerpo 28 pts)
    df = bars(rows, start="2025-01-07 00:00", freq="15min")
    df["time"] = pd.date_range("2025-01-07 07:15", periods=len(df), freq="15min")
    sig = gen_b(df, dict(k=2.0, ker_on=False, sl_mode="atr"))
    idx = np.flatnonzero(sig.direction != 0)
    assert len(idx) == 1 and sig.direction[idx[0]] == 1 and idx[0] == 30
    assert abs(sig.tp_dist[30] / sig.sl_dist[30] - 1.5) < 1e-9


MQL = ROOT / "mql5"


def test_v3_ea_safety_static():
    src = (MQL / "REMIX_EURUSD_V3.mq5").read_text(encoding="utf-8-sig")
    assert re.search(r"input ENUM_V3_MODULE Module\s*=\s*MOD_NONE", src) and re.search(r"input bool\s+EnableTrading\s*=\s*false", src)
    assert "NINGUN MODULO TIENE VENTAJA" in src and "OrderSend(" not in src and "OrderSendAsync" not in src
    allowed = {"OpenTrade", "ClosePosition", "ModifySL"}
    cur, name = [], None
    funcs = {}
    for line in src.splitlines():
        m = re.match(r"^(?:void|bool|double|int|string|datetime)\s+(\w+)\s*\(", line)
        if m:
            if name: funcs[name] = "\n".join(cur)
            name, cur = m.group(1), [line]
        elif name:
            cur.append(line)
    funcs[name] = "\n".join(cur)
    for fn, body in funcs.items():
        if re.search(r"trade\.(Buy|Sell|PositionClose|PositionModify)\(", body):
            assert fn in allowed and "TradingAllowed()" in body, fn
    assert "MQL_TESTER" in funcs["TradingAllowed"] and "ACCOUNT_TRADE_MODE_REAL" in funcs["TradingAllowed"] and "MOD_C_MACRO_NEWS" in funcs["TradingAllowed"]
    assert "SKIP_NO_SL" in funcs["OpenTrade"] and "SizingPolicy == SIZE_STRICT" in funcs["CalcLots"]
    assert 'StringFind(_Symbol, "EURUSD") != 0' in src
    assert "PENDIENTE DE DATOS" in src
    assert "martingal" not in src.lower()


def test_previous_eas_untouched():
    sha = lambda p: hashlib.sha256((MQL / p).read_bytes()).hexdigest()
    assert sha("REMIX_STRATEGY_RESEARCH_LAB_V1.mq5").lower() == "1c327de0d8f1d8e70c47fde2c2d4ed85e023e2d91cf5f03085bbd7cba46c42d7"
    assert sha("REMIX_EURUSD_V2.mq5") == "9908279f438ba7848e2f9503ba9244d49bb190ce0d9c27c212482f2b3056dc94"
    assert sha("REMIX_EURUSD_V2_1.mq5") == "9a5be44f1d6b081c454f338298a3d28468720828f97ee47c99a5613878715df6"

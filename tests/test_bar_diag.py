import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from compare_bar_diag import compare, python_side  # noqa: E402
from tests.test_lookahead import synth  # noqa: E402


def fake_diag(h4, adx_kind, path):
    """CSV con el formato del EA V2.1 construido desde Python (ida y vuelta) para validar el comparador."""
    py = python_side(h4)
    a = py.adx_mt5 if adx_kind == "mt5" else py.adx_wilder
    p = py.pdi_mt5 if adx_kind == "mt5" else py.pdi_wilder
    m = py.mdi_mt5 if adx_kind == "mt5" else py.mdi_wilder
    rows = []
    for i in range(300, len(h4)):
        z = py.z50.iloc[i]
        sig = 1 if z <= -2 else (-1 if z >= 2 else 0)
        rows.append(dict(bar0_time=(h4.time.iloc[i] + pd.Timedelta(hours=4)).strftime("%Y.%m.%d %H:%M"), bar1_time=h4.time.iloc[i].strftime("%Y.%m.%d %H:%M"),
                         open1=h4.open.iloc[i], high1=h4.high.iloc[i], low1=h4.low.iloc[i], close1=h4.close.iloc[i], spread_pts=9, atr14=py.atr14.iloc[i],
                         sma50_manual=py.sma50_manual.iloc[i], sma50_ima=py.sma50_manual.iloc[i], std50=py.std50.iloc[i], z50=z, adx14=a.iloc[i], plus_di=p.iloc[i],
                         minus_di=m.iloc[i], signal_dir=sig, reason="NO_SIGNAL", in_position=0, balance=3000.0))
    pd.DataFrame(rows).to_csv(path, index=False)


def test_comparator_roundtrip_identifies_adx_implementation(tmp_path):
    h4 = synth(1200, seed=33)
    h4["time"] = pd.date_range("2025-01-06 00:00", periods=len(h4), freq="4h")
    fake_diag(h4, "mt5", tmp_path / "mt5.csv")
    r = compare(tmp_path / "mt5.csv", h4)
    assert r["atr14"]["max_abs_diff"] < 1e-9 and r["z50"]["max_abs_diff"] < 1e-9
    assert r["adx14"]["closest_implementation"] == "MT5_EMA" and r["adx14"]["max_abs_diff_vs_formula_MT5_EMA"] < 1e-6
    fake_diag(h4, "wilder", tmp_path / "wilder.csv")
    r2 = compare(tmp_path / "wilder.csv", h4)
    assert r2["adx14"]["closest_implementation"] == "Wilder"

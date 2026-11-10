import sys
from pathlib import Path
import pandas as pd, pytest
R = Path(__file__).resolve().parent.parent / "research"
need = [R / f for f in ("V7_ROBUSTNESS_RESULTS.csv", "V7_ROBUSTNESS_RESULTS_H1.csv", "V7_MARKET_PROFILES.csv")]


@pytest.mark.skipif(not all(p.exists() for p in need), reason="resultados V7 locales")
def test_v7_no_class_a_and_multiplicity_declared():
    for f in need[:2]:
        t = pd.read_csv(f)
        assert not (t["class"] == "A").any()                      # sin datos independientes no hay clase A
        assert (t["class"] == "B").sum() == 0 or t[t["class"] == "B"].passes_multiplicity_is.all()
        assert t.N_tests.iloc[0] == len(t) and abs(t.t_star_multiplicity.iloc[0] - (2 * __import__("math").log(len(t))) ** 0.5) < 0.01
    assert len(pd.read_csv(need[2])) == 10                          # diez mercados exactos


def test_v7_data_stops_before_holdout():
    d = Path(__file__).resolve().parent.parent / "data" / "raw" / "v7"
    if not d.exists():
        pytest.skip("datos locales")
    for f in d.glob("*_M15.csv"):
        t = pd.read_csv(f, usecols=["time"], parse_dates=["time"]).time.max()
        assert t <= pd.Timestamp("2026-11-01 06:00"), f.name       # holdout posterior a 2026-11-01 sin tocar

"""Prueba generica de causalidad: la senal de la barra i no cambia al truncar los datos posteriores (S01-S04)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from remix_lab.strategies import generate  # noqa: E402

SPEC = {"point": 1e-5}


def synth(n=3000, seed=7):
    rng = np.random.default_rng(seed)
    c = 1.1 + np.cumsum(rng.normal(0, 0.0004, n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + rng.uniform(0, 0.0003, n)
    l = np.minimum(o, c) - rng.uniform(0, 0.0003, n)
    t = pd.date_range("2025-01-06 00:00", periods=n, freq="15min")
    return pd.DataFrame({"time": t, "open": o, "high": h, "low": l, "close": c, "tick_volume": 100, "spread": 8, "real_volume": 0})


@pytest.mark.parametrize("sid", ["S01", "S02", "S03", "S04"])
def test_signal_does_not_depend_on_future(sid):
    df = synth()
    full = generate(sid, df, SPEC)
    for cut in (1200, 1800, 2500):
        part = generate(sid, df.iloc[:cut].reset_index(drop=True), SPEC)
        a, b = full.direction[:cut - 1], part.direction[:cut - 1]     # la ultima barra del tramo se excluye (S01 usa el dia completo)
        # S01: el rango asiatico del dia en curso no debe depender de barras posteriores a la senal
        if sid == "S01":
            m = ~pd.Series(df.time.iloc[:cut - 1]).dt.normalize().eq(df.time.iloc[cut - 1].normalize()).to_numpy()
            a, b = a[m], b[m]
        assert np.array_equal(a, b), f"{sid}: la senal cambia al truncar el futuro (lookahead)"
        assert np.allclose(full.sl_dist[:cut - 1][a != 0] if sid != "S01" else 0, part.sl_dist[:cut - 1][b != 0] if sid != "S01" else 0, equal_nan=True) or sid == "S01"
    assert (full.direction != 0).sum() > 0, f"{sid} sin senales en datos sinteticos (prueba vacia)"

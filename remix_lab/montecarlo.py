"""G. MONTE CARLO ENGINE - estabilidad y riesgo por remuestreo de las R-multiples de las operaciones.

Reordena (bootstrap con reemplazo) las R netas y recompone la curva con riesgo fraccional fijo
(compuesto). Mide la dependencia del orden de las operaciones; NO crea ventaja nueva y NO
sustituye la validacion fuera de muestra.
"""
from __future__ import annotations

import numpy as np


def monte_carlo(r_multiples, risk_pct=0.5, initial=100.0, n_sims=5000, seed=12345, ruin_fraction=0.5):
    r = np.asarray(r_multiples, float)
    r = r[np.isfinite(r)]
    if len(r) < 10:
        return dict(n_trades=int(len(r)), note="insuficientes operaciones (<10)")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(r), size=(n_sims, len(r)))
    f = np.maximum(1.0 + r[idx] * risk_pct / 100.0, 0.0)
    eq = initial * np.cumprod(f, axis=1)
    eq0 = np.concatenate([np.full((n_sims, 1), initial), eq], axis=1)
    peak = np.maximum.accumulate(eq0, axis=1)
    dd = ((peak - eq0) / peak).max(axis=1) * 100
    ret = (eq[:, -1] / initial - 1) * 100
    ruin = (eq0.min(axis=1) <= initial * ruin_fraction).mean() * 100
    q = lambda a, p: float(np.percentile(a, p))
    return dict(n_trades=int(len(r)), n_sims=n_sims,
                return_pct_p5=q(ret, 5), return_pct_p50=q(ret, 50), return_pct_p95=q(ret, 95),
                max_dd_pct_p50=q(dd, 50), max_dd_pct_p95=q(dd, 95),
                prob_loss_pct=float((ret < 0).mean() * 100), prob_ruin_pct=float(ruin))

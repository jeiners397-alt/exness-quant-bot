"""Impacto de usar el ADX con la formula de MT5 (EMA 2/(n+1)) en lugar de Wilder en L2 (S05 H4, z=2, ADX<25, SL 2 ATR, 18 barras).
Mismos parametros congelados; solo cambia la implementacion del ADX. Barras H4 NATIVAS 2022-2026 + (2018-2021 derivadas de H1). Exploratorio."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab import harness as H  # noqa: E402
from remix_lab.strategies import Signals  # noqa: E402
from remix_lab.strategies_d import GEN, resample  # noqa: E402

F = H.load_frames()
H1 = pd.concat([F["RETRO"]["H1"], F["EXPL"]["H1"]]).reset_index(drop=True)
H4 = resample(H1, "H4")
PER = {"TRAIN 2018-21": ("2018-01-01", "2022-01-01"), "VALID 2022-24": ("2022-01-01", "2025-01-01"), "EXPL 2025-26": ("2025-01-01", "2026-11-01"), "POOL 2018-26": ("2018-01-01", "2026-11-01")}
rows = []
for impl in ("wilder", "mt5"):
    sig = GEN["S05"](H4, dict(z_th=2.0, trend_filter=True, sl_atr=2.0, max_bars=18, adx_impl=impl))
    for name, (a, b) in PER.items():
        m = ((H4.time >= a) & (H4.time < b)).to_numpy()
        df = H4[m].reset_index(drop=True)
        s = Signals(sig.direction[m], sig.sl_dist[m], sig.tp_dist[m], None, 18)
        r, tr = H.run(df, s, dict(adx=impl, period=name), n_ctrl=200 if name.startswith("POOL") else 0, with_control=name.startswith("POOL"))
        rows.append({k: r.get(k) for k in ("adx", "period", "n", "wr", "pf", "exp_R", "ci_block", "t", "maxdd_pct", "net_usd", "ctrl_p")})
R = pd.DataFrame(rows)
R.to_csv(ROOT / "research/L2_ADX_IMPACT.csv", index=False)
pd.set_option("display.width", 220)
print(R.to_string(index=False))

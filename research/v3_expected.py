"""Operaciones ESPERADAS por Python (motor corregido) para los .set de REMIX_EURUSD_V3, 2025-01-01..2026-10-31, 3000 USD, 0,5 %, estricto. No son resultados de MT5."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab import harness as H  # noqa: E402
from remix_lab import indicators as ind  # noqa: E402
from remix_lab.backtest import BacktestConfig, run_backtest  # noqa: E402
from remix_lab.strategies import Signals  # noqa: E402
from remix_lab.strategies_d import GEN, resample  # noqa: E402
from remix_lab.v3 import gen_a, gen_b  # noqa: E402

START, END = pd.Timestamp("2025-01-01"), pd.Timestamp("2026-11-01")
F = H.load_frames()
H1 = pd.concat([F["RETRO"]["H1"], F["EXPL"]["H1"]]).reset_index(drop=True)
H4 = pd.read_csv(ROOT / "data/raw/hist/EURUSDm_H4_native_2022_2026.csv", parse_dates=["time"])
H4.loc[H4.spread <= 0, "spread"] = H4.spread[H4.spread > 0].median()
CFG = BacktestConfig(H.CAP, H.RISK, "strict", 0.0, 0.0, True, max_spread_frac_sl=0.15, max_spread_points=30, reenter_after_open_exit=True, bar_seconds=0)


def run(df, sig, cost=True, session=False):
    if cost:
        sig = H.cost_filter(df, sig, 0.10)
    j0 = int(np.searchsorted(df.time.values, np.datetime64(START))); i0 = max(j0 - 1, 0); e = int(np.searchsorted(df.time.values, np.datetime64(END)))
    sub = df.iloc[i0:e].reset_index(drop=True)
    s2 = Signals(sig.direction[i0:e], sig.sl_dist[i0:e], sig.tp_dist[i0:e], sig.time_exit_hour, sig.max_bars)
    return run_backtest(sub, s2, H.SPEC, CFG)


out = ROOT / "results" / "v3_expected"; out.mkdir(parents=True, exist_ok=True)
summ = {}
# A: H1, PD, confirm 1, struct
sa = gen_a(H1, dict(levels="PD", confirm="1", sl_mode="struct"))
# B: H1, impulso k=2.0, sin KER, SL estructural
sb = gen_b(H1, dict(mode="impulse", k=2.0, ker_on=False, sl_mode="struct"))
# D: H4 nativo, z=2, sin ADX, regimen KER<0.514 & CHOP>=43.587 (terciles TRAIN), SL 2 ATR, TP media, max 18 barras
f = pd.DataFrame({"ker": ind.ker(H4.close, 10), "chop": ind.choppiness(H4, 14)})
base = GEN["S05"](H4, dict(z_th=2.0, trend_filter=False, sl_atr=2.0, max_bars=18))
m = ((f.ker < 0.514) & (f.chop >= 43.587)).to_numpy()
sd = Signals(np.where(m, base.direction, 0), base.sl_dist, base.tp_dist, None, 18)
for name, df, sig in (("A_H1_PD_struct", H1, sa), ("B_H1_impulse_k2_struct", H1, sb), ("D_H4_regime", H4, sd)):
    tr, info = run(df, sig, cost=(name != "D_H4_regime"))
    tr[["entry_time", "exit_time", "dir", "lots", "entry", "exit", "exit_reason", "sl_dist", "tp_dist", "net_r", "net_money", "swap", "balance"]].to_csv(out / f"V3_{name}_expected_trades.csv", index=False)
    r = H.summarize(tr, info, {})
    summ[name] = {k: r.get(k) for k in ("n", "wr", "pf", "exp_R", "net_usd", "maxdd_pct", "recovery", "top1_share", "exp_R_ex5")} | {"skipped": info["skipped"]}
    print(name, summ[name], flush=True)
(out / "V3_expected_summary.json").write_text(json.dumps(summ, indent=1, default=str), encoding="utf-8")

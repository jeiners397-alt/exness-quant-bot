"""Operaciones ESPERADAS por Python (motor corregido) para REMIX_EURUSD_V2_1 / L2 (S05 H4), 3000 USD, 0,5 %, estricto, EURUSDm, 2025-01-01..2026-10-31.
Semantica de V2.1: max_bars en barras reales; compuertas de spread en la barra de entrada; ADX con formula MT5; reentrada en la barra de salida;
modelo de sesion (spread del primer tick y mercado cerrado antes de las 22:00). NO es un resultado de MT5: sirve para compararlo con el export del Tester."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research")); sys.path.insert(0, str(ROOT))
import parity_v2_l2 as P  # noqa: E402
from remix_lab import harness as H  # noqa: E402

full = pd.read_csv(ROOT / "data/raw/hist/EURUSDm_H4_native_2022_2026.csv", parse_dates=["time"])
full.loc[full.spread <= 0, "spread"] = full.spread[full.spread > 0].median()
tr, info = P.python_run(full, warmup=True, gates=True, adx="mt5", reenter=True, calendar=False, session=True)
out = ROOT / "results" / "v2_1_expected"; out.mkdir(parents=True, exist_ok=True)
cols = ["entry_time", "exit_time", "dir", "lots", "entry", "exit", "exit_reason", "sl_dist", "tp_dist", "entry_spread_pts", "bars_held", "nights", "swap", "net_r", "net_money", "balance"]
tr[cols].to_csv(out / "V2_1_S05_L2_H4_expected_trades.csv", index=False)
r = H.summarize(tr, info, {})
summ = {k: r.get(k) for k in ("n", "wr", "pf", "exp_R", "net_usd", "maxdd_pct", "recovery", "payoff", "cost_R", "gross_R")}
summ.update(skipped=info["skipped"], semantics="V2.1: max_bars en barras reales; gates 0.15xSL y 30 pts; ADX MT5; reentrada; modelo de sesion", period="2025-01-01..2026-10-31", capital=3000, risk_pct=0.5)
(out / "V2_1_S05_L2_H4_expected_summary.json").write_text(json.dumps(summ, indent=1, default=str), encoding="utf-8")
print(json.dumps(summ, indent=1, default=str))
print(tr.exit_reason.value_counts().to_dict())

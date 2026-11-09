"""Analiza el CSV del EA V4 (Strategy Tester) y escribe research/MULTI_MARKET_RESULTS.csv-compatible resumen + verificaciones de margen/lotaje."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sym = sys.argv[1] if len(sys.argv) > 1 else "EURUSDm"
per = sys.argv[2] if len(sys.argv) > 2 else "PERIOD_M15"
src = Path.home() / "AppData/Roaming/MetaQuotes/Terminal/Common/Files" / f"REMIX_V4_margin_{sym}_{per}.csv"
d = pd.read_csv(src)
adm = d[d.event.isin(["OPEN", "PENDING"])]
rej = d[d.event == "REJECT"]
out = dict(
    symbol=sym, events=len(d), admitted=len(adm), admitted_market=int((adm.event == "OPEN").sum()), admitted_pending=int((adm.event == "PENDING").sum()),
    rejected=len(rej), rejected_by_reason=rej.reason.value_counts().to_dict(),
    # margen del simbolo tras admitir vs presupuesto (5 % de la equidad del mismo instante, previo a la orden)
    max_margin_after_over_budget=float((adm.margin_symbol_after / adm.budget).max()),
    n_admitted_exceeding_budget=int((adm.margin_symbol_after > adm.budget * (1 + 1e-9)).sum()),
    max_margin_pct_of_equity_at_log=float(adm.margin_pct_after.max()),
    lots_min=float(adm.lots.min()), lots_max=float(adm.lots.max()), lots_distinct=sorted(adm.lots.unique().tolist())[:12],
    broker_volmin=float(d.volmin.iloc[0]), broker_volstep=float(d.volstep.iloc[0]),
    lots_below_volmin=int((adm.lots < d.volmin.iloc[0] - 1e-9).sum()),
    lots_off_step=int(((adm.lots / d.volstep.iloc[0]).round(6) % 1 > 1e-6).sum()),
    max_simultaneous_positions=int(d.n_positions.max()), max_pending=int(d.n_pending.max()),
    risk_pct_max=float(adm.risk_pct.max()), risk_pct_mean=float(adm.risk_pct.mean()),
    sl_modes=adm.sl_mode.value_counts().to_dict(),
    sl_dist_by_mode={k: round(float(v), 6) for k, v in adm.groupby("sl_mode").sl_dist.mean().items()},
    rejected_while_budget_available=int(((rej.reason == "MARGIN_BUDGET") & ((rej.budget - rej.margin_symbol_before) > 0.5 * rej.budget)).sum()),
)
print(json.dumps(out, indent=1, default=str))
(ROOT / "research" / f"V4_DIAG_{sym}.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
d.to_csv(ROOT / "research" / f"V4_DIAG_{sym}_events.csv", index=False)

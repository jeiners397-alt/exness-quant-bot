"""Consolida los resultados OFICIALES de MT5 (informes parseados) en research/*.csv. No inventa metricas."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rows = []
for d in sorted((ROOT / "results" / "v4_runs").glob("RUN_*")):
    m, s = d / "meta.json", d / "stats.json"
    if not (m.exists() and s.exists()):
        continue
    meta, st = json.loads(m.read_text(encoding="utf-8")), json.loads(s.read_text(encoding="utf-8"))["stats"]
    rows.append(dict(run_id=meta["run_id"], symbol=meta["symbol"], period=meta["period"], strategy=meta["strategy"], from_date=meta["from_date"], to_date=meta["to_date"],
                     capital=meta["capital"], leverage=meta["leverage"], model=meta["model"], status=meta["status"], ea_version=meta["ea_version"],
                     config_hash=meta["config_hash"][:16], net_profit=st["total_net_profit"], gross_profit=st["gross_profit"], gross_loss=st["gross_loss"],
                     profit_factor=st["profit_factor"], expected_payoff=st["expected_payoff"], trades=st["total_trades"], win_pct=st.get("profit_trades_pct"),
                     equity_dd_pct=st.get("equity_dd_max_pct"), recovery_factor=st["recovery_factor"], sharpe=st["sharpe_ratio"], history_quality=st["history_quality"]))
if rows:
    with open(ROOT / "research" / "MULTI_MARKET_RESULTS.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    strat = [dict(rank=i + 1, run_id=r["run_id"], strategy=r["strategy"], symbol=r["symbol"], trades=r["trades"], profit_factor=r["profit_factor"], net_profit=r["net_profit"],
                  verdict=("DIAGNOSTICO (no es estrategia)" if r["strategy"].startswith("V4_DIAG") else "SIN VENTAJA DEMOSTRADA"))
             for i, r in enumerate(sorted(rows, key=lambda r: -(r["profit_factor"] or 0)))]
    with open(ROOT / "research" / "STRATEGY_RANKING.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(strat[0].keys())); w.writeheader(); w.writerows(strat)
print(len(rows), "runs")
for r in rows:
    print(r["run_id"], r["status"], r["net_profit"], r["trades"], r["profit_factor"])

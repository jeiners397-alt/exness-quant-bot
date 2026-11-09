"""H. REPORT ENGINE - informes comparativos en Markdown/CSV."""
from __future__ import annotations

import pandas as pd

from . import RESULTS_DIR
from .metrics import breakdown, compute_metrics


def _fmt(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False, floatfmt=".3f")
    except ImportError:  # tabulate no instalado
        return "```\n" + df.to_string(index=False) + "\n```"


def tag_sample(tr: pd.DataFrame, holdout_start) -> pd.DataFrame:
    tr = tr.copy()
    tr["sample"] = (tr["entry_time"] >= pd.Timestamp(holdout_start)).map({True: "HOLDOUT", False: "IN_SAMPLE"})
    return tr


def strategy_report(tr: pd.DataFrame, title: str, initial=100.0) -> str:
    m = compute_metrics(tr, initial)
    out = [f"## {title}", "", "| Metrica | Valor |", "|---|---|"]
    for k, v in m.items():
        out.append(f"| {k} | {v:.4f} |" if isinstance(v, float) else f"| {k} | {v} |")
    for by in ("dir", "symbol", "timeframe", "sample"):
        if by in tr.columns and not tr.empty:
            out += ["", f"### Por `{by}`", "", _fmt(breakdown(tr, by, initial))]
    return "\n".join(out)


def save_trades(tr: pd.DataFrame, name: str):
    p = RESULTS_DIR / f"{name}.csv"
    tr.to_csv(p, index=False)
    return p


def comparison_table(path=None) -> pd.DataFrame:
    p = path or RESULTS_DIR / "experiments.csv"
    df = pd.read_csv(p)
    cols = ["stage", "strategy", "symbol", "timeframe", "trades", "win_rate", "profit_factor", "expectancy_r",
            "net_profit", "max_dd_pct", "total_costs", "sizing", "skipped"]
    return df[cols]

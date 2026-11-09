"""Registro de hipotesis y seleccion de experimentos (max 20 por lote). No repite hipotesis descartadas sin una hipotesis nueva declarada.
Estado persistente en research/EXPERIMENT_REGISTER.csv."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "research" / "EXPERIMENT_REGISTER.csv"
FIELDS = ["exp_id", "hypothesis", "family", "markets", "timeframes", "status", "decision", "new_hypothesis_justification", "evidence_file", "notes"]
MAX_PER_BATCH = 20
DISCARDED = {"DISCARDED", "NO_EDGE"}

# hipotesis ya investigadas (no se repiten) y nuevas pendientes definidas de antemano
SEED = [
    ("H001", "S01 L2 mean reversion EURUSD M15", "reversion", "EURUSDm", "M15", "DONE", "NO_EDGE", "", "docs/INFORME_FASE_C_2026-11-09.md", "t=0.52"),
    ("H002", "S02-S04 EURUSD M15/H1", "multi", "EURUSDm", "M15|H1", "DONE", "NO_EDGE", "", "docs/INFORME_FASES_1-5_EURUSD_2026-11-09.md", "costes"),
    ("H003", "Phase D S05-S12 (100 configs)", "multi", "EURUSDm", "H1|H4|D1", "DONE", "NO_EDGE", "", "docs/REMIX_EURUSD_PHASE_D_REPORT.md", ""),
    ("H004", "V3 A False Breakout", "liquidity_sweep", "EURUSDm", "M15|H1", "DONE", "NO_EDGE", "", "docs/REMIX_EURUSD_V3_REPORT.md", ""),
    ("H005", "V3 B Volatility Momentum", "momentum", "EURUSDm", "M15|H1", "DONE", "DISCARDED", "", "docs/REMIX_EURUSD_V3_REPORT.md", ""),
    ("H006", "V3 D regimen H4 (KER/CHOP)", "regime", "EURUSDm", "H4", "DONE", "WEAK_LEAD", "", "docs/REMIX_EURUSD_V3_REPORT.md", "t=1.27"),
    ("H007", "Macro news (C)", "news", "EURUSDm", "M5|M15", "BLOCKED", "PENDING_DATA", "", "remix_lab/news.py", "sin calendario verificable"),
    ("H101", "Sweep+BOS en M15 multiactivo (XAUUSD,GBPUSD,USDJPY) con contexto H1", "liquidity_sweep", "GBPUSDm|USDJPYm|XAUUSDm", "M15", "PLANNED", "", "mercados distintos de EURUSD no probados", "", ""),
    ("H102", "Breakout-retest de consolidacion Londres->NY (M15/M5)", "breakout_retest", "EURUSDm|GBPUSDm", "M15|M5", "PLANNED", "", "familia no probada", "", ""),
    ("H103", "Estacionalidad intradia por hora (event-study) en 8 mercados", "seasonality", "multi", "M15", "PLANNED", "", "no probada fuera de EURUSD", "", ""),
]


def load() -> list[dict]:
    if not REG.exists():
        save([dict(zip(FIELDS, s)) for s in SEED])
    with REG.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save(rows: list[dict]) -> None:
    REG.parent.mkdir(exist_ok=True)
    with REG.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)


def select_batch(max_n: int = MAX_PER_BATCH) -> list[dict]:
    rows = load()
    out = []
    for r in rows:
        if r["status"] != "PLANNED":
            continue
        if r["decision"] in DISCARDED and not r["new_hypothesis_justification"].strip():
            continue                                       # no se repite sin hipotesis nueva
        out.append(r)
        if len(out) >= min(max_n, MAX_PER_BATCH):
            break
    return out


def update(exp_id: str, **kw) -> None:
    rows = load()
    for r in rows:
        if r["exp_id"] == exp_id:
            r.update(kw)
    save(rows)

"""Ejecucion y registro de experimentos (todos se registran, tambien los negativos)."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

import pandas as pd

from . import RESULTS_DIR, load_config, data_engine as de, strategies as st
from .backtest import BacktestConfig, run_backtest
from .metrics import compute_metrics

log = logging.getLogger("remix.exp")
EXP_FILE = RESULTS_DIR / "experiments.csv"


class HoldoutViolation(RuntimeError):
    pass


def split_dates(cfg):
    s = cfg["splits"]
    return s["in_sample_start"], s["in_sample_end"], s["holdout_start"], s["holdout_end"]


def bt_config(cfg, **over) -> BacktestConfig:
    a, c = cfg["account"], cfg["costs"]
    kw = dict(initial_capital=a["initial_capital"], risk_pct=a["risk_pct"], sizing_policy=cfg["sizing_policy"],
              commission_per_lot_roundturn=c["commission_per_lot_roundturn"], slippage_points=c["slippage_points"])
    kw.update(over)
    return BacktestConfig(**kw)


def load_spec(symbol):
    """Especificacion guardada por scripts/01_download_data.py (sin necesidad de MT5)."""
    from . import DATA_DIR
    with open(DATA_DIR / "symbol_specs.json", encoding="utf-8") as f:
        return json.load(f)[symbol]


def log_experiment(row: dict):
    EXP_FILE.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([row])
    df.to_csv(EXP_FILE, mode="a", header=not EXP_FILE.exists(), index=False)


def run_one(sid, symbol, tf, params, start, end, cfg, stage="single", df=None, spec=None, bt=None,
            log_it=True, note=""):
    df = de.load_rates(symbol, tf, start, end) if df is None else df
    spec = spec or load_spec(symbol)
    bt = bt or bt_config(cfg)
    sig = st.generate(sid, df, spec, params)
    tr, info = run_backtest(df, sig, spec, bt, tag=dict(strategy=sid, symbol=symbol, timeframe=tf))
    m = compute_metrics(tr, bt.initial_capital)
    if log_it:
        full = {**st.get_strategy(sid)[0].defaults, **(params or {})}
        log_experiment(dict(run_id=uuid.uuid4().hex[:10], ts=datetime.now().isoformat(timespec="seconds"),
                            stage=stage, strategy=sid, symbol=symbol, timeframe=tf, start=start, end=end,
                            params=json.dumps(full, sort_keys=True), sizing=bt.sizing_policy,
                            skipped=json.dumps(info["skipped"]), note=note, **m))
    return tr, m, info

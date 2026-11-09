"""E. OPTIMIZATION ENGINE - busqueda en rejilla sobre grids predefinidos, SOLO en muestra.

El holdout final esta protegido: cualquier dato posterior a in_sample_end lanza HoldoutViolation.
Todos los puntos evaluados (buenos y malos) quedan en results/experiments.csv.
"""
from __future__ import annotations

import itertools

import pandas as pd

from . import strategies as st
from .experiments import HoldoutViolation, run_one, split_dates


def guard_in_sample(df: pd.DataFrame, cfg):
    _, is_end, _, _ = split_dates(cfg)
    if not df.empty and df["time"].max() >= pd.Timestamp(is_end) + pd.Timedelta(days=1):
        raise HoldoutViolation(f"Datos posteriores a {is_end} no pueden usarse para seleccionar parametros.")


def grid_points(sid, grid=None):
    spec = st.get_strategy(sid)[0]
    g = grid or spec.grid
    keys = list(g)
    return [dict(zip(keys, v)) for v in itertools.product(*[g[k] for k in keys])]


def optimize(sid, symbol, tf, df, spec, bt, cfg, start, end, min_trades=30, grid=None, stage="opt", objective="expectancy_r"):
    """Devuelve DataFrame con todos los puntos ordenados por objetivo (restriccion: min_trades)."""
    guard_in_sample(df, cfg)
    rows = []
    for p in grid_points(sid, grid):
        _, m, info = run_one(sid, symbol, tf, p, start, end, cfg, stage=stage, df=df, spec=spec, bt=bt)
        rows.append({**p, **{k: m[k] for k in ("trades", "profit_factor", "expectancy_r", "net_profit", "max_dd_pct")}})
    res = pd.DataFrame(rows)
    res["eligible"] = res["trades"] >= min_trades
    res = res.sort_values(["eligible", objective], ascending=False).reset_index(drop=True)
    return res

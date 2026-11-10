"""Rentabilidad diaria a partir de los informes OFICIALES de MT5 (trades.csv de cada run). Solo beneficio REALIZADO: el beneficio flotante intradia
no se exporta en el informe HTML => se marca NO_DISPONIBLE (no se inventa). Uso: python research/v7_daily_profitability.py [prefijo_run ...]"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TARGET = 0.01


def daily(run_dir: Path, capital=3000.0) -> pd.DataFrame:
    t = pd.read_csv(run_dir / "trades.csv")
    if t.empty: return pd.DataFrame()
    t["close_time"] = pd.to_datetime(t.close_time, format="%Y.%m.%d %H:%M:%S")
    t["day"] = t.close_time.dt.normalize()
    t["net"] = t.profit + t.commission + t.swap
    days = pd.date_range("2024-01-01", "2026-10-31", freq="D")
    g = t.groupby("day").agg(realized=("net", "sum"), trades=("net", "size"), costs=("commission", "sum"), swaps=("swap", "sum"), lots=("lots", "sum")).reindex(days).fillna(0.0)
    g["eq_start"] = capital + g.realized.cumsum().shift(1).fillna(0.0)
    g["eq_end"] = capital + g.realized.cumsum()
    g["daily_return_pct"] = g.realized / g.eq_start * 100
    g["trading_day"] = g.trades > 0
    peak = g.eq_end.cummax(); g["drawdown_pct"] = (g.eq_end / peak - 1) * 100
    return g


def metrics(g: pd.DataFrame) -> dict:
    r = g.daily_return_pct / 100; td = g[g.trading_day]; rt = td.daily_return_pct / 100
    n_cal, n_td = len(g), len(td)
    mu_td = float(rt.mean()) if n_td else float("nan")
    se = float(rt.std(ddof=1) / math.sqrt(n_td)) if n_td > 2 else float("nan")
    geo = float((g.eq_end.iloc[-1] / g.eq_start.iloc[0]) ** (1 / n_cal) - 1)
    under = (g.eq_end < g.eq_end.cummax()).astype(int)
    run = (under.groupby((under != under.shift()).cumsum()).cumsum() * under).max()
    neg = (g.realized < 0).astype(int); streak = (neg.groupby((neg != neg.shift()).cumsum()).cumsum() * neg).max()
    return dict(calendar_days=n_cal, trading_days=n_td, mean_ret_trading_day_pct=round(mu_td * 100, 4), mean_ret_calendar_day_pct=round(float(r.mean()) * 100, 4),
                geo_daily_ret_pct=round(geo * 100, 4), cum_return_pct=round(float(g.eq_end.iloc[-1] / g.eq_start.iloc[0] - 1) * 100, 2),
                ci95_mean_trading_day_pct=f"[{(mu_td - 1.96 * se) * 100:.4f}, {(mu_td + 1.96 * se) * 100:.4f}]" if se == se else "",
                sharpe_daily_ann=round(float(r.mean() / r.std() * math.sqrt(252)), 2) if r.std() > 0 else float("nan"),
                pos_days=int((td.realized > 0).sum()), neg_days=int((td.realized < 0).sum()), worst_day_pct=round(float(td.daily_return_pct.min()), 3) if n_td else np.nan,
                best_day_pct=round(float(td.daily_return_pct.max()), 3) if n_td else np.nan, max_neg_streak_days=int(streak), max_underwater_days=int(run),
                max_dd_realized_pct=round(float(g.drawdown_pct.min()), 2), p_day_loss_gt_2pct=round(float((td.daily_return_pct < -2).mean()), 4) if n_td else np.nan,
                target_1pct_daily_ratio=round(mu_td / TARGET, 4) if mu_td == mu_td else np.nan, days_to_double_at_geo=round(math.log(2) / math.log(1 + geo), 0) if geo > 0 else "inf")


def main(prefixes):
    runs = sorted((ROOT / "results" / "v5_runs").glob("RUN_*"))
    summ, rows = [], []
    for rd in runs:
        if not (rd / "trades.csv").exists(): continue
        g = daily(rd)
        if g.empty: continue
        m = metrics(g); m["run_id"] = rd.name; summ.append(m)
        if any(rd.name.startswith(p) or p in rd.name for p in prefixes):
            x = g.reset_index().rename(columns={"index": "date"})
            x["run_id"] = rd.name; x["floating_pnl"] = "NO_DISPONIBLE"; x["intraday_dd"] = "NO_DISPONIBLE"
            x["day_type"] = np.where(~x.trading_day, "sin_operaciones", np.where(x.realized > 0, "positivo", "negativo"))
            rows.append(x)
    S = pd.DataFrame(summ).sort_values("cum_return_pct", ascending=False)
    S.to_csv(ROOT / "research" / "V7_DAILY_SUMMARY_V5_RUNS.csv", index=False)
    if rows:
        X = pd.concat(rows)[["run_id", "date", "eq_start", "eq_end", "realized", "floating_pnl", "daily_return_pct", "trades", "lots", "intraday_dd", "drawdown_pct", "costs", "swaps", "day_type"]]
        X.rename(columns={"eq_start": "equity_inicial", "eq_end": "equity_final", "realized": "beneficio_realizado", "floating_pnl": "beneficio_flotante", "daily_return_pct": "rentabilidad_diaria_pct",
                          "trades": "operaciones", "lots": "lotes_cerrados", "intraday_dd": "drawdown_intradia", "drawdown_pct": "drawdown_pct_cierre", "costs": "comisiones", "swaps": "swaps", "day_type": "tipo_de_dia"}).round(4).to_csv(
            ROOT / "research" / "DAILY_PROFITABILITY_ANALYSIS.csv", index=False)
    print(S.head(8)[["run_id", "cum_return_pct", "mean_ret_trading_day_pct", "mean_ret_calendar_day_pct", "target_1pct_daily_ratio", "max_dd_realized_pct"]].to_string())
    print("mejor media diaria por dia de negociacion:", S.mean_ret_trading_day_pct.max(), "| objetivo 1.0")


if __name__ == "__main__":
    main(sys.argv[1:] or ["RUN_20261109_ETHUSDm_M15_F1_SWEEP_REV_022", "RUN_20261109_XAUUSDm_M5_F1_SWEEP_REV_027"])

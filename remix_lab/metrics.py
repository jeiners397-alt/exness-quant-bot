"""Metricas obligatorias (seccion 7). Funciones puras sobre el DataFrame de operaciones."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _dd(balance: np.ndarray, start: float):
    eq = np.concatenate([[start], balance])
    peak = np.maximum.accumulate(eq)
    dd = peak - eq
    return float(dd.max()), float((dd / peak).max() * 100)


def _daily_returns(tr: pd.DataFrame, start: float) -> pd.Series:
    s = tr.set_index("exit_time")["balance"].resample("1D").last()
    s = s.ffill()
    s = pd.concat([pd.Series([start], index=[s.index[0] - pd.Timedelta(days=1)]), s])
    return s.pct_change().dropna()


def compute_metrics(tr: pd.DataFrame, initial_capital: float = 100.0) -> dict:
    if tr is None or tr.empty:
        return dict(trades=0, win_rate=np.nan, profit_factor=np.nan, expectancy_r=np.nan, net_profit=0.0,
                    return_pct=0.0, max_dd_money=0.0, max_dd_pct=0.0, sharpe=np.nan, sortino=np.nan,
                    total_costs=0.0, spread_cost=0.0, commission=0.0, swap=0.0, slippage_cost=0.0)
    w = tr[tr.net_money > 0].net_money.sum()
    ls = -tr[tr.net_money < 0].net_money.sum()
    pf = (w / ls) if ls > 0 else (np.inf if w > 0 else np.nan)
    ddm, ddp = _dd(tr["balance"].to_numpy(), initial_capital)
    sharpe = sortino = np.nan
    if len(tr) >= 2:
        dr = _daily_returns(tr, initial_capital)
        if len(dr) >= 30 and dr.std(ddof=1) > 0:
            sharpe = float(dr.mean() / dr.std(ddof=1) * np.sqrt(252))
            dn = dr[dr < 0]
            if len(dn) >= 2 and dn.std(ddof=1) > 0:
                sortino = float(dr.mean() / np.sqrt((dn ** 2).mean()) * np.sqrt(252))
    net = float(tr.net_money.sum())
    return dict(
        trades=int(len(tr)),
        win_rate=float((tr.net_money > 0).mean() * 100),
        profit_factor=float(pf),
        expectancy_r=float(tr.net_r.mean()),
        net_profit=net,
        return_pct=net / initial_capital * 100,
        max_dd_money=ddm, max_dd_pct=ddp,
        sharpe=sharpe, sortino=sortino,
        total_costs=float(tr.spread_cost.sum() + tr.commission.sum() + tr.slippage_cost.sum() - tr.swap.sum()),
        spread_cost=float(tr.spread_cost.sum()), commission=float(tr.commission.sum()),
        swap=float(tr.swap.sum()), slippage_cost=float(tr.slippage_cost.sum()),
        avg_risk_real_pct=float(tr.risk_real_pct.mean()),
    )


def breakdown(tr: pd.DataFrame, by: str, initial_capital: float = 100.0) -> pd.DataFrame:
    """Metricas por columna (dir, symbol, timeframe, sample, ...). Usa R y dinero por grupo."""
    rows = []
    for k, g in tr.groupby(by):
        m = compute_metrics(g.assign(balance=initial_capital + g.net_money.cumsum()), initial_capital)
        rows.append({by: k, **{x: m[x] for x in ("trades", "win_rate", "profit_factor", "expectancy_r", "net_profit",
                                                   "max_dd_pct", "total_costs")}})
    return pd.DataFrame(rows)


def assess(m_is: dict, m_oos: dict | None, mc: dict | None, criteria: dict) -> dict:
    """Checklist de validacion. Nunca se declara 'rentable' solo por beneficio."""
    chk = {
        "trades>=min": m_is["trades"] >= criteria["min_trades"],
        "PF>=min": bool(m_is["profit_factor"] >= criteria["min_profit_factor"]),
        "expectancy_R>=min": bool(m_is["expectancy_r"] >= criteria["min_expectancy_r"]),
        "maxDD<=max": m_is["max_dd_pct"] <= criteria["max_drawdown_pct"],
    }
    if m_oos is not None:
        chk["OOS_PF>=min"] = bool(m_oos["profit_factor"] >= criteria["min_oos_profit_factor"]) and m_oos["trades"] > 0
    if mc is not None and criteria.get("mc_p5_return_positive"):
        chk["MC_p5_return>0"] = bool(mc["return_pct_p5"] > 0)
    chk["_passes_all"] = all(chk.values())
    return chk

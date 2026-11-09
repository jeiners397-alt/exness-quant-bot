import pandas as pd
m = pd.read_csv("research/MULTI_MARKET_STRATEGY_MATRIX.csv")
blank = m.strategy.str.contains("realticks")
for c in ("max_margin_pct_symbol", "avg_lots", "max_lots", "signals", "rej_margin", "rej_risk", "rej_minlot", "skip_cost"):
    m.loc[blank, c] = ""
m.to_csv("research/MULTI_MARKET_STRATEGY_MATRIX.csv", index=False)
b = m[m.strategy.isin(["F1_SWEEP_REV", "F2_DONCHIAN_BO", "F3_ZSCORE_REV"])]
p = b.pivot_table(index="symbol", columns=["strategy", "timeframe"], values="net_profit")
print(p.round(0).to_string())
print(b.groupby("category").agg(n=("run_id", "count"), pos=("net_profit", lambda s: int((s > 0).sum())), medR=("expectancy_R_proxy", "median")).round(3))
print("max margen simbolo %:", pd.to_numeric(b.max_margin_pct_symbol, errors="coerce").max(), " lotes medios min/max:", pd.to_numeric(b.avg_lots, errors="coerce").min(), pd.to_numeric(b.avg_lots, errors="coerce").max())
print("trades total:", int(b.trades.sum()), " total ejecuciones:", len(m))
cols = ["run_id", "strategy", "symbol", "timeframe", "trades", "net_profit", "return_pct", "profit_factor", "win_rate_pct", "expectancy_R_proxy", "max_dd_equity_pct", "max_margin_pct_symbol", "class"]
c = m[cols].copy()
c["run_id"] = c.run_id.str.replace("RUN_20261109_", "", regex=False)
c.to_csv("research/V5_MATRIX_COMPACT.csv", index=False)
print(len(c), "filas compactas")

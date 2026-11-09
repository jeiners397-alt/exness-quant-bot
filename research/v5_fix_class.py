import pandas as pd
m = pd.read_csv("research/MULTI_MARKET_STRATEGY_MATRIX.csv")
i = m.strategy.str.contains("realticks")
m.loc[i, "class"] = "E"
m.loc[i, "status"] = "ERROR_DATOS"
m.loc[i, "classification_reason"] = "error tecnico: 'no history data, stop testing' (descarga de ticks reales cancelada); NO es ausencia de senales"
m.to_csv("research/MULTI_MARKET_STRATEGY_MATRIX.csv", index=False)
pd.set_option("display.width", 250)
print(m[m.strategy.str.contains("val|risk")][["strategy", "symbol", "trades", "net_profit", "profit_factor", "max_dd_equity_pct", "max_margin_pct_symbol", "avg_lots", "rej_risk", "class"]].to_string())
print(m["class"].value_counts().to_dict())

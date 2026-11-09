import pandas as pd

pd.set_option("display.width", 250)
E = pd.read_csv("research/V3_D_EVENTS.csv")
p = E.pivot_table(index=["tf", "cell"], columns="period", values="E_cons")[["TRAIN", "VALID", "EXPL"]].round(3)
n = E.pivot_table(index=["tf", "cell"], columns="period", values="n")[["TRAIN", "VALID", "EXPL"]]
pw = E.pivot_table(index=["tf", "cell"], columns="period", values="p_win")[["TRAIN", "VALID", "EXPL"]].round(3)
print(p.join(n, rsuffix="_n").join(pw, rsuffix="_pwin").to_string())
print(pd.read_csv("research/V3_D_WALKFORWARD.csv").to_string(index=False))
B = pd.read_csv("research/V3_D_BACKTESTS.csv")
print(B[B.period == "FULL"][["tf", "filtro", "n", "wr", "pf", "exp_R", "ci_block", "t", "maxdd_pct", "net_usd", "ctrl_p", "exp_R_ex5"]].to_string(index=False))
print(B.pivot_table(index=["tf", "filtro"], columns="period", values="exp_R")[["TRAIN", "VALID", "EXPL"]].round(3).to_string())

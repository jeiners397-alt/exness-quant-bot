import pandas as pd

pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 70)
R = pd.read_csv("research/V3_ALL_RUNS.csv")
F = R[R.period == "FULL"].copy()
F["p"] = F.params.str.replace('"', "").str.replace("{", "").str.replace("}", "").str.replace("sl_mode", "sl").str.replace("levels", "lv").str.replace("confirm", "cf")
w = R.pivot_table(index="cid", columns="period", values="exp_R")[["TRAIN", "VALID", "EXPL"]].round(3)
F = F.merge(w, left_on="cid", right_index=True, suffixes=("", "_p"))
print(F[["family", "tf", "p", "n", "wr", "pf", "exp_R", "t", "maxdd_pct", "q_pos", "q_total", "TRAIN", "VALID", "EXPL", "ctrl_p", "exp_R_ex5"]].round(3).to_string(index=False))
print(pd.read_csv("research/V3_WALKFORWARD_SUMMARY.csv").to_string(index=False))

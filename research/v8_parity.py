"""V8 Lote A - paridad Python vs Strategy Tester (senales y operaciones).
Uso: python -m research.v8_parity <tag> <variant A_V7_SWEEP_INV|B_CLOSE_OUTSIDE> <rr> <run_id>
Lee los CSV del EA (carpeta Common) y los copia a results/v8/<run_id>/; compara con la referencia Python."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
COMMON = Path(os.environ["APPDATA"]) / "MetaQuotes" / "Terminal" / "Common" / "Files"
OUT = ROOT / "results" / "v8"
FLOOR = "1h"                                     # frecuencia de la vela del TF (1h valido para H1/H4; "5min" para M5)


def load_ea(tag: str, run_id: str):
    d = OUT / run_id
    d.mkdir(parents=True, exist_ok=True)
    for kind in ("signals", "trades"):
        src = COMMON / f"REMIX_{tag}_{kind}.csv"
        if src.exists():
            shutil.copy2(src, d / f"ea_{kind}.csv")
    S = pd.read_csv(d / "ea_signals.csv") if (d / "ea_signals.csv").exists() else pd.DataFrame()
    T = pd.read_csv(d / "ea_trades.csv") if (d / "ea_trades.csv").exists() else pd.DataFrame()
    if len(T):
        T["open_time"] = pd.to_datetime(T.open_time, format="%Y.%m.%d %H:%M:%S"); T["close_time"] = pd.to_datetime(T.close_time, format="%Y.%m.%d %H:%M:%S")
        T["entry_bar"] = T.open_time.dt.floor(FLOOR)
    if len(S):
        S["signal_bar_time"] = pd.to_datetime(S.signal_bar_time, format="%Y.%m.%d %H:%M")
    return S, T


def compare(tag: str, variant: str, rr: float, run_id: str) -> dict:
    P = pd.read_csv(OUT / f"xau_h1_reference_{variant}_rr{rr}.csv", parse_dates=["entry_time", "exit_time", "signal_time"])
    S, T = load_ea(tag, run_id)
    P["entry_bar"] = P.entry_time
    m = P.merge(T, on="entry_bar", how="outer", suffixes=("_py", "_ea"), indicator=True)
    both = m[m._merge == "both"].copy()
    only_py, only_ea = m[m._merge == "left_only"], m[m._merge == "right_only"]
    both["dir_ok"] = both.dir_py == both.dir_ea
    both["entry_diff_ATR"] = (both.entry_py - both.entry_ea).abs() / both.atr
    both["reason_ok"] = both.reason == both.exit_reason
    both["R_diff"] = both.R_gross - both.R          # R del EA es bruto de comision (precio de salida / SL); se compara con R_gross de Python
    both["R_net_ea"] = both.profit / (both.sl_dist * 100 * both.volume)   # beneficio real en R (incluye spread/slippage de ejecucion)
    n_py, n_ea = len(P), len(T)
    # causas de las senales de Python que el EA no abrio
    causes = {}
    if len(S) and len(only_py):
        sb = S.set_index("signal_bar_time")
        for _, r in only_py.iterrows():
            k = r.signal_time
            causes[sb.decision.get(k, "SIN_SENAL_EA") if k in sb.index else "SIN_SENAL_EA"] = causes.get(sb.decision.get(k, "SIN_SENAL_EA") if k in sb.index else "SIN_SENAL_EA", 0) + 1
    summ = dict(run_id=run_id, variant=variant, rr=rr, n_python=n_py, n_ea=n_ea, matched=len(both), only_python=len(only_py), only_ea=len(only_ea),
                signal_overlap_pct=round(100 * len(both) / max(n_py, 1), 1), direction_agree_pct=round(100 * both.dir_ok.mean(), 1) if len(both) else np.nan,
                median_entry_diff_ATR=round(float(both.entry_diff_ATR.median()), 4) if len(both) else np.nan,
                exit_reason_agree_pct=round(100 * both.reason_ok.mean(), 1) if len(both) else np.nan,
                median_abs_R_diff=round(float(both.R_diff.abs().median()), 4) if len(both) else np.nan,
                sumR_python_net=round(float(P.R_net.sum()), 2), sumR_ea_gross=round(float(T.R.sum()), 2) if len(T) else np.nan,
                sumR_ea_net_money=round(float(both.R_net_ea.sum()), 2) if len(both) else np.nan,
                expR_python_net=round(float(P.R_net.mean()), 4), expR_ea_net_money=round(float((T.profit / (T.sl_dist * 100 * T.volume)).mean()), 4) if len(T) else np.nan,
                only_python_causes=str(causes))
    both.to_csv(OUT / run_id / "parity_matched.csv", index=False)
    only_py.to_csv(OUT / run_id / "parity_only_python.csv", index=False)
    only_ea.to_csv(OUT / run_id / "parity_only_ea.csv", index=False)
    return summ


if __name__ == "__main__":
    tag, variant, rr, rid = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
    r = compare(tag, variant, rr, rid)
    for k, v in r.items():
        print(k, "=", v)


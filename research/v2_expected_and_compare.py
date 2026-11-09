"""FASE 9: V1 (S01 canonico) vs modulos V2, 3000 USD, 0.5 %, estricto. Genera ademas los TRADES ESPERADOS DE PYTHON de cada modulo para
compararlos con el export CSV del Strategy Tester (results/v2_expected/). Todo exploratorio: EXPL = 2025-01..2026-10 (ya inspeccionado);
POOL = 2018..2026-10 (RETRO + EXPL). No es evidencia prospectiva."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab import harness as H  # noqa: E402
from remix_lab.strategies import generate  # noqa: E402
from remix_lab.strategies_d import GEN, resample, transform  # noqa: E402

F = H.load_frames()
H4n = pd.read_csv(ROOT / "data/raw/EURUSDm_H4.csv", parse_dates=["time"])                    # H4 NATIVO (identico a las barras de MT5)
H1_pool = pd.concat([F["RETRO"]["H1"], F["EXPL"]["H1"]]).reset_index(drop=True)
H4_pool = resample(H1_pool, "H4")
OUT = ROOT / "results" / "v2_expected"; OUT.mkdir(parents=True, exist_ok=True)

MODS = {
    "V1_S01_M15": ("M15", lambda d: generate("S01", d, H.SPEC, {})),
    "M05_S05_L2_H4": ("H4", lambda d: GEN["S05"](d, dict(z_th=2.0, trend_filter=True, sl_atr=2.0, max_bars=18))),
    "M06_S06_L3_H4": ("H4", lambda d: GEN["S06"](d, dict(rsi_lo=5, rsi_hi=95))),
    "M08_S08_L4_H4": ("H4", lambda d: GEN["S08"](d, dict(confirm=False, regime=True, max_bars=12))),
    "M11_L1_S03inv_H1": ("H1", lambda d: transform(generate("S03", d, H.SPEC, {}), "long_inv", "mirror")),
}
frames = {"EXPL": {"M15": F["EXPL"]["M15"], "H1": F["EXPL"]["H1"], "H4": H4n[(H4n.time >= "2025-01-01") & (H4n.time < "2026-11-01")].reset_index(drop=True)},
          "POOL": {"H1": H1_pool, "H4": H4_pool}}
rows = []
for name, (tf, fn) in MODS.items():
    for per in ("EXPL", "POOL"):
        if tf not in frames[per]:
            continue
        df = frames[per][tf]; sig = fn(df)
        r, tr = H.run(df, sig, dict(module=name, period=per, tf=tf), n_ctrl=200, hours_from_signals=(name.startswith("V1")))
        d2 = df.copy(); d2["spread"] *= 1.5
        from remix_lab.backtest import BacktestConfig, run_backtest
        t2, _ = run_backtest(d2, sig, H.SPEC, BacktestConfig(H.CAP, H.RISK, "strict", 0.0, 10.0))
        r["expR_stress"] = round(float(t2.net_r.mean()), 4) if len(t2) else np.nan
        r["pf_stress"] = round(float(t2.net_money[t2.net_money > 0].sum() / max(-t2.net_money[t2.net_money < 0].sum(), 1e-9)), 3) if len(t2) else np.nan
        r["years"] = round(((pd.to_datetime(tr.exit_time.iloc[-1]) - pd.to_datetime(tr.entry_time.iloc[0])).days / 365.25), 2) if len(tr) else np.nan
        r["trades_per_year"] = round(r["n"] / r["years"], 1) if r.get("years") else np.nan
        r["usd_per_year"] = round(r["net_usd"] / r["years"], 1) if r.get("years") else np.nan
        rows.append(r)
        if per == "EXPL":
            tr[["entry_time", "exit_time", "dir", "lots", "entry", "exit", "exit_reason", "sl_dist", "tp_dist", "net_r", "net_money", "balance"]].to_csv(OUT / f"{name}_EXPL_expected_trades.csv", index=False)
        print(name, per, r["n"], r["pf"], r["exp_R"], r["t"], r.get("ctrl_p"), flush=True)
R = pd.DataFrame(rows)
for c in ("ci_block", "ci_boot"):
    R[c] = R[c].astype(str)
R.to_csv(ROOT / "research/V2_VS_V1_COMPARISON.csv", index=False)
cols = ["module", "period", "n", "wr", "pf", "exp_R", "ci_block", "t", "net_usd", "ret_pct", "maxdd_pct", "recovery", "payoff", "cost_R", "gross_R", "expR_stress", "pf_stress", "q_pos", "q_total", "exp_R_ex5", "trades_per_year", "usd_per_year", "ctrl_p"]
pd.set_option("display.width", 300)
print(R[cols].to_string(index=False))

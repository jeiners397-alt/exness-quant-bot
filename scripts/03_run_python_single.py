"""Simulacion individual en Python (motor propio). Por defecto SOLO en muestra (nunca toca el holdout)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from remix_lab import load_config, RESULTS_DIR  # noqa: E402
from remix_lab import experiments as ex, data_engine as de  # noqa: E402
from remix_lab.report import save_trades, strategy_report  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--strategy", default="S01")
ap.add_argument("--symbol", default="EURUSDm")
ap.add_argument("--tf", default="M15")
ap.add_argument("--start", default="2025-01-01")
ap.add_argument("--end", default="2025-03-31")
ap.add_argument("--sizing", default=None, choices=["strict", "min_lot", "ideal"])
ap.add_argument("--slippage", type=float, default=None)
ap.add_argument("--note", default="")
a = ap.parse_args()

cfg = load_config()
_, is_end, h_start, _ = ex.split_dates(cfg)
if a.end > is_end:
    sys.exit(f"RECHAZADO: --end {a.end} invade el holdout (>{is_end}).")
over = {k: v for k, v in dict(sizing_policy=a.sizing, slippage_points=a.slippage).items() if v is not None}
bt = ex.bt_config(cfg, **over)
df = de.load_rates(a.symbol, a.tf, a.start, a.end)
print(f"datos: {len(df)} barras {df.time.iloc[0]} -> {df.time.iloc[-1]}")
tr, m, info = ex.run_one(a.strategy, a.symbol, a.tf, {}, a.start, a.end, cfg, stage="single", df=df, bt=bt, note=a.note)
name = f"py_{a.strategy}_{a.symbol}_{a.tf}_{a.start}_{a.end}_{bt.sizing_policy}"
if not tr.empty:
    save_trades(tr, name)
print(strategy_report(tr, name) if not tr.empty else "SIN OPERACIONES")
print("omitidas:", info["skipped"], "| swap modelado:", info["swap_modeled"])

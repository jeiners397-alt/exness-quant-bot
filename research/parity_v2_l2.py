"""PARIDAD Python-MT5 de V2 / L2 (S05 H4). Oficial = export del Strategy Tester del usuario (deals + log de senales del EA).
Ablacion acumulativa de correcciones, SIN tocar parametros estrategicos. Salida: research/PARITY_V2_L2_*.csv/json"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab import harness as H  # noqa: E402
from remix_lab.backtest import BacktestConfig, run_backtest  # noqa: E402
from remix_lab.strategies import Signals  # noqa: E402
from remix_lab.strategies_d import GEN  # noqa: E402

COMMON = Path.home() / "AppData/Roaming/MetaQuotes/Terminal/Common/Files"
DEALS = ROOT / "results/v2_official/REMIX_V2_deals_M05_EURUSDm_PERIOD_H4.csv"
SIGS = ROOT / "results/v2_official/REMIX_V2_signals_M05_EURUSDm_PERIOD_H4.csv"
START = pd.Timestamp("2025-01-01"); END = pd.Timestamp("2026-11-01")
P = dict(z_th=2.0, trend_filter=True, sl_atr=2.0, max_bars=18)        # L2 congelada


def load_official():
    d = pd.read_csv(DEALS)
    d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S")
    ins, outs = d[d.entry == 0].reset_index(drop=True), d[d.entry == 1].reset_index(drop=True)
    assert len(ins) == len(outs)
    t = pd.DataFrame({"entry_time": ins.time, "dir": np.where(ins.type == 0, 1, -1), "lots": ins.volume, "entry": ins.price, "exit_time": outs.time, "exit": outs.price,
                      "profit": outs.profit, "swap": outs.swap, "comment": outs.comment.fillna("")})
    t["reason"] = np.where(t.comment.str.startswith("sl"), "sl", np.where(t.comment.str.startswith("tp"), "tp", "max_bars"))
    t["net"] = t.profit + t.swap
    s = pd.read_csv(SIGS)
    s["time"] = pd.to_datetime(s["time"], format="%Y.%m.%d %H:%M:%S")
    op = s[s.event == "OPEN"].reset_index(drop=True)
    assert len(op) == len(t), (len(op), len(t))
    t["sl_dist"], t["tp_dist"], t["spread_pts_log"] = op.sl_dist.values, op.tp_dist.values, op.spread_pts.values
    return t, s


def add_session_columns(h4):
    """Modelo de sesion (evidencia: log del EA y diario del Tester). gate_spread = spread de la PRIMERA barra M15 dentro de la barra H4 (proxy del primer tick);
    no_trade_at_open = barra H4 que abre tras un hueco de mercado cuyo primer dato M15 es anterior a las 22:00 (diario del Tester: 4/4 cierres de domingo
    a las 21:05 fallaron con [Market closed]; los de las 22:05 se ejecutaron). Solo hay M15 desde nov-2022; antes se usa el spread de la barra H4."""
    m15 = pd.read_csv(ROOT / "data/raw/hist/EURUSDm_M15_pre2025.csv", parse_dates=["time"])
    m15 = pd.concat([m15, pd.read_csv(ROOT / "data/raw/EURUSDm_M15.csv", parse_dates=["time"])]).drop_duplicates("time").sort_values("time")
    m15["blk"] = m15.time.dt.floor("4h")
    first = m15.groupby("blk").agg(first_t=("time", "min"), first_spr=("spread", "first"))
    out = h4.join(first, on="time")
    out["gate_spread"] = out.first_spr.fillna(out.spread)
    gap_open = (out.first_t - out.time) >= pd.Timedelta(hours=1)
    out["no_trade_at_open"] = (gap_open & (out.first_t.dt.hour < 22)).fillna(False)
    return out.drop(columns=["first_t", "first_spr"])


def python_run(h4, warmup=True, gates=False, adx="mt5", reenter=False, calendar=False, gap_skip=False, session=False, n_ctrl=0):
    p = {**P, "adx_impl": adx}
    sig = GEN["S05"](h4 if warmup else h4[h4.time >= START].reset_index(drop=True), p)
    df = h4 if warmup else h4[h4.time >= START].reset_index(drop=True)
    # evaluacion desde el primer bar >= START; la senal de la ultima barra previa SI puede entrar (como el Tester, que precarga historia)
    j0 = int(np.searchsorted(df.time.values, np.datetime64(START)))
    i0 = max(j0 - 1, 0)
    e = int(np.searchsorted(df.time.values, np.datetime64(END)))
    if session:
        df = add_session_columns(df)
    sub = df.iloc[i0:e].reset_index(drop=True)
    s2 = Signals(sig.direction[i0:e], sig.sl_dist[i0:e], sig.tp_dist[i0:e], None, sig.max_bars)
    cfg = BacktestConfig(3000.0, 0.5, "strict", 0.0, 0.0, True,
                         max_spread_frac_sl=0.15 if gates else None, max_spread_points=30 if gates else None,
                         reenter_after_open_exit=reenter, max_bars_mode="calendar" if calendar else "bars", bar_seconds=14400, skip_entry_after_gap=gap_skip)
    tr, info = run_backtest(sub, s2, H.SPEC, cfg)
    tr["bars_py"] = tr.bars_held
    tr["entry_time"] = pd.to_datetime(tr.entry_time)
    return tr, info


def match(py, off):
    a, b = set(py.entry_time), set(off.entry_time)
    return dict(n_py=len(py), n_mt5=len(off), matched=len(a & b), only_py=len(a - b), only_mt5=len(b - a))


def main():
    off, sigs = load_official()
    full = pd.read_csv(ROOT / "data/raw/hist/EURUSDm_H4_native_2022_2026.csv", parse_dates=["time"])
    full.loc[full.spread <= 0, "spread"] = full.spread[full.spread > 0].median()
    steps = [("0 Python original (serie recortada a 2025, sin compuertas, ADX Wilder)", dict(warmup=False, gates=False, adx="wilder")),
             ("1 + warm-up previo a 2025 (serie completa)", dict(warmup=True, gates=False, adx="wilder")),
             ("2 + compuertas spread 0.15xSL y 30 pts en la barra de entrada", dict(warmup=True, gates=True, adx="wilder")),
             ("3 + ADX con la formula MT5 (EMA 2/(n+1) de cocientes)", dict(warmup=True, gates=True, adx="mt5")),
             ("4 + reentrada en la misma barra tras salida a la apertura", dict(warmup=True, gates=True, adx="mt5", reenter=True)),
             ("5 + max_bars calendario (comportamiento del EA V2)", dict(warmup=True, gates=True, adx="mt5", reenter=True, calendar=True)),
             ("6 + modelo de sesion: spread del primer tick (M15) en compuertas/cierres y mercado cerrado antes de las 22:00 (ver informe)", dict(warmup=True, gates=True, adx="mt5", reenter=True, calendar=True, session=True))]
    rows, final = [], None
    for name, kw in steps:
        tr, info = python_run(full, **kw)
        m = match(tr, off)
        first = sorted(set(tr.entry_time) ^ set(off.entry_time))
        rows.append({"paso": name, **m, "primera_divergencia": str(first[0]) if first else "ninguna", "net_usd_py": round(float(tr.net_money.sum()), 2), "swap_py": round(float(tr.swap.sum()), 2), "skipped": json.dumps(info["skipped"])})
        final = tr
        print(rows[-1], flush=True)
    R = pd.DataFrame(rows); R.to_csv(ROOT / "research/PARITY_V2_L2_ABLATION.csv", index=False)
    # comparacion operacion a operacion con el ultimo paso
    py = final.copy()
    J = off.merge(py, on="entry_time", how="outer", suffixes=("_mt5", "_py"), indicator=True)
    J.to_csv(ROOT / "research/PARITY_V2_L2_TRADES.csv", index=False)
    b = J[J._merge == "both"]
    cmp_ = dict(
        n_matched=len(b), dir_equal=int((b.dir_mt5 == b.dir_py).sum()),
        entry_price_diff_pts_median=round(float(((b.entry_mt5 - b.entry_py) / 1e-5).median()), 2), entry_price_exact=int(((b.entry_mt5 - b.entry_py).abs() < 1e-9).sum()),
        sl_dist_diff_pts_median=round(float(((b.sl_dist_mt5 - b.sl_dist_py).abs() / 1e-5).median()), 2), sl_dist_exact_1pt=int(((b.sl_dist_mt5 - b.sl_dist_py).abs() < 1.5e-5).sum()),
        tp_dist_diff_pts_median=round(float(((b.tp_dist_mt5 - b.tp_dist_py).abs() / 1e-5).median()), 2),
        lots_equal=int((b.lots_mt5 == b.lots_py).sum()),
        reason_equal=int((b.reason == b.exit_reason.map({"sl": "sl", "sl_gap": "sl", "tp": "tp", "max_bars": "max_bars", "end_of_data": "end"})).sum()),
        exit_time_equal=int((pd.to_datetime(b.exit_time_mt5).dt.floor("4h") == pd.to_datetime(b.exit_time_py).dt.floor("4h")).sum()),
        net_mt5_matched=round(float(b.net.sum()), 2), net_py_matched=round(float(b.net_money.sum()), 2),
        swap_mt5_matched=round(float(b.swap_mt5.sum()), 2), swap_py_matched=round(float(b.swap_py.sum()), 2))
    cmp_["net_mt5_all"] = round(float(off.net.sum()), 2); cmp_["swap_mt5_all"] = round(float(off.swap.sum()), 2)
    (ROOT / "research/PARITY_V2_L2_SUMMARY.json").write_text(json.dumps({"ablation": rows, "matched_trades_comparison": cmp_}, indent=1, default=str), encoding="utf-8")
    print(json.dumps(cmp_, indent=1))
    return off, sigs, full


if __name__ == "__main__":
    main()



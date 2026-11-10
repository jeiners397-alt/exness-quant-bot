"""V8 Lote A - consolida paridad, resultados oficiales, analisis de operaciones, robustez y rentabilidad diaria del EA REMIX_V8_XAU_BREAKOUT.
Todo sale de informes oficiales del Strategy Tester + CSV del EA. La parte 'modelado' (costes x1.5/x2, bootstrap, Monte Carlo) se marca MODELADO."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research import v8_parity as P

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "research"
RUNS = ROOT / "results" / "v4_runs"
V8 = ROOT / "results" / "v8"
RNG = np.random.default_rng(20261110)
CAP = 3000.0
D0, D1 = pd.Timestamp("2024-01-01"), pd.Timestamp("2026-10-31")

# run_id -> (tag, rr, model, nota)
SEQ = {5: ("V8A0_RR1.5_ohlc_1m", 1.5, "OHLC 1 min", "referencia"),
       6: ("V8A0_RR3.0_ohlc_1m", 3.0, "OHLC 1 min", "segundo TP prefijado"),
       7: ("V8A0_RR1.5_every_tick", 1.5, "Cada tick (generado)", "comparacion de modelado"),
       8: ("V8A0_RR1.5_real_ticks", 1.5, "Ticks reales (calidad 9%)", "ticks reales SOLO parcialmente disponibles"),
       9: ("V8A0_RR1.5_delay500", 1.5, "OHLC 1 min + ExecutionMode=500", "sin efecto medible"),
       10: ("V8A0_RR1.5_delay-1", 1.5, "OHLC 1 min + ExecutionMode=-1", "sin efecto medible"),
       11: ("V8A0_RR1.5_delay2000", 1.5, "OHLC 1 min + ExecutionMode=2000", "sin efecto medible"),
       12: ("V8H4A1_RR2.0_ohlc_1m", 2.0, "OHLC 1 min", "XAU H4 breakout20 (lote B, pista clase C)"),
       13: ("V8H4A1_RR3.0_ohlc_1m", 3.0, "OHLC 1 min", "XAU H4 breakout20 (lote B, pista clase C)")}


def rid_of(n: int) -> str:
    return next(p.name for p in RUNS.iterdir() if p.name.startswith("RUN_20261110_XAUUSDm_H") and "V8_XAU_BREAKOUT" in p.name and p.name.endswith(f"_{n:03d}"))


def official() -> pd.DataFrame:
    rows = []
    for n, (tag, rr, model, nota) in SEQ.items():
        rid = rid_of(n)
        s = json.load(open(RUNS / rid / "stats.json")); s = s.get("stats", s)
        tr = pd.read_csv(RUNS / rid / "trades.csv")
        days = (D1 - D0).days + 1
        net = s["total_net_profit"]; n_tr = int(s["total_trades"])
        rows.append(dict(run_id=rid, tag=tag, symbol="XAUUSDm", timeframe=("H4" if n >= 12 else "H1"), model=model, rr=rr, period="2024-01-01..2026-10-31", capital=CAP, leverage=500, trades=n_tr, net_profit=net,
                         return_pct=round(100 * net / CAP, 2), profit_factor=s["profit_factor"], expected_payoff_usd=s["expected_payoff"], win_rate_pct=s["profit_trades_pct"], equity_dd_pct=s["equity_dd_max_pct"],
                         balance_dd_pct=s["balance_dd_max_pct"], sharpe_tester=s["sharpe_ratio"], history_quality_pct=s["history_quality"], ticks=int(s["ticks"]), max_consec_losses=int(s["max_consec_losses"]),
                         mean_pct_per_calendar_day=round(100 * net / CAP / days, 4), nota=nota,
                         origen="informe oficial MT5 (Strategy Tester aislado), EA REMIX_V8_XAU_BREAKOUT, lote fijo 0.01", report_html=str(RUNS / rid / "report.htm")))
    O = pd.DataFrame(rows)
    O.to_csv(RES / "V8_XAU_H1_OFFICIAL_RESULTS.csv", index=False)
    return O


def parity() -> pd.DataFrame:
    rows = []
    for n, rr, vv in ((5, 1.5, "A_V7_SWEEP_INV"), (6, 3.0, "A_V7_SWEEP_INV"), (12, 2.0, "H4A1"), (13, 3.0, "H4A1")):
        rid = rid_of(n)
        r = P.compare(SEQ[n][0], vv, rr, rid)
        r["explicacion_only_python"] = ("6 entradas en horas 22-23/02 UTC con mercado cerrado (retcode 10018) + 1 rechazada por tope de riesgo 3% (ATR extremo)")
        r["explicacion_only_ea"] = ("2 al inicio (Python no tiene 96 velas previas: su serie empieza 2024-01-01) y 1 en 2026-10-30 (Python descarta senales sin 40 velas posteriores)")
        r["explicacion_R"] = ("R por nivel identico (SL-SL, TP-TP). Diferencia: 5 operaciones TP en Python que el EA cerro en SL (-2.5R cada una): en cortos el SL se activa con ASK y Python usa barras BID; +1 TIME->SL. "
                              "El coste de spread de Python (restado) y el efecto real (stops por ask) no son identicos")
        rows.append(r)
    D = pd.DataFrame(rows)
    D.to_csv(RES / "V8_XAU_H1_PARITY.csv", index=False)
    return D


def mdd(pnl: np.ndarray) -> float:
    b = CAP + np.cumsum(pnl); pk = np.maximum.accumulate(np.r_[CAP, b])[1:]
    return float(((pk - b) / pk).max() * 100)


def block_boot(x: np.ndarray, B=5000, L=8) -> tuple[float, float, float]:
    n = len(x); m = []
    for _ in range(B):
        idx = []
        while len(idx) < n:
            s = RNG.integers(0, n); idx += [(s + k) % n for k in range(L)]
        m.append(x[idx[:n]].mean())
    m = np.array(m)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)), float((m <= 0).mean())


def analysis() -> dict:
    out = {}
    rows = []
    for n in (5, 6, 12, 13):
        tag, rr, _, _ = SEQ[n]; rid = rid_of(n)
        T = pd.read_csv(V8 / rid / "ea_trades.csv")
        T["open_time"] = pd.to_datetime(T.open_time, format="%Y.%m.%d %H:%M:%S"); T["close_time"] = pd.to_datetime(T.close_time, format="%Y.%m.%d %H:%M:%S")
        T["pnl"] = T.profit + T.commission + T.swap   # incluye swap y comision (el neto del tester los incluye)
        T["year"] = T.open_time.dt.year; T["win"] = T.pnl > 0
        T["R_money"] = T.pnl / (T.sl_dist * 100 * T.volume)
        T["session"] = pd.cut(T.hour_entry, [-1, 6, 12, 16, 23], labels=["asia(0-6)", "londres(7-12)", "ny(13-16)", "tarde(17-23)"])
        T.to_csv(V8 / rid / "trade_analysis.csv", index=False)
        x = T.R_money.values; k = len(x)
        t = x.mean() / (x.std(ddof=1) / np.sqrt(k))
        lo, hi, p0 = block_boot(x)
        top5 = np.sort(x)[:-5]
        # Monte Carlo: reordenacion aleatoria de los P&L en USD -> distribucion del DD
        pn = T.pnl.values; dds = np.array([mdd(RNG.permutation(pn)) for _ in range(5000)])
        # costes MODELADOS: coste extra = (mult-1) * spread_entry (precio) * 100 oz * lote, por operacion (el spread de salida no se modela)
        spr_usd = T.spread_pts_entry * 0.001 * 100 * T.volume
        sc = {m: float((T.pnl - (m - 1) * spr_usd).sum()) for m in (1.0, 1.5, 2.0, 3.0)}
        swap_total = float(T.swap.sum())
        is_ = T[T.open_time < "2025-07-01"].R_money; oos = T[T.open_time >= "2025-07-01"].R_money
        res = dict(tf=("H4" if n >= 12 else "H1"), rr=rr, run_id=rid, n=k, expR_money=round(x.mean(), 4), t_stat=round(t, 2), boot95_lo=round(lo, 4), boot95_hi=round(hi, 4), p_boot_mean_le0=round(p0, 4),
                   expR_drop_top5_wins=round(float(top5.mean()), 4), mc_dd_p50=round(float(np.median(dds)), 2), mc_dd_p95=round(float(np.percentile(dds, 95)), 2), mc_dd_p99=round(float(np.percentile(dds, 99)), 2),
                   net_cost_x1=round(sc[1.0], 1), net_cost_x1p5=round(sc[1.5], 1), net_cost_x2=round(sc[2.0], 1), net_cost_x3=round(sc[3.0], 1),
                   pf_cost_x2=round(float((T.pnl - spr_usd).clip(lower=0).sum() / -(T.pnl - spr_usd).clip(upper=0).sum()), 3), swap_total_usd=round(swap_total, 2), net_pnl_usd=round(float(T.pnl.sum()), 2),
                   expR_IS=round(is_.mean(), 4), n_IS=len(is_), expR_OOS=round(oos.mean(), 4), n_OOS=len(oos),
                   by_year={int(y): dict(n=int(len(g)), net=round(float(g.pnl.sum()), 1), expR=round(float(g.R_money.mean()), 3)) for y, g in T.groupby("year")},
                   by_dir={int(d): dict(n=int(len(g)), net=round(float(g.pnl.sum()), 1), expR=round(float(g.R_money.mean()), 3)) for d, g in T.groupby("dir")},
                   by_session={str(s): dict(n=int(len(g)), net=round(float(g.pnl.sum()), 1), expR=round(float(g.R_money.mean()), 3)) for s, g in T.groupby("session", observed=True)},
                   by_exit={str(s): dict(n=int(len(g)), net=round(float(g.pnl.sum()), 1)) for s, g in T.groupby("exit_reason")},
                   winners=dict(n=int(T.win.sum()), mfe_R_med=round(float(T[T.win].mfe_R.median()), 2), bars_med=float(T[T.win].bars_held.median())),
                   losers=dict(n=int((~T.win).sum()), mfe_R_med=round(float(T[~T.win].mfe_R.median()), 2), mae_R_med=round(float(T[~T.win].mae_R.median()), 2), bars_med=float(T[~T.win].bars_held.median()),
                               pct_losers_that_reached_1R_mfe=round(float((T[~T.win].mfe_R >= 1.0).mean() * 100), 1)),
                   margin_max_usd=round(float(T.margin.max()), 2), margin_pct_eq_max=round(float(T.margin.max() / CAP * 100), 2), risk_usd_med=round(float(T.risk_money.median()), 2), risk_usd_max=round(float(T.risk_money.max()), 2),
                   MODELADO="costes x1.5/x2/x3, bootstrap por bloques (L=8, 5000), Monte Carlo (5000 reordenaciones): modelado sobre las operaciones oficiales del tester, no ejecuciones del tester")
        rows.append(res)
        # ---- rentabilidad diaria con trades oficiales
        cal = pd.date_range(D0, D1, freq="D"); dpl = T.groupby(T.close_time.dt.normalize()).pnl.sum().reindex(cal, fill_value=0.0)
        bal = CAP + dpl.cumsum(); ret = dpl / bal.shift(1).fillna(CAP)
        tdays = cal[cal.dayofweek < 5]
        rt = ret.loc[tdays]
        pk = bal.cummax(); uw = (bal < pk); streak = (uw.groupby((~uw).cumsum()).cumsum()).max()
        daily = dict(tf=("H4" if n >= 12 else "H1"), rr=rr, run_id=rid, calendar_days=len(cal), trading_days_mon_fri=len(tdays), mean_daily_ret_calendar_pct=round(float(ret.mean() * 100), 4), mean_daily_ret_trading_day_pct=round(float(rt.mean() * 100), 4),
                     geometric_daily_pct=round(float(((bal.iloc[-1] / CAP) ** (1 / len(cal)) - 1) * 100), 4), cumulative_pct=round(float((bal.iloc[-1] / CAP - 1) * 100), 2),
                     pct_days_with_close_positive=round(float((dpl > 0).sum() / max((dpl != 0).sum(), 1) * 100), 1), days_with_closed_trades=int((dpl != 0).sum()),
                     pct_trading_days_negative=round(float((rt < 0).mean() * 100), 1), worst_day_pct=round(float(ret.min() * 100), 3), best_day_pct=round(float(ret.max() * 100), 3),
                     max_dd_balance_pct=round(float(((pk - bal) / pk).max() * 100), 2), longest_underwater_days=int(streak), sharpe_daily_ann=round(float(ret.mean() / ret.std() * np.sqrt(252)), 2) if ret.std() > 0 else np.nan,
                     fraction_of_1pct_target=round(float(rt.mean() / 0.01), 4), days_to_reach_1pct_at_this_rate=round(float(0.01 / rt.mean()), 1) if rt.mean() > 0 else np.nan,
                     nota="beneficio REALIZADO por fecha de cierre; el PnL flotante intradia no se exporta en el informe (DD de equidad intradia: ver equity_dd_pct en OFFICIAL_RESULTS)")
        out[n] = daily
        dd = pd.DataFrame(dict(date=cal, pnl=dpl.values, balance=bal.values, ret_pct=(ret * 100).values)); dd.insert(0, "rr", rr); dd.insert(1, "run_id", rid)
        dd.to_csv(V8 / rid / "daily.csv", index=False)
    pd.DataFrame(rows).to_json(V8 / "xau_h1_trade_analysis.json", orient="records", indent=1)
    pd.DataFrame(list(out.values())).to_csv(RES / "V8_DAILY_PROFITABILITY.csv", index=False)
    return dict(analysis=rows, daily=out)


if __name__ == "__main__":
    O = official(); print(O[["tag", "trades", "net_profit", "profit_factor", "equity_dd_pct", "history_quality_pct"]].to_string())
    D = parity(); print(D[["rr", "n_python", "n_ea", "matched", "only_python", "only_ea", "exit_reason_agree_pct", "sumR_python_net", "sumR_ea_gross"]].to_string())
    A = analysis()
    for r in A["analysis"]:
        print(json.dumps(r, default=str)[:2600])
    print(json.dumps(A["daily"], default=str, indent=1)[:2500])



"""Lote multimercado: ESTRATEGIA x SIMBOLO x TIMEFRAME x PERIODO con el ejecutor V4 (instancia aislada). Parametros congelados por familia (sin optimizar por activo).
Cada fila de research/MULTI_MARKET_STRATEGY_MATRIX.csv proviene de un informe oficial del Strategy Tester. Reanuda desde el checkpoint."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation import drive_backup  # noqa: E402
from automation.compile_ea import compile_ea  # noqa: E402
from automation.parse_mt5_report import parse_report  # noqa: E402
from automation.run_mt5_test import LAB, run_id, run_test  # noqa: E402

MATRIX = ROOT / "research" / "MULTI_MARKET_STRATEGY_MATRIX.csv"
RUNS = ROOT / "results" / "v5_runs"
EA_SRC = ROOT / "mql5" / "REMIX_V5_GENERIC.mq5"
FAMILIES = {"F1_SWEEP_REV": 1, "F2_DONCHIAN_BO": 2, "F3_ZSCORE_REV": 3}
FROZEN = dict(MarginPct=5.0, GlobalMarginPct=15.0, RiskPercent=0.5, MaxTotalRiskPct=5.0, CheckPendingOrders="true", AllowMultiple="false", MaxPositions=5,
              CostGateR=0.10, HourFrom=0, HourTo=24, ATR_N=14, F1_MinSweepATR=0.1, F1_BufATR=0.1, F1_RR=1.5, F1_SLMinATR=0.5, F1_SLMaxATR=3.0,
              F2_MinRangeATR=1.0, F2_SL_ATR=1.5, F2_RR=2.0, F3_Z=2.5, F3_SL_ATR=2.0, F3_RR=1.0)
TF_PARAMS = {"M5": dict(MaxHoldBars=96, F2_N=96, F3_N=50), "M15": dict(MaxHoldBars=48, F2_N=48, F3_N=50)}
COLS = ["run_id", "strategy", "symbol", "category", "timeframe", "from_date", "to_date", "capital", "leverage", "model", "trades", "net_profit", "return_pct", "profit_factor", "win_rate_pct",
        "expectancy_R_proxy", "max_dd_equity_pct", "sharpe", "recovery_factor", "max_margin_pct_symbol", "avg_lots", "max_lots", "signals", "rej_margin", "rej_risk", "rej_minlot", "skip_cost",
        "history_quality", "bars_in_test", "period_in_log", "symbol_in_log", "status", "class", "classification_reason", "report_path"]


def agent_summary() -> tuple[str, str]:
    logs = sorted((LAB / "Tester").glob("Agent-*/logs/*.log"), key=lambda p: p.stat().st_mtime)
    init = summ = ""
    for lg in logs[-1:]:
        b = lg.read_bytes()
        t = b.decode("utf-16", errors="ignore") if b[:2] == b"\xff\xfe" else b.decode("utf-8", errors="ignore")
        for ln in t.splitlines():
            if "REMIX V5 init" in ln: init = ln
            if "REMIX V5 resumen" in ln: summ = ln
    return init, summ


def classify(trades: int, pf, net, exp_r, status: str, bars_hq) -> tuple[str, str]:
    if status in ("SIN_INFORME", "TIMEOUT", "INFORME_INCOMPLETO", "ERROR_INICIO"):
        return "E", f"error tecnico: {status}"
    if status == "SIN_OPERACIONES" or trades == 0:
        return "D", "sin operaciones (ausencia de senales o rechazo por margen/riesgo/coste)"
    if trades < 30:
        return ("B" if (net or 0) > 0 else "C"), f"{trades} operaciones (<30): estadisticamente insuficiente"
    if (net or 0) > 0 and (pf or 0) > 1.2:
        return "B", f"positivo (PF {pf}, {trades} ops) pero una sola ejecucion sin validacion: NO evidencia (A requiere walk-forward/control)"
    return "C", f"negativo o marginal (neto {net}, PF {pf})"


def run_batch(symbols: dict[str, str], families: list[str], tfs: list[str], from_date: str, to_date: str, model="ohlc_1m", timeout=2400, limit: int | None = None) -> None:
    c = compile_ea(EA_SRC)
    assert c["ok"], c
    done = {r["run_id"] for r in _rows()}
    seen = {(r["strategy"], r["symbol"], r["timeframe"], r["from_date"], r["to_date"]) for r in _rows()}
    n = 0
    for fam in families:
        for tf in tfs:
            for sym, cat in symbols.items():
                if (fam, sym, tf, from_date, to_date) in seen:
                    continue
                if limit and n >= limit:
                    return
                n += 1
                inputs = dict(FROZEN, Family=FAMILIES[fam], EnableTrading="true", MagicNumber=20260501, **TF_PARAMS[tf])
                rid = run_id(sym, tf, fam, len(_rows()) + 1)
                meta = run_test(rid=rid, expert="REMIX\\REMIX_V5_GENERIC", symbol=sym, period=tf, from_date=from_date, to_date=to_date, inputs=inputs, strategy=fam,
                                deposit=3000.0, leverage=500, model=model, timeout=timeout, ea_version="V5 " + c["sha256_src"][:12])
                _record(meta, cat, tf, fam, sym)


def _rows() -> list[dict]:
    if not MATRIX.exists():
        return []
    with MATRIX.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _record(meta: dict, cat: str, tf: str, fam: str, sym: str) -> None:
    rid = meta["run_id"]
    out = ROOT / "results" / "v4_runs" / rid                      # el ejecutor escribe aqui; se mueve a v5_runs
    st, trades_df = {}, None
    if meta["status"] in ("OK", "SIN_OPERACIONES") and meta.get("report"):
        pr = parse_report(Path(meta["report"]), out)
        st = pr["stats"]
        tp = out / "trades.csv"
        trades_df = pd.read_csv(tp) if tp.exists() else None
        if trades_df is not None:
            net = (trades_df.profit + trades_df.commission.fillna(0) + trades_df.swap.fillna(0)).sum()
            if st.get("total_net_profit") is not None and abs(net - st["total_net_profit"]) > 0.02:
                meta["status"] = "INCONSISTENTE"
    init, summ = agent_summary()
    g = lambda pat, s: (re.search(pat, s).group(1) if re.search(pat, s) else "")
    n = int(st.get("total_trades") or 0)
    avg_loss, exp = st.get("avg_loss"), st.get("expected_payoff")
    exp_r = round(exp / abs(avg_loss), 4) if exp is not None and avg_loss else ""
    cl, why = classify(n, st.get("profit_factor"), st.get("total_net_profit"), exp_r, meta["status"], st.get("history_quality"))
    if init and (g(r"period=(\w+)", init) != f"PERIOD_{tf}" or g(r"symbol=(\S+)", init) != sym):
        cl, why = "E", f"el log del EA no coincide con el simbolo/timeframe pedidos ({g(r'symbol=(\S+)', init)}, {g(r'period=(\w+)', init)})"
    tl = out / "tester_log.txt"
    if cl == "D" and tl.exists() and "no history data" in tl.read_bytes().decode("utf-16", errors="ignore") + tl.read_bytes().decode("utf-8", errors="ignore"):
        cl, why, meta["status"] = "E", "error tecnico: 'no history data, stop testing' (historial/ticks reales no disponibles o descarga cancelada), NO es ausencia de senales", "ERROR_DATOS"
    row = dict(run_id=rid, strategy=fam, symbol=sym, category=cat, timeframe=tf, from_date=meta["from_date"], to_date=meta["to_date"], capital=meta["capital"], leverage=meta["leverage"],
               model=meta["model"], trades=n, net_profit=st.get("total_net_profit", ""), return_pct=round(100 * st["total_net_profit"] / meta["capital"], 3) if st.get("total_net_profit") is not None else "",
               profit_factor=st.get("profit_factor", ""), win_rate_pct=st.get("profit_trades_pct", ""), expectancy_R_proxy=exp_r, max_dd_equity_pct=st.get("equity_dd_max_pct", ""),
               sharpe=st.get("sharpe_ratio", ""), recovery_factor=st.get("recovery_factor", ""), max_margin_pct_symbol=g(r"max_margen_simbolo=([\d.]+)", summ),
               avg_lots=g(r"lotes\(min/medio/max\)=[\d.]+/([\d.]+)/", summ), max_lots=g(r"lotes\(min/medio/max\)=[\d.]+/[\d.]+/([\d.]+)", summ), signals=g(r"senales=(\d+)", summ),
               rej_margin=g(r"rech_margen=(\d+)", summ), rej_risk=g(r"rech_riesgo=(\d+)", summ), rej_minlot=g(r"rech_minlote=(\d+)", summ), skip_cost=g(r"omit_coste=(\d+)", summ),
               history_quality=st.get("history_quality", ""), bars_in_test=st.get("bars", ""), period_in_log=g(r"period=(\w+)", init), symbol_in_log=g(r"symbol=(\S+)", init),
               status=meta["status"], **{"class": cl}, classification_reason=why, report_path=f"results/v5_runs/{rid}/report.htm")
    new = not MATRIX.exists()
    with MATRIX.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new:
            w.writeheader()
        w.writerow(row)
    dst = RUNS / rid
    dst.mkdir(parents=True, exist_ok=True)
    if out.exists():
        for p in out.glob("*"):
            p.replace(dst / p.name)
        out.rmdir()
    print(rid, meta["status"], cl, "ops", n, "net", st.get("total_net_profit"), flush=True)

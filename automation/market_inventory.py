"""Inventario REAL de instrumentos de la instancia aislada (solo lectura: symbols_get/symbol_info/copy_rates). Escribe research/EXNESS_MARKET_UNIVERSE.csv.
Conecta con la instalacion aislada en modo portable; al terminar la cierra (solo ese PID)."""
from __future__ import annotations

import csv
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5

ROOT = Path(__file__).resolve().parent.parent
LAB = Path(r"C:\REMIX_MT5_LAB\terminal")
OUT = ROOT / "research" / "EXNESS_MARKET_UNIVERSE.csv"
COVERAGE_BASES = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD", "USDCHF", "EURGBP", "EURJPY", "XAUUSD", "XAGUSD", "US30", "US500", "USTEC", "DE30", "UK100",
                  "JP225", "BTCUSD", "ETHUSD", "USOIL", "UKOIL", "XNGUSD")
MAJORS = {"EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"}
CCY = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"}
EXOTIC_CCY = {"MXN", "ZAR", "TRY", "SEK", "NOK", "PLN", "HUF", "CZK", "SGD", "HKD", "CNH", "DKK", "RUB", "ILS", "THB"}
CALC = {0: "FOREX", 1: "FUTURES", 2: "CFD", 3: "CFD_INDEX", 4: "CFD_LEVERAGE", 5: "FOREX_NO_LEVERAGE", 32: "EXCH_STOCKS"}


def categorize(s) -> str:
    n = s.name.upper()
    path = (s.path or "").upper()
    base = "".join(ch for ch in n if ch.isalpha())[:6]
    if any(k in n for k in ("XAU", "XPT", "XPD")) or "METAL" in path and "XAG" not in n:
        return "METAL_OTHER" if not n.startswith("XAU") else "GOLD"
    if n.startswith("XAG"):
        return "SILVER"
    if any(k in n for k in ("BTC", "ETH", "LTC", "XRP", "SOL", "DOGE", "ADA", "BNB")) or "CRYPTO" in path:
        return "CRYPTO"
    if any(k in n for k in ("USOIL", "UKOIL", "XTI", "XBR", "XNG", "NGAS", "BRENT", "WTI")) or "ENERGY" in path:
        return "ENERGY"
    if any(k in n for k in ("US30", "US500", "USTEC", "NAS", "SPX", "DJ30")) or n.startswith("US") and ("IND" in path or "INDEX" in path):
        return "INDEX_US"
    if any(k in n for k in ("DE30", "GER", "UK100", "FR40", "STOXX", "ES35", "IT40", "EU50", "NL25", "CH20")):
        return "INDEX_EU"
    if any(k in n for k in ("JP225", "HK50", "AUS200", "CN50", "SG30", "IN50", "TW", "KOR")):
        return "INDEX_ASIA"
    if "INDEX" in path or "INDICES" in path:
        return "INDEX_OTHER"
    if len(base) == 6 and base[:3] in CCY | EXOTIC_CCY and base[3:6] in CCY | EXOTIC_CCY:
        if base in MAJORS:
            return "FOREX_MAJOR"
        if base[:3] in EXOTIC_CCY or base[3:6] in EXOTIC_CCY:
            return "FOREX_EXOTIC"
        return "FOREX_MINOR"
    return "OTHER_CFD"


def main() -> None:
    assert mt5.initialize(path=str(LAB / "terminal64.exe"), portable=True), mt5.last_error()
    ti, acc = mt5.terminal_info(), mt5.account_info()
    print("terminal:", ti.path, "| cuenta", acc.login, acc.server, "| posiciones", len(mt5.positions_get() or []))
    syms = mt5.symbols_get() or []
    rows = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for s in syms:
        mt5.symbol_select(s.name, True)
        info = mt5.symbol_info(s.name)
        r = dict(symbol=s.name, category=categorize(s), path=s.path, available=bool(info and info.visible or mt5.symbol_select(s.name, True)), trade_mode=info.trade_mode,
                 spread_pts=info.spread, spread_floating=info.spread_float, digits=info.digits, point=info.point, tick_size=info.trade_tick_size, tick_value=info.trade_tick_value,
                 contract_size=info.trade_contract_size, vol_min=info.volume_min, vol_max=info.volume_max, vol_step=info.volume_step, margin_calc_mode=CALC.get(info.trade_calc_mode, info.trade_calc_mode),
                 currency_profit=info.currency_profit, currency_base=info.currency_base)
        issues = []
        evaluated = (s.name.endswith("m") and not s.name.endswith(("_x10m", "_x100m")) and any(s.name.upper().startswith(b) for b in COVERAGE_BASES))
        r["history_coverage_evaluated"] = evaluated
        for tf_name, tf in (("M5", mt5.TIMEFRAME_M5), ("M15", mt5.TIMEFRAME_M15)):
            if not evaluated:
                r[f"{tf_name}_bars"], r[f"{tf_name}_first"], r[f"{tf_name}_last"] = "", "", ""
                continue
            rates = mt5.copy_rates_range(s.name, tf, datetime(2020, 1, 1), now)     # (copy_rates_from_pos rechaza 100000 barras: 'Invalid params')
            if rates is None or len(rates) == 0:
                r[f"{tf_name}_bars"], r[f"{tf_name}_first"], r[f"{tf_name}_last"] = 0, "", ""
                issues.append(f"sin historial {tf_name}")
            else:
                r[f"{tf_name}_bars"] = len(rates)
                r[f"{tf_name}_first"] = datetime.utcfromtimestamp(rates[0]["time"]).strftime("%Y-%m-%d")
                r[f"{tf_name}_last"] = datetime.utcfromtimestamp(rates[-1]["time"]).strftime("%Y-%m-%d")
                if (now - datetime.utcfromtimestamp(rates[-1]["time"])).days > 10:
                    issues.append(f"{tf_name} desactualizado")
                if (rates["spread"] == 0).mean() > 0.5:
                    issues.append(f"{tf_name} spread=0 en >50% barras")
        # la API Python no expone las sesiones de negociacion: se infiere el horario EMPIRICO (horas servidor con barras M15 en los ultimos ~30 dias)
        rr = mt5.copy_rates_from_pos(s.name, mt5.TIMEFRAME_M15, 0, 2000) if evaluated else None
        if rr is not None and len(rr):
            import numpy as np
            tt = rr["time"].astype("int64")
            hrs = np.unique((tt % 86400) // 3600)
            wd = np.unique(((tt // 86400) + 4) % 7)               # 0=domingo
            r["trading_hours_server_empirical"] = f"{int(hrs.min()):02d}-{int(hrs.max()) + 1:02d}h ({len(hrs)} horas distintas); dias {','.join(map(str, sorted(wd.tolist())))}"
        else:
            r["trading_hours_server_empirical"] = "n/d"
        tk = mt5.copy_ticks_from(s.name, now.replace(month=max(1, now.month - 1)), 100, mt5.COPY_TICKS_ALL) if evaluated else None
        r["real_ticks_recent"] = bool(tk is not None and len(tk) > 0) if evaluated else "NO_EVALUADO"
        if not evaluated:
            issues.append("cobertura historica NO evaluada (descarga de 357 simbolos inviable: ~3 simbolos/min)")
        r["trade_mode_text"] = {0: "DISABLED", 1: "LONGONLY", 2: "SHORTONLY", 3: "CLOSEONLY", 4: "FULL"}.get(info.trade_mode, str(info.trade_mode))
        if info.trade_mode != 4:
            issues.append("trading no FULL")
        r["issues"] = "; ".join(issues)
        rows.append(r)
    # duplicados / variantes de contrato por raiz
    def root(n):
        return "".join(ch for ch in n.upper() if ch.isalpha())[:6]
    from collections import Counter
    c = Counter(root(r["symbol"]) for r in rows)
    for r in rows:
        r["variants_same_root"] = c[root(r["symbol"])]
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    mt5.shutdown()
    cats = Counter(r["category"] for r in rows)
    print(len(rows), "simbolos", dict(cats))
    print("sin historial M15:", sum(1 for r in rows if r["M15_bars"] == 0))


if __name__ == "__main__":
    main()

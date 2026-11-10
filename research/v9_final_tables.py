"""V9 - resultados oficiales MT5, rentabilidad diaria y registro de experimentos acumulado."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "research"
CAP = 3000.0


def daily_row(rid: str, label: str, linea: str) -> dict:
    T = pd.read_csv(ROOT / "results" / "v4_runs" / rid / "trades.csv", parse_dates=["close_time"])
    T["pnl"] = T.profit + T.commission + T.swap
    cal = pd.date_range("2024-01-01", "2026-10-31", freq="D")
    dpl = T.groupby(T.close_time.dt.normalize()).pnl.sum().reindex(cal, fill_value=0.0)
    bal = CAP + dpl.cumsum(); ret = dpl / bal.shift(1).fillna(CAP)
    td = cal[cal.dayofweek < 5]; rt = ret.loc[td]
    pk = bal.cummax(); uw = bal < pk
    nd = max(len(td), 1)
    return dict(linea=linea, config=label, run_id=rid, trades=len(T), trades_per_trading_day=round(len(T) / nd, 2), net_usd=round(float(T.pnl.sum()), 2), cumulative_pct=round(float((bal.iloc[-1] / CAP - 1) * 100), 2),
                mean_daily_pct_trading_day=round(float(rt.mean() * 100), 4), mean_daily_pct_calendar=round(float(ret.mean() * 100), 4), geometric_daily_pct=round(float(((bal.iloc[-1] / CAP) ** (1 / len(cal)) - 1) * 100), 4),
                pct_trading_days_positive=round(float((rt > 0).mean() * 100), 1), pct_trading_days_negative=round(float((rt < 0).mean() * 100), 1), worst_day_pct=round(float(ret.min() * 100), 3), best_day_pct=round(float(ret.max() * 100), 3),
                max_dd_balance_pct=round(float(((pk - bal) / pk).max() * 100), 2), longest_underwater_days=int((uw.groupby((~uw).cumsum()).cumsum()).max()),
                swap_usd=round(float(T.swap.sum()), 2), commission_usd=round(float(T.commission.sum()), 2), est_spread_cost_usd=np.nan,
                fraction_of_1pct_target=round(float(rt.mean() / 0.01), 4), nota="beneficio realizado por fecha de cierre; PnL flotante intradia no exportado en el informe")


def main():
    O = pd.read_csv(RES / "V8_XAU_H1_OFFICIAL_RESULTS.csv"); O.insert(0, "linea", "A_XAU_CORE (V8 preservado)")
    runs = ROOT / "results" / "v4_runs"
    rid14 = next(p.name for p in runs.iterdir() if p.name.endswith("V9M5B_RR1.5_every_tick_014"))
    s = pd.read_json(runs / rid14 / "stats.json", typ="series"); s = s["stats"] if "stats" in s.index else s
    row = dict(linea="B_SCALPING (control negativo: M5 B_BREAKOUT)", run_id=rid14, tag="V9M5B_RR1.5_every_tick", symbol="XAUUSDm", timeframe="M5", model="Cada tick (generado)", rr=1.5, period="2024-01-01..2026-10-31", capital=CAP, leverage=500,
               trades=int(s["total_trades"]), net_profit=s["total_net_profit"], return_pct=round(100 * s["total_net_profit"] / CAP, 2), profit_factor=s["profit_factor"], expected_payoff_usd=s["expected_payoff"], win_rate_pct=s["profit_trades_pct"],
               equity_dd_pct=s["equity_dd_max_pct"], balance_dd_pct=s["balance_dd_max_pct"], history_quality_pct=s["history_quality"], ticks=int(s["ticks"]), max_consec_losses=int(s["max_consec_losses"]),
               nota="NO es candidata: ejecucion de contraste que verifica el coste del scalping; Python predijo expectativa negativa (paridad 97.2%)", report_html=str(runs / rid14 / "report.htm"))
    X = pd.concat([O, pd.DataFrame([row])], ignore_index=True)
    X.to_csv(RES / "V9_MT5_OFFICIAL_RESULTS.csv", index=False)
    rows = []
    for _, r in O[O.tag.isin(["V8A0_RR1.5_ohlc_1m", "V8A0_RR3.0_ohlc_1m", "V8H4A1_RR2.0_ohlc_1m", "V8H4A1_RR3.0_ohlc_1m"])].iterrows():
        rows.append(daily_row(r.run_id, r.tag, "A_XAU_CORE (V8 preservado, retrospectivo)"))
    rows.append(daily_row(rid14, "V9M5B_RR1.5_every_tick", "B_SCALPING (control negativo)"))
    D = pd.DataFrame(rows)
    D["dias_para_1pct_a_este_ritmo"] = [round(0.01 / (m / 100), 1) if m > 0 else np.nan for m in D.mean_daily_pct_trading_day]
    D.to_csv(RES / "V9_DAILY_PROFITABILITY.csv", index=False)
    # registro acumulado
    G = pd.read_csv(RES / "V9_EXPERIMENT_REGISTER.csv")
    extra = []
    B = pd.read_csv(RES / "V9_BASKET_TRADING.csv"); H = pd.read_csv(RES / "V9_HEDGING_ANALYSIS.csv"); M = pd.read_csv(RES / "V9_MOMENTUM_ANALYSIS.csv")
    for i, r in enumerate(pd.concat([B, H]).drop_duplicates(["senales", "policy"]).to_dict("records")):
        extra.append(dict(exp_id=f"V9P_{i:03d}", tipo="politica_posiciones/cesta/cobertura", symbol="XAUUSDm", tf="H4" if "H4" in r["senales"] else "M5", family=r["senales"], variant=r["policy"], n_ALL=r["n_closed"], expR_ALL=r["expR"], class_="-"))
    for i, r in enumerate(M[M.kind == "modo_entrada"].to_dict("records")):
        extra.append(dict(exp_id=f"V9E_{i:03d}", tipo="modo_entrada", symbol="XAUUSDm", tf=r["tf"], family=r["family"], variant=f'{r["variant"]}/{r["bucket"]}', n_ALL=r["n"], expR_ALL=r["expR_net_1p5"], class_="-"))
    X2 = pd.DataFrame(extra).rename(columns={"class_": "class"})
    n_v9 = len(G) + len(X2)
    N = 3174 + n_v9
    G["N_V9"] = n_v9; G["N_acumulado_V7_V8_V9"] = N; G["t_star_acumulado"] = round(math.sqrt(2 * math.log(N)), 2)
    X2["N_V9"] = n_v9; X2["N_acumulado_V7_V8_V9"] = N; X2["t_star_acumulado"] = round(math.sqrt(2 * math.log(N)), 2)
    out = pd.concat([G, X2], ignore_index=True)
    out.to_csv(RES / "V9_EXPERIMENT_REGISTER.csv", index=False)
    print(D[["config", "trades", "trades_per_trading_day", "net_usd", "mean_daily_pct_trading_day", "max_dd_balance_pct", "dias_para_1pct_a_este_ritmo"]].to_string()); print("N V9", n_v9, "acum", N, "t*", round(math.sqrt(2 * math.log(N)), 2))


if __name__ == "__main__":
    main()

"""V10 - tablas finales: rentabilidad diaria (corregida con el registro del EA), robustez (costes, outliers, estabilidad, PBO/CSCV, DSR), candidatas, resultados oficiales MT5 y registro de experimentos."""
from __future__ import annotations

import itertools
import json
import math

import numpy as np
import pandas as pd

from research.v10_common import R1, RES, ROOT, bars, m15, m5, norm_cdf, pf, split_of, summ, tstat, sha256
from research import v8_lote_c_h4 as C4
from research.v10_h4_audit import prep as prep_h4, dsr, trial_sr_variance

RUNS = ROOT / "results" / "v4_runs"; V8 = ROOT / "results" / "v8"
N_V9_CUM = 3719


# ---------------------------------------------------------------- rentabilidad diaria
def daily_row(linea, config, run_id, t, ndays_trading, ndays_cal, note):
    t = t.sort_values("close_time")
    pnl = t.pnl.values; bal = 3000 + np.cumsum(pnl)
    byday = t.groupby(t.close_time.dt.normalize()).pnl.sum()
    days = pd.date_range("2024-01-01", "2026-10-31", freq="D")        # MISMA definicion que V9: retorno diario = beneficio cerrado del dia / balance previo; dias de negociacion = lun-vie
    s = byday.reindex(days).fillna(0.0); bal_d = 3000 + s.cumsum(); prev = bal_d.shift(1).fillna(3000)
    pct = (s / prev * 100)
    tdays = pct[pct.index.dayofweek < 5]
    ndays_trading, ndays_cal = len(tdays), len(days)
    peak = np.maximum.accumulate(np.r_[3000, bal]); dd = (peak[1:] - bal) / peak[1:] * 100
    hi = np.where(bal >= peak[1:] - 1e-9)[0]
    ct = t.close_time.values
    uw = max(((ct[min(b, len(ct) - 1)] - ct[a]) / np.timedelta64(1, "D") for a, b in zip(hi, np.r_[hi[1:], len(bal) - 1])), default=0)
    mean_td = float(tdays.mean())
    return dict(linea=linea, config=config, run_id=run_id, trades=len(t), trades_per_trading_day=round(len(t) / ndays_trading, 3), net_usd=round(float(pnl.sum()), 2), cumulative_pct=round(float(pnl.sum() / 30), 2),
                mean_daily_pct_trading_day=round(mean_td, 4), mean_daily_pct_calendar=round(float(pct.mean()), 4),
                geometric_daily_pct_trading_day=round(float(((bal[-1] / 3000) ** (1 / ndays_cal) - 1) * 100), 4), pct_trading_days_negative_among_all=round(float((tdays < 0).mean() * 100), 1),
                pct_days_with_closed_trades_negative=round(float((byday < 0).mean() * 100), 1), worst_day_pct=round(float(pct.min()), 3), best_day_pct=round(float(pct.max()), 3),
                max_dd_balance_pct=round(float(dd.max()), 2), longest_underwater_days=round(float(uw), 0), spread_cost_usd=round(float(t.spr.sum()), 2) if "spr" in t else np.nan, swap_usd=round(float(t.swap.sum()), 2),
                fraction_of_1pct_target=round(mean_td / 1.0, 4), days_to_1pct_at_this_rate=round(1.0 / mean_td, 0) if mean_td > 0 else "no aplica",
                nota=note)


def load_ea(run_dir, rr_dir=V8):
    e = pd.read_csv(rr_dir / run_dir / "ea_trades.csv")
    for c in ("open_time", "close_time"):
        e[c] = pd.to_datetime(e[c].astype(str).str.replace(r"\s+", " ", regex=True), format="%Y.%m.%d %H:%M:%S")
    e["pnl"] = e.profit + e.swap + e.commission
    d = bars("H4"); e["spr"] = np.nan
    return e


def daily_table():
    d4 = bars("H4")
    ndt = d4.time.dt.normalize().nunique(); ndc = (d4.time.iloc[-1] - d4.time.iloc[0]).days
    rows = []
    r3 = "RUN_20261110_XAUUSDm_H4_V8_XAU_BREAKOUT_V8H4A1_RR3.0_ohlc_1m_013"; r2 = "RUN_20261110_XAUUSDm_H4_V8_XAU_BREAKOUT_V8H4A1_RR2.0_ohlc_1m_012"; r15 = "RUN_20261110_XAUUSDm_M15_V8_XAU_BREAKOUT_V10M15B_RR3_015"
    _, t3 = prep_h4()
    rows.append(daily_row("A_XAU_H4 (congelada, retrospectiva)", "H4 breakout-20 SL1 TP3R (registro del EA)", r3, t3, ndt, ndc, "fechas de cierre por position_id (EA); sustituye al emparejamiento FIFO de trades.csv usado en V9; flotante intradia no exportado"))
    e2 = load_ea(r2)
    rows.append(daily_row("A_XAU_H4 (congelada, retrospectiva)", "H4 breakout-20 SL1 TP2R (registro del EA)", r2, e2, ndt, ndc, "idem"))
    e15 = load_ea(r15)
    rows.append(daily_row("D_XAU_M15 control (no candidata)", "M15 ruptura 96 velas SL1 TP3R, OHLC 1 min", r15, e15, ndt, ndc, "control oficial MT5 de la unica ruptura M15 con expectativa neta > 0 (t=1,0)"))
    v9 = pd.read_csv(RES / "V9_DAILY_PROFITABILITY.csv"); x = v9[v9.config.str.contains("V9M5B|M5", regex=True)]
    if len(x):
        r = x.iloc[0].to_dict(); r["nota"] = "copiado de V9 (control negativo M5 cada tick); no recalculado"; rows.append({k: r.get(k, np.nan) for k in rows[0]})
    # referencia: comprar y mantener (1 oz) sobre D1
    d1 = bars("D1"); pnl_bh = float(d1.close.iloc[-1] - d1.open.iloc[0])
    rows.append(dict(linea="Referencia comprar y mantener 1 oz (0,01 lote)", config="XAU D1 2024-01..2026-10", run_id="", trades=1, trades_per_trading_day=round(1 / ndt, 4), net_usd=round(pnl_bh, 2), cumulative_pct=round(pnl_bh / 30, 2),
                     mean_daily_pct_trading_day=round(pnl_bh / 3000 * 100 / ndt, 4), mean_daily_pct_calendar=round(pnl_bh / 3000 * 100 / ndc, 4), max_dd_balance_pct=55.78,
                     nota="DD de la serie MTM H4 (V10_XAU_H4_BENCHMARKS.csv); exposicion 100 %; no es una estrategia"))
    D = pd.DataFrame(rows); D.to_csv(RES / "V10_DAILY_PROFITABILITY.csv", index=False)
    return D, t3, e15, e2


# ---------------------------------------------------------------- PBO (CSCV) sobre la rejilla H4 de V8
def pbo_cscv():
    d = bars("H4"); months = pd.period_range("2024-01", "2026-10", freq="M")[:32]
    cols, M = [], []
    for n in (10, 15, 20, 30, 40, 55):
        idx, dr = C4.signals_n(d, n)
        for sl in (0.75, 1.0, 1.5):
            for rr in (1.5, 2.0, 3.0):
                T = R1.trades(d, idx, dr, rr, sl)
                s = T.groupby(pd.to_datetime(T.entry_time).dt.to_period("M")).R_net.sum().reindex(months).fillna(0.0)
                cols.append((n, sl, rr)); M.append(s.values)
    M = np.array(M).T                                        # 32 meses x 54 configuraciones
    S = 8; blocks = np.array_split(np.arange(len(M)), S); lam = []
    for comb in itertools.combinations(range(S), S // 2):
        isx = np.concatenate([blocks[i] for i in comb]); oos = np.concatenate([blocks[i] for i in range(S) if i not in comb])
        sr = lambda X: X.mean(0) / np.where(X.std(0) == 0, np.nan, X.std(0))
        a, b = sr(M[isx]), sr(M[oos])
        best = int(np.nanargmax(a)); rank = (np.sum(b[~np.isnan(b)] <= b[best])) / (np.sum(~np.isnan(b)) + 1)
        lam.append(math.log(rank / (1 - rank)))
    lam = np.array(lam); pbo = float((lam <= 0).mean())
    # configuracion de la baseline (n=20, sl=1, rr=3): su rango OOS medio
    return dict(pbo=round(pbo, 3), n_configs=M.shape[1], n_splits=len(lam), logit_median=round(float(np.median(lam)), 3), months=M.shape[0])


# ---------------------------------------------------------------- robustez
def robustness(t3, e15):
    rows = []
    def add(prueba, medida, valor, nota=""):
        rows.append(dict(sistema="XAU H4 breakout-20 (congelada)", prueba=prueba, medida=medida, valor=valor, nota=nota))
    def addm(prueba, medida, valor, nota=""):
        rows.append(dict(sistema="XAU M15 breakout-96 (control)", prueba=prueba, medida=medida, valor=valor, nota=nota))
    g = json.load(open(ROOT / "results" / "v10" / "h4_audit_summary.json"))["global"]
    for k in ("boot_expR_lo", "boot_expR_hi", "boot_p_expR_le0", "boot_pf_lo", "boot_pf_hi", "boot_p_pf_le1"):
        add("bootstrap por bloques (8 op., 4000 rep.)", k, g[k])
    for k in ("DSR_N1", "DSR_N54", "DSR_N890", "DSR_N3719", "sr_trade", "sr0_N3719", "var_sr_trials", "skew_R", "kurt_R"):
        add("Deflated Sharpe Ratio (Bailey-Lopez de Prado 2014)", k, g[k], "SR por operacion; var(SR) estimada entre las pruebas H4/D1 de V8; N = numero de ensayos" if k.startswith("DSR") else "")
    # costes
    for k in (0, 1, 2, 3):
        p = t3.pnl + (1 - k) * t3.spr * 1.0               # k=1 real; k=0 sin spread; k=2,3 mas spread (1 oz)
        R = p / t3.risk
        add("sensibilidad a costes (spread x k)", f"x{k}: neto / PF / expR", f"{p.sum():.0f} / {pf(p.values):.2f} / {R.mean():.3f}")
    p = t3.pnl + 2 * t3.swap.abs() * 0 - t3.swap.abs()   # swap duplicado
    add("sensibilidad a costes (swap x2)", "neto / PF", f"{p.sum():.0f} / {pf(p.values):.2f}")
    # outliers y concentracion
    s = np.sort(t3.pnl.values)[::-1]
    for k in (1, 3, 5, 10):
        add("outliers", f"sin las {k} mejores operaciones: neto / PF", f"{s[k:].sum():.0f} / {pf(s[k:]):.2f}")
    mo = t3.groupby(t3.close_time.dt.to_period("M")).pnl.sum().sort_values(ascending=False)
    for k in (1, 3):
        add("concentracion temporal", f"sin los {k} mejores meses ({', '.join(map(str, mo.index[:k]))}): neto", round(float(mo.sum() - mo.iloc[:k].sum()), 2))
    # estabilidad por tramo y por ano
    for sp in ("DEV", "SEL", "VAL"):
        x = summ(t3[t3.split == sp].R); add("estabilidad por tramo", f"{sp}: n / expR / t / PF", f"{x['n']} / {x['expR']} / {x['t']} / {x['pf']}")
    x = summ(t3[t3.split != "VAL"].R); add("estabilidad por tramo", "DEV+SEL (sin 2026): n / expR / t / PF", f"{x['n']} / {x['expR']} / {x['t']} / {x['pf']}")
    # dependencia de la tendencia
    for lab, m in (("a favor de la tendencia 50d", t3.trend_long > 0), ("contra la tendencia 50d", t3.trend_long < 0)):
        x = summ(t3[m].R); add("dependencia de la tendencia", f"{lab}: n / expR / t / PF", f"{x['n']} / {x['expR']} / {x['t']} / {x['pf']}", "post hoc: hipotesis de nueva generacion, contamina el historico")
    # retardo: no medible
    add("retardo / latencia", "no evaluado", "n/a", "el parametro de retardo del probador no produce cambios comprobables (V8); se declara como NO evaluado")
    # PBO
    pb = pbo_cscv()
    add("Probability of Backtest Overfitting (CSCV, S=8, 70 divisiones)", "PBO", pb["pbo"], f"rejilla H4: {pb['n_configs']} configuraciones (ventana x SL x RR), {pb['months']} meses; mediana del logit {pb['logit_median']}")
    # M15 control
    q = e15.sort_values("open_time"); q["R"] = q.pnl / q.sl_dist
    addm("resultado oficial MT5", "n / neto / PF", f"{len(q)} / {q.pnl.sum():.0f} / {pf(q.pnl.values):.2f}")
    addm("expectativa", "expR / t", f"{q.R.mean():.3f} / {tstat(q.R):.2f}")
    bm = np.array([np.mean(x) for x in [np.random.default_rng(5).choice(q.R.values, len(q))]])
    from research.v10_common import block_boot
    b = block_boot(q.R.values, 12, 3000, 11)
    addm("bootstrap por bloques (12 op.)", "IC95 expR / P(expR<=0)", f"[{np.percentile(b,2.5):.3f}, {np.percentile(b,97.5):.3f}] / {(b<=0).mean():.3f}")
    for sp, (a, z) in (("DEV", ("2024-01-01", "2025-01-01")), ("SEL", ("2025-01-01", "2026-01-01")), ("VAL", ("2026-01-01", "2026-11-01"))):
        x = q[(q.open_time >= a) & (q.open_time < z)]; xs = summ(x.R); addm("estabilidad por tramo", f"{sp}: n / expR / t / PF", f"{xs['n']} / {xs['expR']} / {xs['t']} / {pf(x.pnl.values):.2f}")
    sw = q.swap.sum(); addm("costes", "swap total USD", round(float(sw), 1), "el swap de XAU es negativo para largos y cortos en el servidor; pesa en operaciones de varios dias")
    dsr15 = dsr(q.R.values, 3805, trial_sr_variance()); addm("Deflated Sharpe Ratio", "DSR (N=3805)", round(dsr15["dsr"], 4), f"SR/op={dsr15['sr_trade']:.3f}; SR0={dsr15['sr0']:.3f}")
    R = pd.DataFrame(rows); R.to_csv(RES / "V10_ROBUSTNESS_RESULTS.csv", index=False)
    return R, pb


# ---------------------------------------------------------------- resultados oficiales MT5
def official_table(e15):
    fr = json.load(open(ROOT / "results" / "v9" / "XAU_FROZEN.json"))["official_runs"]
    rows = []
    for key, rr in (("H4_RR2", 2.0), ("H4_RR3", 3.0)):
        r = fr[key]
        rows.append(dict(linea="A_XAU_H4 (congelada V8)", run_id=r["run_id"], symbol="XAUUSDm", timeframe="H4", params="Lookback 20, Cooldown 6, SL 1 ATR, hold 40, lote 0.01", rr=rr, model="OHLC 1 min", periodo="2024-01-01..2026-10-31",
                         trades=r["trades"], net_profit=r["net_profit"], profit_factor=r["profit_factor"], equity_dd_pct=r["equity_dd_pct"], history_quality_pct=r["history_quality"], report_sha256=r["report_sha256"],
                         ticks_reales="NO (OHLC 1 min; calidad de historial 98 % de las barras, ticks reales solo ~desde 2026-05)", paridad_python="98-99 % de senales (V8)", rol="referencia congelada",
                         nota="trades.csv oficial: emparejamiento FIFO cruza horas de cierre de operaciones solapadas (43 de 248); neto y recuento correctos; analisis por operacion con ea_trades.csv"))
    st = json.load(open(RUNS / "RUN_20261110_XAUUSDm_M15_V8_XAU_BREAKOUT_V10M15B_RR3_015" / "stats.json"))["stats"]
    par = pd.read_csv(RES / "V10_M15_PARITY.csv").iloc[0]
    rows.append(dict(linea="D_XAU_M15 control V10 (no candidata)", run_id="RUN_20261110_XAUUSDm_M15_V8_XAU_BREAKOUT_V10M15B_RR3_015", symbol="XAUUSDm", timeframe="M15", params="Variante 1, Lookback 96, Cooldown 16, SL 1 ATR, hold 96, lote 0.01", rr=3.0, model="OHLC 1 min",
                     periodo="2024-01-01..2026-10-31", trades=int(st.get("total_trades", 0)), net_profit=st.get("total_net_profit"), profit_factor=st.get("profit_factor"), equity_dd_pct=st.get("equity_dd_max_pct"),
                     history_quality_pct=st.get("history_quality"), report_sha256=sha256(RUNS / "RUN_20261110_XAUUSDm_M15_V8_XAU_BREAKOUT_V10M15B_RR3_015" / "report.htm"),
                     ticks_reales="NO (OHLC 1 min)", paridad_python=f"{par.signal_overlap_pct} % senales, direccion {par.direction_agree_pct} %, salidas {par.exit_reason_agree_pct} %", rol="control oficial de la unica ruptura M15 con expectativa neta > 0 en Python (t=1,0): NO es candidata",
                     nota="expR Python 0,054 vs MT5 0,062; 32 entradas de Python con mercado cerrado (10018)"))
    v9 = pd.read_csv(RES / "V9_MT5_OFFICIAL_RESULTS.csv"); x = v9[v9.run_id.str.contains("014")]
    if len(x):
        r = x.iloc[0]
        rows.append(dict(linea="B_scalping M5 control negativo (V9)", run_id=r.run_id, symbol="XAUUSDm", timeframe="M5", params="Variante 1, Lookback 30, Cooldown 10, hold 12", rr=r.rr, model=r.model, periodo=r.period, trades=r.trades, net_profit=r.net_profit,
                         profit_factor=r.profit_factor, equity_dd_pct=r.equity_dd_pct, history_quality_pct=r.history_quality_pct, report_sha256="", ticks_reales="NO (modelo cada tick generado)", paridad_python="97,2 % (V9)", rol="control negativo preservado", nota=""))
    O = pd.DataFrame(rows); O.to_csv(RES / "V10_OFFICIAL_MT5_RESULTS.csv", index=False)
    return O


# ---------------------------------------------------------------- candidatas y registro
def build_register_and_candidates(pb):
    mom = pd.read_csv(RES / "V10_MOMENTUM_RESEARCH.csv"); eco = pd.read_csv(RES / "V10_ECONOMIC_REGIMES.csv"); vol = pd.read_csv(RES / "V10_VOLATILITY_REGIMES.csv")
    m15e = pd.read_csv(RES / "V10_XAU_M15_EVENTS.csv"); m15e = m15e[m15e.tipo == "evento"]; bch = pd.read_csv(RES / "V10_XAU_H4_BENCHMARKS.csv"); mac = pd.read_csv(RES / "V10_MACRO_SUMMARY.csv")
    n_v10 = len(mom) + 12 + 5 + len(m15e) + 3 + 6                       # momentum + economicas (6+6 por variable) + volatilidad (5 variables) + M15 + macro (3 tipos) + controles aleatorios H4 (6)
    N = N_V9_CUM + n_v10; tstar = math.sqrt(2 * math.log(N))
    reg = []
    def R(lote, tipo, hip, fund, var, mercado, tf, periodo, datos, costes, n, resultado, prueba, control, clase):
        reg.append(dict(exp_id=f"V10X_{len(reg):03d}", lote=lote, tipo=tipo, hipotesis=hip, fundamento=fund, variables=var, mercado=mercado, temporalidad=tf, periodo=periodo, datos=datos, costes=costes, n_obs=n, resultado=resultado,
                        prueba_estadistica=prueba, comparacion_control=control, clase=clase))
    for _, r in bch[bch.benchmark.str.match(r"^(D\.|D-L|D-S|E1\.|E1b|E2|F\.)")].iterrows():
        R("A", "control_H4", r.benchmark, "separar la ventaja de la ruptura de la deriva del oro / seleccion", "direccion, hora, regimen", "XAUUSDm", "H4", "2024-01..2026-10", "M15->H4 (v7)", "spread real de la vela", r.n,
          f"expR {r.expR}" + (f" | {r.nota}" if isinstance(r.nota, str) else ""), "aleatorizacion (600 reps) / comparacion directa", "ver nota", "C")
    R("A", "auditoria_H4", "DSR de la baseline H4 con N ensayos", "Bailey & Lopez de Prado 2014", "SR por operacion", "XAUUSDm", "H4", "2024-01..2026-10", "ea_trades.csv", "reales", 248, "DSR(N=3805) ~ 0", "Deflated Sharpe", "-", "C")
    R("A", "auditoria_H4", "PBO de la rejilla H4 (54 configs)", "Bailey et al. 2015 CSCV", "ventana x SL x RR", "XAUUSDm", "H4", "2024-01..2026-09", "ref. Python", "spread real", 54, f"PBO={pb['pbo']}", "CSCV S=8", "-", "C")
    for _, r in mom.iterrows():
        cl = r.clase
        if cl in ("A", "B") and not (abs(r.t_hac) >= tstar):
            cl = "C"
        R("B", "momentum", r.hipotesis, r.fundamento, f"L={r.L}, h={r.h}", r.mercado, r.tf, "2024-01..2026-10", "OHLC XAU", "vol-escalado (coste en nota)", r.n, f"pendiente {r.pendiente} | t_HAC {r.t_hac}", "Newey-West", "DEV/SEL/VAL", cl)
    for _, r in eco.iterrows():
        R("B", "regimen_economico", f"{r.analisis}: {r.variable} {r.get('tercil', '') if isinstance(r.get('tercil', ''), str) else ''}", "tasas reales/nominales, inflacion implicita, dolar y VIX como determinantes del oro (retardo 2 d)", r.variable, "XAUUSDm", "D1/H4",
          "2024-01..2026-10", "FRED (no revisadas)", "n/a", r.n, f"pendiente {r.pendiente} | t {r.t_hac}", "Newey-West / terciles", "-", "D" if abs(r.t_hac) < 2 else "C")
    for v in vol.variable[vol.analisis.str.startswith("ruptura")].unique():
        R("B", "regimen_volatilidad", f"expectativa de la ruptura H4 por tercil de: {v}", "agrupamiento de volatilidad", v, "XAUUSDm", "H4", "2024-01..2026-10", "ref. Python", "spread real", 243, "ver V10_VOLATILITY_REGIMES.csv", "terciles", "-", "C")
    for _, r in mac.iterrows():
        R("C", "macro_ventana", f"{r.event}: rango de la ventana de 30 min posterior vs control", "reaccion de volatilidad del oro a anuncios macro", "rango, vol, continuacion", "XAUUSDm", "M5", "2024-01..2026-10", "BLS/Fed fechas; M5", "spread", r.n,
          f"rango x{r.razon_rango_media_geom}, t(log)={r.t_log_razon}, P(continuacion 15-60min)={r.p_continuacion_15_60}", "t sobre log-razon vs control mismo reloj", "4 controles de +-1,2 semanas", "C" if r.t_log_razon >= 4 else "D")
    for _, r in m15e.iterrows():
        R("D", "M15", f"{r.familia} [{r.variante}, RR {r.RR}]", r.hipotesis_fundamento, "ruptura/sesion/compresion/pullback", "XAUUSDm", "M15", "2024-01..2026-10", "M15", "spread real", r.n_ALL,
          f"bruta {r.expR_bruta_ALL} | neta {r.expR_neta_ALL} (t {r.t_neta_ALL})", "t-test + direccion barajada (300 reps)", f"p={r.p_control_direccion}", r.clase)
    Rg = pd.DataFrame(reg)
    Rg["N_V10_registrado"] = n_v10; Rg["N_acumulado_V7_V8_V9_V10"] = N; Rg["t_star_acumulado"] = round(tstar, 2)
    Rg.to_csv(RES / "V10_EXPERIMENT_REGISTER.csv", index=False)

    cand = [
        dict(id="V10C_01", sistema="XAU H4 breakout-20, SL 1 ATR, TP 3R (V8, congelada)", mercado="XAUUSDm H4", clase="C", evidencia="248 op. oficiales MT5: +2.172,77 USD, PF 1,57, DD eq. 8,4 %; expR +0,30 R (t 2,5); bootstrap P(expR<=0)=0,006",
             limitaciones=f"DSR~0 con N>=54; PBO={pb['pbo']}; 80 % del neto en 3 meses; aleatorios con la misma proporcion LONG ganan +0,12 R (p=0,027); LONG aleatorio +0,30 R (p=0,16); contra tendencia 50d -0,08 R (n=60); sin 2026: expR +0,20 (t 1,45); historico ya explorado",
             siguiente="evaluar la definicion EXACTA con datos >= 2026-11-01 (prospectivo)"),
        dict(id="V10C_02", sistema="XAU M15 ruptura 96 velas, SL 1 ATR, TP 3R (control oficial MT5)", mercado="XAUUSDm M15", clase="C", evidencia="MT5: 1.077 op., +656,97 USD, PF 1,13, DD eq. 9,65 %; Python expR +0,054 (t 1,0); invertida -0,10 R (direccion con informacion)",
             limitaciones="DEV negativo (-0,05 R), t 1,0, p(control)=0,087; edge neto ~ coste; no cumple regla de candidata", siguiente="solo prospectivo; no optimizar"),
        dict(id="V10C_03", sistema="XAU M15 ruptura 96 velas alineada con tendencia H4, TP 3R", mercado="XAUUSDm M15", clase="C", evidencia="Python: bruta +0,127, neta +0,084 R (t 1,29), SEL +0,13, VAL +0,20, p(control)=0,043", limitaciones="DEV -0,07 R: no pasa la regla de candidata (DEV t>=2); 1 de 22 pruebas", siguiente="hipotesis de nueva generacion; prospectivo"),
        dict(id="V10C_04", sistema="XAU H4 ruptura 20 tras consolidacion previa (rango 10v <= cuartil inferior)", mercado="XAUUSDm H4", clase="C", evidencia="n=114, expR +0,49 R (t 2,7), VAL +1,47; diferencia con/sin consolidacion t 1,09 (no distinguible)", limitaciones="subconjunto de las mismas operaciones ya exploradas", siguiente="prospectivo"),
        dict(id="V10C_05", sistema="TSMOM M15 L=16 h=96 (signo de 4 h -> 24 h)", mercado="XAUUSDm M15", clase="C", evidencia="pendiente 0,029 sigma (t_HAC 2,10) con signo coherente en DEV/SEL/VAL", limitaciones=f"|t|<t*={tstar:.2f}; 1 de 25 pruebas (se esperan ~1 por azar); efecto 0,03 sigma ~ coste 0,007 sigma por viaje", siguiente="descartar salvo replica prospectiva"),
        dict(id="V10C_06", sistema="Ventanas macro NFP/CPI/FOMC (volatilidad y reversion)", mercado="XAUUSDm M5", clase="F", evidencia="rango 30 min x2,2-3,0 y vol x2,3-3,7 sobre el control (t 7-13); NFP revierte 74 % (15->60 min, n=31)", limitaciones="sin consenso => sin sorpresas; n<100; la volatilidad no es direccion", siguiente="buscar fuente de consenso verificable"),
        dict(id="V10C_07", sistema="Scalping M1/M5 (V9) y todas las pruebas D de V10", mercado="varios", clase="D", evidencia="expectativa bruta ~0 y neta negativa (V9); momentum/reversion/macro regimenes sin evidencia", limitaciones="", siguiente="no repetir"),
    ]
    C = pd.DataFrame(cand); C.to_csv(RES / "V10_STRATEGY_CANDIDATES.csv", index=False)
    return Rg, C, n_v10, N, tstar


def main():
    D, t3, e15, e2 = daily_table()
    R, pb = robustness(t3, e15)
    O = official_table(e15)
    Rg, C, n_v10, N, tstar = build_register_and_candidates(pb)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); pd.set_option("display.max_colwidth", 50)
    print(D.drop(columns=["nota"]).to_string()); print(R[["sistema", "prueba", "medida", "valor"]].to_string()); print(O.drop(columns=["nota", "rol", "ticks_reales", "params", "report_sha256"]).to_string())
    print("N_V10", n_v10, "N_total", N, "t*", round(tstar, 3), Rg.clase.value_counts().to_dict())


if __name__ == "__main__":
    main()

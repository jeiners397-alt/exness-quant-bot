"""V8 - tablas de analisis condicional de entradas, salidas/entradas alternativas, costes de transaccion y registro de experimentos."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from research import v8_htf_event_study as H
from research import v8_lote_c_h4 as C
from research import v8_xau_h1_reference as R1

V = H.V
ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "research"
V8 = ROOT / "results" / "v8"
SPLIT = V.SPLIT


# ----------------------------------------------------------------------------- 1. entradas condicionales
def entry_analysis() -> pd.DataFrame:
    F = pd.read_pickle(V8 / "htf_features.pkl")
    F["time"] = pd.to_datetime(F.time)
    rows = []
    feats = ["vol_pct", "er30", "speed3", "range_pos", "compression", "dist_ma_ATR", "spread_ATR", "bar_range_ATR"]
    for (tf, fam, var), g in F.groupby(["tf", "family", "variant"]):
        for scope, gg in (("POOL_5_MERCADOS", g), ("XAUUSDm", g[g.symbol == "XAUUSDm"])):
            if len(gg) < 30:
                continue
            for f in feats:
                x = gg[f].replace([np.inf, -np.inf], np.nan)
                try:
                    q = pd.qcut(x, 3, labels=["T1_bajo", "T2_medio", "T3_alto"], duplicates="drop")
                except ValueError:
                    continue
                for lab, h in gg.groupby(q, observed=True):
                    if len(h) < 10:
                        continue
                    t, _ = V.tstat(h["R_1.5"])
                    rows.append(dict(tf=tf, family=fam, variant=var, scope=scope, feature=f, bucket=str(lab), n=len(h), feat_lo=round(float(x[h.index].min()) if False else float(h[f].min()), 4),
                                     feat_hi=round(float(h[f].max()), 4), expR_1p5=round(h["R_1.5"].mean(), 4), expR_3=round(h["R_3.0"].mean(), 4), t_1p5=round(t, 2) if t == t else np.nan,
                                     mfe_mean=round(h.mfe.mean(), 3), mae_mean=round(h.mae.mean(), 3)))
            for lab, h in gg.groupby("trend_align"):
                if len(h) >= 10:
                    t, _ = V.tstat(h["R_1.5"])
                    rows.append(dict(tf=tf, family=fam, variant=var, scope=scope, feature="trend_align(SMA20-SMA50 vs direccion)", bucket=str(int(lab)), n=len(h), expR_1p5=round(h["R_1.5"].mean(), 4),
                                     expR_3=round(h["R_3.0"].mean(), 4), t_1p5=round(t, 2) if t == t else np.nan, mfe_mean=round(h.mfe.mean(), 3), mae_mean=round(h.mae.mean(), 3)))
            if tf == "H4":
                for lab, h in gg.groupby("hour"):
                    if len(h) >= 10:
                        t, _ = V.tstat(h["R_1.5"])
                        rows.append(dict(tf=tf, family=fam, variant=var, scope=scope, feature="hora_UTC_vela", bucket=str(int(lab)), n=len(h), expR_1p5=round(h["R_1.5"].mean(), 4),
                                         expR_3=round(h["R_3.0"].mean(), 4), t_1p5=round(t, 2) if t == t else np.nan, mfe_mean=round(h.mfe.mean(), 3), mae_mean=round(h.mae.mean(), 3)))
    E = pd.DataFrame(rows)
    E["nota"] = "descriptivo/condicional; NO se selecciono ningun filtro por su rendimiento. Cada celda es una comparacion adicional: con ~%d celdas, ~5%% daran |t|>1.96 por azar." % len(E)
    E.to_csv(RES / "V8_ENTRY_ANALYSIS.csv", index=False)
    return E


# ----------------------------------------------------------------------------- 2. salidas / entradas alternativas (simulacion barra a barra, mismas senales)
MAXH = 40


def sim_one(d, i, s, entry_mode: str, exit_mode: str):
    o, h, l, c, a, sp = (d[k].values for k in ("open", "high", "low", "close", "atr", "spr"))
    at = a[i]
    if not (at > 0) or i + 1 + MAXH + 4 >= len(d):
        return None
    start = i + 1
    if entry_mode == "next_open":
        e = o[i + 1]
    else:
        off = 0.3 if entry_mode == "limit_0.3ATR" else 0.6
        lim = c[i] - s * off * at
        e = None
        for j in range(i + 1, i + 4):                               # orden limite valida 3 velas
            if (l[j] <= lim) if s > 0 else (h[j] >= lim):
                e, start = lim, j; break
        if e is None:
            return None
    cost = sp[start] / at
    sl_d, tp_d, trail, be, partial, tmax = 1.0, None, False, False, False, MAXH
    if exit_mode == "TP1.5": tp_d = 1.5
    elif exit_mode == "TP3": tp_d = 3.0
    elif exit_mode == "SL1.5_TP3": sl_d, tp_d = 1.5, 3.0
    elif exit_mode == "SL0.75_TP1.5": sl_d, tp_d = 0.75, 1.5
    elif exit_mode == "STRUCT_SL_TP2x":
        ext = (c[i] - l[i]) if s > 0 else (h[i] - c[i])                  # distancia al extremo opuesto de la vela de senal
        sl_d = float(np.clip((ext + 0.1 * at) / at, 0.5, 3.0)); tp_d = 2 * sl_d
    elif exit_mode.startswith("TIME"): tmax = int(exit_mode[4:])
    elif exit_mode == "TRAIL_1ATR_after_1R": trail = True
    elif exit_mode == "BE_1R_TP3": tp_d, be = 3.0, True
    elif exit_mode == "PARTIAL_50_at_1.5R_rest_3R": tp_d, partial = 3.0, True
    sl = e - s * sl_d * at; tp = e + s * tp_d * at if tp_d else None
    R_unit = sl_d * at
    best = e; first_done = False; locked = 0.0; frac = 1.0
    for j in range(start, start + tmax):
        if j == start and entry_mode != "next_open":
            pass
        hit_sl = (l[j] <= sl) if s > 0 else (h[j] >= sl)
        if hit_sl:
            r = frac * s * (sl - e) / R_unit
            return locked + r - cost / sl_d
        if partial and not first_done:
            t1 = e + s * 1.5 * R_unit
            if (h[j] >= t1) if s > 0 else (l[j] <= t1):
                locked += 0.5 * 1.5; frac = 0.5; first_done = True; sl = e                      # resto a break-even
        if tp is not None and ((h[j] >= tp) if s > 0 else (l[j] <= tp)):
            return locked + frac * (tp_d / sl_d) - cost / sl_d
        if be and not first_done and ((h[j] >= e + s * R_unit) if s > 0 else (l[j] <= e - s * R_unit)):
            sl = e; first_done = True
        if trail:
            best = max(best, c[j]) if s > 0 else min(best, c[j])
            if s * (best - e) >= R_unit:
                ns = best - s * at
                sl = max(sl, ns) if s > 0 else min(sl, ns)
    last = start + tmax - 1
    return locked + frac * s * (c[last] - e) / R_unit - cost / sl_d


def exit_entry_study() -> pd.DataFrame:
    exits = ["TP1.5", "TP3", "SL1.5_TP3", "SL0.75_TP1.5", "STRUCT_SL_TP2x", "TIME10", "TIME20", "TIME40", "TRAIL_1ATR_after_1R", "BE_1R_TP3", "PARTIAL_50_at_1.5R_rest_3R"]
    rows = []
    rules = {}
    d1 = R1.V.load("XAUUSDm") if False else None
    # regla 1: XAU H1 V7 (sweep invertido); regla 2: XAU H4 A1
    import os
    dH1 = H.load_htf("XAUUSDm", "H1")
    V.COOL = 12                                       # enfriamiento de la regla V7 (12 velas)
    i1, r1 = R1.signals(dH1, "A_V7_SWEEP_INV")
    assert len(i1) in (320, 321, 322, 323), len(i1)
    V.COOL = 6
    dH4 = H.load_htf("XAUUSDm", "H4"); i4, r4 = C.signals_n(dH4, 20)
    rules["XAU_H1_V7_SWEEP_INV"] = (dH1, i1, r1); rules["XAU_H4_A1_BREAKOUT20"] = (dH4, i4, r4)
    combos = [("next_open", ex) for ex in exits] + [("limit_0.3ATR", "TP1.5"), ("limit_0.3ATR", "TP3"), ("limit_0.6ATR", "TP1.5"), ("limit_0.6ATR", "TP3")]
    for rn, (d, idx, dr) in rules.items():
        t = d.time.values
        for em, ex in combos:
            res = []
            for i, s in zip(idx, dr):
                r = sim_one(d, i, s, em, ex)
                if r is not None:
                    res.append((t[min(i + 1, len(t) - 1)], r))
            if not res:
                continue
            X = pd.DataFrame(res, columns=["time", "R"]); X["time"] = pd.to_datetime(X.time)
            for split, m in (("ALL", X.time > "1900"), ("IS", X.time < SPLIT), ("OOS", X.time >= SPLIT)):
                x = X[m].R
                tt, _ = V.tstat(x)
                pf = x[x > 0].sum() / -x[x < 0].sum() if (x < 0).any() else np.nan
                rows.append(dict(rule=rn, entry_mode=em, exit_mode=ex, split=split, n=len(x), expR_net=round(x.mean(), 4), t=round(tt, 2) if tt == tt else np.nan, pf_R=round(pf, 3), win_rate=round((x > 0).mean(), 3),
                                 sum_R=round(x.sum(), 1), fill_rate=round(len(X) / max(len(idx), 1), 3), es_baseline=(em == "next_open" and ex in ("TP1.5", "TP3"))))
    E = pd.DataFrame(rows)
    # mejor por IS vs su OOS (para comprobar si la 'mejora' sobrevive)
    piv = E.pivot_table(index=["rule", "entry_mode", "exit_mode"], columns="split", values="expR_net").reset_index()
    best = piv.sort_values("IS", ascending=False).groupby("rule").head(1)
    E["nota"] = "exploratorio, mismo historico; cada combinacion cuenta en el registro. La referencia sin optimizar es next_open + TP1.5/TP3 con SL 1 ATR. Mejor-por-IS: " + "; ".join(
        f"{r.rule}: {r.entry_mode}/{r.exit_mode} IS {r.IS:.3f} -> OOS {r.OOS:.3f}" for r in best.itertuples())
    E.to_csv(RES / "V8_EXIT_ANALYSIS.csv", index=False)
    return E


# ----------------------------------------------------------------------------- 3. costes
def cost_table() -> pd.DataFrame:
    rows = []
    swaps = {}
    try:
        import MetaTrader5 as mt5
        if mt5.initialize(path=r"C:\REMIX_MT5_LAB\terminal\terminal64.exe", portable=True):
            for s in V.SYMS:
                mt5.symbol_select(s, True)
                i = mt5.symbol_info(s)
                if i is not None:
                    swaps[s] = dict(swap_long=i.swap_long, swap_short=i.swap_short, swap_mode=i.swap_mode, swap_rollover3days=i.swap_rollover3days, tick_size=i.trade_tick_size, tick_value=i.trade_tick_value,
                                    contract=i.trade_contract_size, vol_min=i.volume_min, stops_level=i.trade_stops_level, freeze_level=i.trade_freeze_level, spread_float=i.spread_float)
            mt5.shutdown()
    except Exception as ex:                                                              # lectura solamente; si falla se registra
        swaps["_error"] = str(ex)[:200]
    for s in V.SYMS:
        d = pd.read_csv(V.D / f"{s}_M15.csv", parse_dates=["time"]); d["spr"] = d.spread * V.INFO[s]["point"]
        d["hour"] = d.time.dt.hour
        pc = d.close.shift(1); tr = np.maximum(d.high - d.low, np.maximum((d.high - pc).abs(), (d.low - pc).abs())); d["atr"] = tr.rolling(14).mean()
        sw = swaps.get(s, {})
        row = dict(symbol=s, spread_pts_median=float(d.spread.median()), spread_pts_p95=float(d.spread.quantile(0.95)), spread_price_median=float(d.spr.median()),
                   cost_ATR_M15=round(float((d.spr / d.atr).median()), 4), commission="0 (Exness Standard: solo spread; NO verificado en el servidor, sin dato historico)", slippage="no disponible en historico; el probador no aplica deslizamiento (entrada al ask/bid de la barra)", **sw)
        for tf in ("H1", "H4", "D1"):
            rule = {"H1": "1h", "H4": "4h", "D1": "1D"}[tf]
            g = d.set_index("time").resample(rule).agg(dict(high="max", low="min", close="last", spread="mean")).dropna()
            gp = g.close.shift(1); trr = np.maximum(g.high - g.low, np.maximum((g.high - gp).abs(), (g.low - gp).abs())); at = trr.rolling(14).mean()
            row[f"cost_ATR_{tf}"] = round(float((g.spread * V.INFO[s]["point"] / at).median()), 5)
        sess = d.groupby(pd.cut(d.hour, [-1, 6, 12, 16, 23], labels=["asia_0-6", "londres_7-12", "ny_13-16", "tarde_17-23"]), observed=True).spread.median()
        for k, v in sess.items():
            row[f"spread_pts_med_{k}"] = float(v)
        rows.append(row)
    T = pd.DataFrame(rows)
    # escenarios de coste sobre las ejecuciones oficiales (modelado a partir de las operaciones del tester)
    A = json.load(open(V8 / "xau_h1_trade_analysis.json"))
    T.attrs["scen"] = A
    T.to_csv(RES / "V8_TRANSACTION_COSTS.csv", index=False)
    sc = pd.DataFrame([dict(escenario=f"{r['tf']}_RR{r['rr']}", n=r["n"], neto_USD_tester_costes_historicos=r["net_cost_x1"], costes_x1_5=r["net_cost_x1p5"], costes_x2=r["net_cost_x2"], costes_x3=r["net_cost_x3"],
                            swap_total_USD=r["swap_total_usd"], PF_x2=r["pf_cost_x2"], nota="A=historicos del tester (x1) | B=+50% spread (x1.5) | C=x2 | D=retraso: ExecutionMode del tester sin efecto medible -> se modela como x2..x3 de spread; MODELADO") for r in A])
    sc.to_csv(RES / "V8_TRANSACTION_COSTS_SCENARIOS.csv", index=False)
    return T


# ----------------------------------------------------------------------------- 4. registro
def register(E_exit: pd.DataFrame):
    R = pd.read_csv(RES / "V8_ROBUSTNESS_RESULTS.csv")
    rows = [dict(exp_id=f"V8B_{i:04d}", lote="B", tipo="event_study_HTF", symbol=r.symbol, tf=r.tf, descripcion=f"{r.family}/{r.variant}/RR{r.rr}", n_all=r.n_all, expR_all=r.expR_all, t_all=r.t_all, clase=r["class"])
            for i, r in enumerate(R.to_dict("records") and R.itertuples(index=False))] if False else []
    for i, r in enumerate(R.to_dict("records")):
        rows.append(dict(exp_id=f"V8B_{i:04d}", lote="B", tipo="event_study_HTF", symbol=r["symbol"], tf=r["tf"], descripcion=f'{r["family"]}/{r["variant"]}/RR{r["rr"]}', n_all=r["n_all"], expR_all=r["expR_all"], t_all=r["t_all"], clase=r["class"]))
    S = pd.read_csv(RES / "V8_H4_SENSITIVITY.csv")
    for i, r in enumerate(S.to_dict("records")):
        rows.append(dict(exp_id=f"V8C_SENS_{i:03d}", lote="C", tipo="sensibilidad_parametros", symbol="XAUUSDm", tf="H4", descripcion=f'ventana{r["window"]}/SL{r["sl_atr"]}/RR{r["rr"]}', n_all=r["n"], expR_all=r["expR_net"], t_all=r["t"], clase="C(sens)"))
    for i, r in enumerate(E_exit[E_exit.split == "ALL"].to_dict("records")):
        rows.append(dict(exp_id=f"V8C_EXIT_{i:03d}", lote="C", tipo="entradas_salidas_alternativas", symbol="XAUUSDm", tf="H1" if "H1" in r["rule"] else "H4", descripcion=f'{r["rule"]}/{r["entry_mode"]}/{r["exit_mode"]}', n_all=r["n"], expR_all=r["expR_net"], t_all=r["t"], clase="C(expl)"))
    O = pd.read_csv(RES / "V8_XAU_H1_OFFICIAL_RESULTS.csv")
    for r in O.to_dict("records"):
        rows.append(dict(exp_id=r["run_id"], lote="A/C", tipo="backtest_oficial_MT5", symbol=r["symbol"], tf=r["timeframe"], descripcion=f'{r["tag"]} [{r["model"]}]', n_all=r["trades"], expR_all=np.nan, t_all=np.nan,
                         clase="reproduccion (no validacion)", net_profit=r["net_profit"], profit_factor=r["profit_factor"]))
    G = pd.DataFrame(rows)
    n_v8 = len(G[G.tipo != "backtest_oficial_MT5"])
    n_total = 2200 + n_v8
    G["N_tests_V8"] = n_v8; G["N_tests_acumulado_V7_V8"] = n_total; G["t_star_acumulado"] = round(math.sqrt(2 * math.log(n_total)), 2)
    G.to_csv(RES / "V8_EXPERIMENT_REGISTER.csv", index=False)
    return n_v8, n_total, round(math.sqrt(2 * math.log(n_total)), 2)


if __name__ == "__main__":
    E = entry_analysis(); print("entry rows", len(E))
    X = exit_entry_study(); print(X[X.split == "ALL"].to_string(max_colwidth=22)); print(X.nota.iloc[0])
    cost_table()
    print(register(X))


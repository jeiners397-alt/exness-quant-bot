"""D. BACKTEST ENGINE - simulacion historica barra a barra con costes.

Modelo de ejecucion (conservador y explicito):
- Senal en el cierre de la barra i -> entrada a mercado en la apertura de i+1.
- Largo entra al ASK = open + spread(barra i+1); sale al BID. Corto entra al BID; sale al ASK = bid + spread.
- SL/TP se evaluan con OHLC de la barra (largo en BID; corto en ASK). Si SL y TP caen en la misma
  barra se asume SL primero. Gap por encima del SL -> salida a la apertura (peor caso).
- Una posicion a la vez. Sin trailing.
- Slippage en puntos (parametro) aplicado en contra en entrada y en salidas por SL / tiempo.
- Swap: swap_mode==1 (puntos) por noche de rollover (x3 en miercoles); otros modos -> sin modelar (se avisa).
- Equity/DD calculados sobre operaciones cerradas (no incluyen DD intra-operacion).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class BacktestConfig:
    initial_capital: float = 100.0
    risk_pct: float = 0.5
    sizing_policy: str = "strict"      # strict | min_lot | ideal
    commission_per_lot_roundturn: float = 0.0
    slippage_points: float = 0.0
    use_swap: bool = True
    # --- paridad con el EA V2 (todos opcionales; por defecto desactivados => resultados anteriores intactos)
    max_spread_frac_sl: float | None = None   # compuerta de entrada: spread(barra de entrada) > frac*SL => se omite (EA: MaxSpreadFracSL)
    max_spread_points: float | None = None    # compuerta de entrada: spread(barra de entrada, puntos) > N => se omite (EA: MaxSpreadPoints)
    reenter_after_open_exit: bool = False     # tras una salida a la APERTURA de la barra k (tiempo/max_bars/regla), la senal de la barra k-1 puede entrar en k (como OnTick del EA)
    max_bars_mode: str = "bars"               # "bars": barras existentes; "calendar": (t_k - t_entrada)/bar_seconds (comportamiento del EA V2, cuenta tambien las horas sin mercado)
    bar_seconds: int = 0
    skip_entry_after_gap: bool = False        # modelo del tick de reapertura: si la barra de entrada abre tras un hueco de mercado (> bar_seconds), el spread del primer tick es desconocido/ancho (MT5: 47-116 pts observados) => se omite


def compute_lots(balance, risk_pct, sl_dist, spec, policy):
    """Devuelve (lotes, riesgo_planificado_$, riesgo_real_$, motivo_omision|None)."""
    vpu = spec["value_per_price_unit_per_lot"]
    risk_money = balance * risk_pct / 100.0
    loss_per_lot = sl_dist * vpu
    if loss_per_lot <= 0:
        return 0.0, risk_money, 0.0, "sl_invalido"
    raw = risk_money / loss_per_lot
    if policy == "ideal":
        return raw, risk_money, risk_money, None
    step, vmin, vmax = spec["volume_step"], spec["volume_min"], spec["volume_max"]
    lots = np.floor(raw / step + 1e-9) * step
    if lots < vmin:
        if policy == "strict":
            return 0.0, risk_money, vmin * loss_per_lot, "lote_minimo_excede_riesgo"
        lots = vmin
    lots = min(lots, vmax)
    return round(float(lots), 8), risk_money, lots * loss_per_lot, None


def _swap_nights(t_in: pd.Timestamp, t_out: pd.Timestamp) -> int:
    n = 0
    d = t_in.normalize()
    end = t_out.normalize()
    while d < end:
        wd = d.weekday()          # medianoche d -> d+1
        n += 3 if wd == 2 else (0 if wd >= 5 else 1)   # mie x3 (cubre sab/dom); vie->sab SI se cobra 1x (verificado con swaps del Tester); sab/dom no
        d += pd.Timedelta(days=1)
    return n


def run_backtest(df: pd.DataFrame, sig, spec: dict, cfg: BacktestConfig, tag: dict | None = None):
    """df: OHLC+spread. sig: Signals. spec: especificacion del simbolo. Devuelve (trades_df, info)."""
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    spr = df["spread"].to_numpy(float) * spec["point"]
    tms = df["time"].to_numpy()
    hours = df["time"].dt.hour.to_numpy()
    n = len(df)
    point = spec["point"]
    vpu = spec["value_per_price_unit_per_lot"]
    slip = cfg.slippage_points * point
    swap_ok = cfg.use_swap and spec.get("swap_mode") == 1

    balance = cfg.initial_capital
    trades, skipped = [], {}
    i = 0
    texit = sig.time_exit_hour
    max_bars = getattr(sig, "max_bars", None)
    ex_l = getattr(sig, "exit_long", None)
    ex_s = getattr(sig, "exit_short", None)
    nzidx = np.flatnonzero(np.asarray(sig.direction) != 0)
    # columnas opcionales del modelo de sesion (Fase paridad): spread del primer tick de la barra y mercado cerrado en el primer tick
    gspr = (df["gate_spread"].to_numpy(float) if "gate_spread" in df.columns else df["spread"].to_numpy(float)) * spec["point"]
    gpts = df["gate_spread"].to_numpy(float) if "gate_spread" in df.columns else df["spread"].to_numpy(float)
    no_trade = df["no_trade_at_open"].to_numpy(bool) if "no_trade_at_open" in df.columns else np.zeros(n, bool)
    while i < n - 1:
        d = int(sig.direction[i])
        if d == 0:
            pos = int(np.searchsorted(nzidx, i))      # salta a la siguiente senal (equivale a i += 1 repetido)
            if pos >= len(nzidx):
                break
            i = int(nzidx[pos])
            continue
        j = i + 1
        sl_d, tp_d = float(sig.sl_dist[i]), float(sig.tp_dist[i])
        # compuertas de spread en la barra de ENTRADA (solo informacion disponible en la apertura de j), mismas que OpenTrade del EA
        if cfg.skip_entry_after_gap and cfg.bar_seconds and (tms[j] - tms[j - 1]) / np.timedelta64(1, "s") > cfg.bar_seconds:
            skipped["gap_open_spread_unknown"] = skipped.get("gap_open_spread_unknown", 0) + 1
            i += 1
            continue
        if no_trade[j]:
            skipped["market_closed_at_open"] = skipped.get("market_closed_at_open", 0) + 1
            i += 1
            continue
        if cfg.max_spread_frac_sl is not None and gspr[j] > cfg.max_spread_frac_sl * sl_d:
            skipped["spread_frac_sl"] = skipped.get("spread_frac_sl", 0) + 1
            i += 1
            continue
        if cfg.max_spread_points is not None and gpts[j] > cfg.max_spread_points:
            skipped["spread_points"] = skipped.get("spread_points", 0) + 1
            i += 1
            continue
        lots, risk_plan, risk_real, why = compute_lots(balance, cfg.risk_pct, sl_d, spec, cfg.sizing_policy)
        if why:
            skipped[why] = skipped.get(why, 0) + 1
            i += 1
            continue
        # --- entrada
        entry = o[j] + (spr[j] if d == 1 else 0.0) + d * slip      # slippage en contra
        sl = entry - d * sl_d
        tp = entry + d * tp_d
        exit_px, reason, k = None, None, j
        while k < n:
            if k > j and texit is not None and hours[k] >= texit:
                exit_px = o[k] + (spr[k] if d == -1 else 0.0) - d * slip
                reason = "time"
                break
            held = (k - j) if cfg.max_bars_mode == "bars" else int((tms[k] - tms[j]) / np.timedelta64(1, "s") // max(cfg.bar_seconds, 1))
            if k > j and not no_trade[k] and ((max_bars and held >= max_bars) or (d == 1 and ex_l is not None and ex_l[k - 1]) or (d == -1 and ex_s is not None and ex_s[k - 1])):
                exit_px = o[k] + (gspr[k] if d == -1 else 0.0) - d * slip
                reason = "max_bars" if (max_bars and held >= max_bars) else "rule_exit"
                break
            if d == 1:
                if o[k] <= sl:
                    exit_px, reason = o[k] - slip, "sl_gap"
                elif l[k] <= sl:
                    exit_px, reason = sl - slip, "sl"
                elif h[k] >= tp:
                    exit_px, reason = tp, "tp"
            else:
                ask_h, ask_l, ask_o = h[k] + spr[k], l[k] + spr[k], o[k] + spr[k]
                if ask_o >= sl:
                    exit_px, reason = ask_o + slip, "sl_gap"
                elif ask_h >= sl:
                    exit_px, reason = sl + slip, "sl"
                elif ask_l <= tp:
                    exit_px, reason = tp, "tp"
            if exit_px is not None:
                break
            k += 1
        if exit_px is None:  # fin de datos: cierre al ultimo cierre (marcado)
            k = n - 1
            exit_px = c[k] + (spr[k] if d == -1 else 0.0)
            reason = "end_of_data"
        # --- costes y resultado
        t_in, t_out = pd.Timestamp(tms[j]), pd.Timestamp(tms[k])
        move = d * (exit_px - entry)
        # el spread ya esta incluido en los precios; se informa aparte: largo lo paga al entrar (ask), corto al salir (ask)
        spread_cost_px = spr[j] if d == 1 else spr[k]
        comm = cfg.commission_per_lot_roundturn * lots
        swap_pts = spec["swap_long"] if d == 1 else spec["swap_short"]
        nights = _swap_nights(t_in, t_out) if swap_ok else 0
        swap_px = nights * swap_pts * point                      # en unidades de precio (negativo = coste)
        gross_money = move * vpu * lots
        swap_money = swap_px * vpu * lots
        net_money = gross_money - comm + swap_money
        comm_px = (cfg.commission_per_lot_roundturn / vpu) if vpu else 0.0
        net_r = (move - comm_px + swap_px) / sl_d
        balance += net_money
        trades.append(dict(
            entry_time=t_in, exit_time=t_out, dir=d, entry=entry, exit=exit_px, sl_dist=sl_d, tp_dist=tp_d,
            lots=lots, exit_reason=reason, bars_held=k - j, net_r=net_r, entry_spread_pts=float(df["spread"].iat[j]), sl_px=sl, tp_px=tp, nights=nights,
            gross_money=gross_money, commission=comm, swap=swap_money,
            spread_cost=spread_cost_px * vpu * lots, slippage_cost=2 * slip * vpu * lots,
            net_money=net_money, balance=balance, risk_plan=risk_plan, risk_real=risk_real,
            risk_real_pct=100 * risk_real / max(balance - net_money, 1e-9),
        ))
        i = k  # una posicion a la vez; la senal de la barra de salida puede entrar en la siguiente
        if cfg.reenter_after_open_exit and reason in ("time", "max_bars", "rule_exit") and k - 1 >= j:
            i = k - 1   # salida a la apertura de k: el EA evalua en esa misma barra con la senal de k-1 (entrada en k)
    tr = pd.DataFrame(trades)
    if tag and not tr.empty:
        for kk, vv in tag.items():
            tr[kk] = vv
    info = dict(skipped=skipped, swap_modeled=bool(swap_ok), final_balance=balance, bars=n,
                sizing_policy=cfg.sizing_policy)
    return tr, info




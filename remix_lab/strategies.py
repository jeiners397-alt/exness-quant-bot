"""C. STRATEGY ENGINE - estrategias individuales registradas por ID.

Contrato: generate(df, params, spec) -> Signals. La senal en la fila i usa SOLO datos
hasta el cierre de la barra i; la entrada se ejecuta en la apertura de la barra i+1.
Todas las horas son hora de servidor MT5 (observada ~UTC en Exness).

PROCEDENCIA DE PARAMETROS: los valores por defecto son valores canonicos de manual
(p.ej. Donchian 20, ATR 14, BB 20/2, EMA 20/50/200, ADX 14) elegidos ANTES de ver
cualquier resultado. No provienen de optimizacion. Los grids de busqueda (GRID) son
rangos predefinidos alrededor de esos valores.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import indicators as ind


@dataclass
class Signals:
    direction: np.ndarray            # +1 long, -1 short, 0 nada
    sl_dist: np.ndarray              # distancia SL en precio desde el precio de entrada
    tp_dist: np.ndarray              # distancia TP en precio
    time_exit_hour: int | None = None  # cierre forzado a la apertura de la primera barra con hora >= valor
    max_bars: int | None = None        # (Fase D) salida temporal de seguridad: tras N barras, cierre a la apertura de la siguiente
    exit_long: "np.ndarray | None" = None   # (Fase D) True en barra i => si hay LARGO abierto, sale a la apertura de i+1
    exit_short: "np.ndarray | None" = None  # idem para CORTOS


@dataclass
class StrategySpec:
    id: str
    name: str
    indicators: str
    long_rule: str
    short_rule: str
    exit_rule: str
    sl_rule: str
    tp_rule: str
    spread_filter: str
    defaults: dict
    grid: dict
    provenance: str = "Valores canonicos de manual, fijados a priori; no optimizados."


def _spread_ok(df, spec, sl_dist, p):
    """Filtro de spread: spread de la barra de senal <= max_spread_frac * distancia SL."""
    sp = df["spread"].to_numpy(float) * spec["point"]
    with np.errstate(invalid="ignore", divide="ignore"):
        return sp <= p["max_spread_frac"] * sl_dist


def _finalize(df, spec, p, direction, sl, tp, time_exit_hour=None):
    direction = np.asarray(direction, dtype=int)
    sl = np.asarray(sl, float)
    tp = np.asarray(tp, float)
    ok = np.isfinite(sl) & np.isfinite(tp) & (sl > 0) & _spread_ok(df, spec, sl, p)
    direction = np.where(ok, direction, 0)
    return Signals(direction, sl, tp, time_exit_hour)


# ---------------------------------------------------------------- S01
S01_SPEC = StrategySpec(
    id="S01", name="London Breakout",
    indicators="Rango asiatico [range_start_h, range_end_h) de la misma fecha (max high / min low).",
    long_rule="Barra con hora de apertura en [range_end_h, entry_end_h) cuyo CIERRE > RangeHigh. Solo la primera senal del dia.",
    short_rule="Idem con CIERRE < RangeLow.",
    exit_rule="SL/TP; o cierre forzado a la apertura de la primera barra con hora >= exit_h.",
    sl_rule="SL = RangeWidth * sl_range_mult desde la entrada.",
    tp_rule="TP = SL * rr.",
    spread_filter="spread(barra de senal) <= max_spread_frac * SL; ademas RangeWidth >= min_range_spread_mult * spread.",
    defaults=dict(range_start_h=0, range_end_h=7, entry_end_h=10, exit_h=17, sl_range_mult=1.0, rr=1.5,
                  min_range_spread_mult=10.0, max_spread_frac=0.15),
    grid=dict(range_end_h=[6, 7, 8], entry_end_h=[9, 10, 12], rr=[1.0, 1.5, 2.0, 3.0], sl_range_mult=[0.75, 1.0]),
)


def gen_s01(df, p, spec):
    t = df["time"]
    hour = t.dt.hour.to_numpy()
    date = t.dt.normalize()
    in_rng = (hour >= p["range_start_h"]) & (hour < p["range_end_h"])
    hi = df["high"].where(in_rng)
    lo = df["low"].where(in_rng)
    rh = hi.groupby(date).transform("max").to_numpy()
    rl = lo.groupby(date).transform("min").to_numpy()
    width = rh - rl
    win = (hour >= p["range_end_h"]) & (hour < p["entry_end_h"])
    c = df["close"].to_numpy()
    sp = df["spread"].to_numpy(float) * spec["point"]
    long_ = win & (c > rh)
    short_ = win & (c < rl)
    d = np.where(long_, 1, np.where(short_, -1, 0))
    d = np.where(width >= p["min_range_spread_mult"] * sp, d, 0)
    # solo la primera senal valida de cada dia
    first = pd.Series(d != 0, index=df.index).groupby(date.to_numpy()).cumsum().to_numpy() == 1
    d = np.where((d != 0) & first, d, 0)
    sl = width * p["sl_range_mult"]
    return _finalize(df, spec, p, d, sl, sl * p["rr"], time_exit_hour=p["exit_h"])


# ---------------------------------------------------------------- S02
S02_SPEC = StrategySpec(
    id="S02", name="Donchian Channel + ATR",
    indicators="Donchian(N) de las N barras anteriores (excluye la actual); ATR(atr_n) SMA del TR.",
    long_rule="close[i] > max(high[i-N..i-1]).",
    short_rule="close[i] < min(low[i-N..i-1]).",
    exit_rule="SL/TP (sin trailing).",
    sl_rule="SL = sl_atr * ATR[i].",
    tp_rule="TP = tp_atr * ATR[i].",
    spread_filter="spread(barra de senal) <= max_spread_frac * SL.",
    defaults=dict(donchian_n=20, atr_n=14, sl_atr=2.0, tp_atr=3.0, max_spread_frac=0.15),
    grid=dict(donchian_n=[10, 20, 40, 55], sl_atr=[1.5, 2.0, 3.0], tp_atr=[2.0, 3.0, 4.5]),
)


def gen_s02(df, p, spec):
    hh, ll = ind.donchian_prev(df, p["donchian_n"])
    a = ind.atr(df, p["atr_n"]).to_numpy()
    c = df["close"]
    d = np.where(c > hh, 1, np.where(c < ll, -1, 0))
    return _finalize(df, spec, p, d, a * p["sl_atr"], a * p["tp_atr"])


# ---------------------------------------------------------------- S03
S03_SPEC = StrategySpec(
    id="S03", name="EMA + ADX Pullback",
    indicators="EMA(fast), EMA(mid), EMA(slow); ADX/+DI/-DI(adx_n, Wilder); ATR(atr_n).",
    long_rule="EMA(mid)>EMA(slow) y ADX>adx_min y +DI>-DI y close[i-1]<EMA(fast)[i-1] y close[i]>EMA(fast)[i] (pullback y reanudacion).",
    short_rule="Espejo: EMA(mid)<EMA(slow), -DI>+DI, close[i-1]>EMA(fast) y close[i]<EMA(fast).",
    exit_rule="SL/TP (sin trailing).",
    sl_rule="SL = sl_atr * ATR[i].",
    tp_rule="TP = tp_atr * ATR[i].",
    spread_filter="spread(barra de senal) <= max_spread_frac * SL.",
    defaults=dict(ema_fast=20, ema_mid=50, ema_slow=200, adx_n=14, adx_min=25.0, atr_n=14, sl_atr=1.5, tp_atr=3.0,
                  max_spread_frac=0.15),
    grid=dict(adx_min=[20.0, 25.0, 30.0], sl_atr=[1.0, 1.5, 2.0], tp_atr=[2.0, 3.0, 4.0], ema_fast=[10, 20]),
)


def gen_s03(df, p, spec):
    c = df["close"]
    ef, em, es = ind.ema(c, p["ema_fast"]), ind.ema(c, p["ema_mid"]), ind.ema(c, p["ema_slow"])
    a, pdi, mdi = ind.adx(df, p["adx_n"])
    atr_ = ind.atr(df, p["atr_n"]).to_numpy()
    up = (em > es) & (a > p["adx_min"]) & (pdi > mdi) & (c.shift(1) < ef.shift(1)) & (c > ef)
    dn = (em < es) & (a > p["adx_min"]) & (mdi > pdi) & (c.shift(1) > ef.shift(1)) & (c < ef)
    d = np.where(up, 1, np.where(dn, -1, 0))
    return _finalize(df, spec, p, d, atr_ * p["sl_atr"], atr_ * p["tp_atr"])


# ---------------------------------------------------------------- S04
S04_SPEC = StrategySpec(
    id="S04", name="Bollinger Squeeze + Momentum",
    indicators="Bollinger(bb_n, bb_k); BandWidth=(U-L)/M; SMA(BandWidth, bw_lookback); Momentum=close[i]-close[i-mom_n]; ATR(atr_n).",
    long_rule="Squeeze en i-1: BW[i-1] < sq_ratio*SMA(BW,bw_lookback)[i-1]; y close[i]>Upper[i] y Momentum[i]>0.",
    short_rule="Squeeze en i-1; close[i]<Lower[i] y Momentum[i]<0.",
    exit_rule="SL/TP (sin trailing).",
    sl_rule="SL = sl_atr * ATR[i].",
    tp_rule="TP = tp_atr * ATR[i].",
    spread_filter="spread(barra de senal) <= max_spread_frac * SL.",
    defaults=dict(bb_n=20, bb_k=2.0, bw_lookback=100, sq_ratio=0.75, mom_n=10, atr_n=14, sl_atr=2.0, tp_atr=3.0,
                  max_spread_frac=0.15),
    grid=dict(sq_ratio=[0.6, 0.75, 0.9], mom_n=[5, 10, 20], sl_atr=[1.5, 2.0, 3.0], tp_atr=[2.0, 3.0, 4.5]),
)


def gen_s04(df, p, spec):
    c = df["close"]
    mid, up, lo = ind.bollinger(c, p["bb_n"], p["bb_k"])
    bw = (up - lo) / mid
    sq = (bw < p["sq_ratio"] * ind.sma(bw, p["bw_lookback"])).shift(1, fill_value=False)
    mom = c - c.shift(p["mom_n"])
    atr_ = ind.atr(df, p["atr_n"]).to_numpy()
    d = np.where(sq & (c > up) & (mom > 0), 1, np.where(sq & (c < lo) & (mom < 0), -1, 0))
    return _finalize(df, spec, p, d, atr_ * p["sl_atr"], atr_ * p["tp_atr"])


REGISTRY = {
    "S01": (S01_SPEC, gen_s01),
    "S02": (S02_SPEC, gen_s02),
    "S03": (S03_SPEC, gen_s03),
    "S04": (S04_SPEC, gen_s04),
}


def get_strategy(sid: str):
    if sid not in REGISTRY:
        raise KeyError(f"Estrategia {sid} no registrada. Disponibles: {list(REGISTRY)}")
    return REGISTRY[sid]


def generate(sid: str, df: pd.DataFrame, sym_spec: dict, params: dict | None = None) -> Signals:
    spec, fn = get_strategy(sid)
    p = {**spec.defaults, **(params or {})}
    return fn(df, p, {"point": sym_spec["point"]})

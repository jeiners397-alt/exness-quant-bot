"""FASE E (fases 1,2,4 de la orden V2): estudio de eventos de tres barreras para familias A-E en EURUSDm H1/H4.
Periodos: TRAIN 2018-2021 | VALID 2022-2024 (replica retrospectiva) | EXPL 2025-01..2026-10 (ya inspeccionado). SL=1.5 ATR14, horizonte H1=24 / H4=12 barras.
Seleccion (pre-registrada en phase_e_select.py): SOLO con TRAIN. Orden intrabarra desconocido -> dos cotas (conservadora/optimista).
Salida: research/PHASE_E_EVENT_STUDY.csv (una fila por hipotesis x tf x regimen x periodo x k) y PHASE_E_HOURLY.csv"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab import harness as H  # noqa: E402
from remix_lab import indicators as ind  # noqa: E402
from remix_lab.events import KS, barrier_events, wilson  # noqa: E402
from remix_lab.strategies_d import prev_day_levels, resample  # noqa: E402

RNG = np.random.default_rng(12345)
F = H.load_frames()
H1 = pd.concat([F["RETRO"]["H1"], F["EXPL"]["H1"]]).reset_index(drop=True)
H4 = resample(H1, "H4")
PER = {"TRAIN": ("2018-01-01", "2022-01-01"), "VALID": ("2022-01-01", "2025-01-01"), "EXPL": ("2025-01-01", "2026-11-01")}
SL_ATR = 1.5
HOR = {"H1": 24, "H4": 12}


def feats(df):
    c = df.close
    f = pd.DataFrame({"atr": ind.atr(df, 14), "z50": ind.zscore(c, 50), "rsi2": ind.rsi(c, 2), "rsi14": ind.rsi(c, 14), "sma100": ind.sma(c, 100),
                      "e20": ind.ema(c, 20), "e50": ind.ema(c, 50), "e200": ind.ema(c, 200), "ker": ind.ker(c, 10), "chop": ind.choppiness(df, 14),
                      "adx": ind.adx(df, 14)[0]})
    mid, up, lo = ind.bollinger(c, 20, 2.0)
    f["bb_up"], f["bb_lo"], f["bb_mid"] = up, lo, mid
    bw = (up - lo) / mid
    f["bbw_pct"] = bw.rolling(100).apply(lambda w: float((w <= w[-1]).mean()), raw=True)
    return f


def cross_in(x):
    x = np.asarray(x, bool); return x & ~np.r_[False, x[:-1]]


def hyps(df, f, tf):
    c, o, h, l = (df[k].to_numpy(float) for k in ("close", "open", "high", "low"))
    out = {}
    z = f.z50.to_numpy()
    for th in (1.5, 2.0, 2.5, 3.0):
        out[f"A1_zrev_{th}"] = np.where(z <= -th, 1, np.where(z >= th, -1, 0))
    r2, s100 = f.rsi2.to_numpy(), f.sma100.to_numpy()
    for lo_, hi_ in ((10, 90), (5, 95)):
        out[f"A2_rsi2_trend_{lo_}"] = np.where((c > s100) & (r2 < lo_), 1, np.where((c < s100) & (r2 > hi_), -1, 0))
        out[f"A2_rsi2_counter_{lo_}"] = np.where(r2 < lo_, 1, np.where(r2 > hi_, -1, 0))
    for n in (20, 55):
        hh, ll = ind.donchian_prev(df, n); hh, ll = np.asarray(hh, float), np.asarray(ll, float)
        up, dn = c > hh, c < ll
        out[f"B1_donchian_cont_{n}"] = np.where(cross_in(up), 1, np.where(cross_in(dn), -1, 0))
        up1, dn1 = np.r_[False, up[:-1]], np.r_[False, dn[:-1]]
        hh1, ll1 = np.r_[np.nan, hh[:-1]], np.r_[np.nan, ll[:-1]]
        out[f"C1_breakout_fail_{n}"] = np.where(up1 & (c < hh1), -1, np.where(dn1 & (c > ll1), 1, 0))
    for n in (20, 60):
        roc = pd.Series(c).pct_change(n).to_numpy()
        st = np.where(roc > 0, 1, np.where(roc < 0, -1, 0))
        out[f"B2_mom_{n}"] = np.where(st != np.r_[0, st[:-1]], st, 0)
    atr_ = f.atr.to_numpy(); rng_ = h - l
    big = rng_ >= 1.5 * np.r_[np.nan, atr_[:-1]]
    bull, bear = big & (c > l + 0.7 * rng_), big & (c < l + 0.3 * rng_)
    out["E1_expansion_fade"] = np.where(bull, -1, np.where(bear, 1, 0))
    out["E2_expansion_follow"] = np.where(bull, 1, np.where(bear, -1, 0))
    e20, e50, e200, ker_ = (f[k].to_numpy() for k in ("e20", "e50", "e200", "ker"))
    cp, e20p = np.r_[np.nan, c[:-1]], np.r_[np.nan, e20[:-1]]
    out["B3_pullback_ker"] = np.where((e20 > e50) & (e50 > e200) & (ker_ > 0.3) & (cp < e20p) & (c > e20), 1,
                                      np.where((e20 < e50) & (e50 < e200) & (ker_ > 0.3) & (cp > e20p) & (c < e20), -1, 0))
    k_up, k_lo = e20 + 2 * atr_, e20 - 2 * atr_
    out["A3_keltner_fade"] = np.where(c < k_lo, 1, np.where(c > k_up, -1, 0))
    r14 = f.rsi14.to_numpy()
    out["A4_bollinger_rsi_fade"] = np.where((c < f.bb_lo.to_numpy()) & (r14 < 30), 1, np.where((c > f.bb_up.to_numpy()) & (r14 > 70), -1, 0))
    sq = np.r_[False, (f.bbw_pct.to_numpy() < 0.2)[:-1]]
    out["B4_squeeze_breakout"] = np.where(sq & (c > f.bb_up.to_numpy()), 1, np.where(sq & (c < f.bb_lo.to_numpy()), -1, 0))
    if tf == "H1":
        pdh, pdl = prev_day_levels(df); c1 = np.r_[np.nan, c[:-1]]
        out["C2_pdhl_breakout"] = np.where((c > pdh) & (c1 <= pdh), 1, np.where((c < pdl) & (c1 >= pdl), -1, 0))
        out["C3_pdhl_sweep"] = np.where((h > pdh) & (c < pdh), -1, np.where((l < pdl) & (c > pdl), 1, 0))
    return out


def regime_masks(df, f, tf):
    hr = df.time.dt.hour.to_numpy()
    m = {"ALL": np.ones(len(df), bool), "KER_LO": (f.ker.to_numpy() < 0.3), "KER_HI": (f.ker.to_numpy() >= 0.3)}
    if tf == "H1":
        m.update({"SES_ASIA": hr < 7, "SES_LON": (hr >= 7) & (hr < 12), "SES_NY": (hr >= 12) & (hr < 17)})
    return m


def block_boot(x, block=5, B=1000):
    x = np.asarray(x, float); n = len(x)
    if n < 20:
        return (np.nan, np.nan)
    blocks = max(1, min(block, n // 4))
    bs = [np.concatenate([x[i:i + blocks] for i in RNG.integers(0, n - blocks + 1, size=n // blocks + 1)])[:n].mean() for _ in range(B)]
    return (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))


rows = []
t0 = time.time()
for tf, df in (("H1", H1), ("H4", H4)):
    f = feats(df)
    sl = f.atr.to_numpy() * SL_ATR
    hz = HOR[tf]
    times = df.time.to_numpy()
    masks = regime_masks(df, f, tf)
    for name, d in hyps(df, f, tf).items():
        for reg, m in masks.items():
            if reg.startswith("SES_") and not (name.startswith(("C2", "C3", "E", "B1", "A1_zrev_2.0"))):
                continue
            dd = np.where(m, d, 0)
            ev = barrier_events(df, dd, sl, hz, KS, min_gap=max(1, hz // 4))
            if ev.empty:
                continue
            ev["time"] = times[ev.idx.to_numpy()]
            for per, (a, b) in PER.items():
                sub = ev[(ev.time >= np.datetime64(a)) & (ev.time < np.datetime64(b))]
                for k in KS:
                    n = len(sub)
                    if n < 20:
                        continue
                    rc, ro = sub[f"Rc_{k}"].to_numpy(), sub[f"Ro_{k}"].to_numpy()
                    wins = int(sub[f"win_{k}"].sum())
                    lo_w, hi_w = wilson(wins, n)
                    ci = block_boot(rc)
                    rows.append(dict(hyp=name, tf=tf, regime=reg, period=per, k=k, n=n, n_long=int((sub.dir == 1).sum()), p_win_cons=round(wins / n, 4),
                                     p_ci_lo=round(lo_w, 4), p_ci_hi=round(hi_w, 4), p_win_opt=round(float((ro >= k - 1e-9).mean()), 4), p_breakeven_nocost=round(1 / (k + 1), 4),
                                     amb_share=round(float(sub[f"amb_{k}"].mean()), 4), E_cons=round(float(rc.mean()), 4), E_opt=round(float(ro.mean()), 4),
                                     E_cons_ci_lo=round(ci[0], 4), E_cons_ci_hi=round(ci[1], 4), t_cons=round(float(rc.mean() / (rc.std(ddof=1) / np.sqrt(n))), 2) if rc.std() > 0 else np.nan,
                                     cost_R=round(float(sub.cost_R.mean()), 4), mfe_med=round(float(sub.mfe_R.median()), 3), mae_med=round(float(sub.mae_R.median()), 3),
                                     bars_med=float(sub[f"bars_{k}"].median())))
    print(f"[{time.time()-t0:.0f}s] {tf} listo, filas={len(rows)}", flush=True)

R = pd.DataFrame(rows)
R.to_csv(ROOT / "research/PHASE_E_EVENT_STUDY.csv", index=False)
# efecto horario/dia (descriptivo, H1): retorno medio de la barra por hora y por periodo, con t
ret = (H1.close / H1.open - 1) * 1e4
hh = pd.DataFrame({"hour": H1.time.dt.hour, "dow": H1.time.dt.dayofweek, "ret_bp": ret, "t": H1.time})
hrows = []
for per, (a, b) in PER.items():
    s = hh[(hh.t >= a) & (hh.t < b)]
    g = s.groupby("hour").ret_bp.agg(["mean", "std", "count"])
    for hr, r in g.iterrows():
        hrows.append(dict(period=per, hour=int(hr), mean_bp=round(r["mean"], 3), t=round(r["mean"] / (r["std"] / np.sqrt(r["count"])), 2), n=int(r["count"])))
pd.DataFrame(hrows).to_csv(ROOT / "research/PHASE_E_HOURLY.csv", index=False)
meta = dict(n_hyp_variants=int(R[["hyp", "tf", "regime"]].drop_duplicates().shape[0]), n_cells=int(R[["hyp", "tf", "regime", "k"]].drop_duplicates().shape[0]), sl_atr=SL_ATR, horizons=HOR, periods=PER,
            data_notes=H.DATA_NOTES, elapsed_s=round(time.time() - t0))
(ROOT / "research/PHASE_E_META.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
print(meta)

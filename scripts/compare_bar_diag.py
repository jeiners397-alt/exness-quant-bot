"""Compara vela por vela el CSV por barra del EA V2.1 (REMIX_V21_bars_*.csv, ExportBarDiag=true) con los indicadores de Python:
ATR14, SMA50 (manual e iMA), sigma50, z-score, ADX14/+DI/-DI (formula MT5 y Wilder), senal y motivo.
Uso:  python scripts/compare_bar_diag.py <ruta_csv_barras> [ruta_h4_nativo.csv]
Salida: resumen en consola y research/PARITY_BAR_DIAG_<n>.json. Solo lectura."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix_lab import indicators as ind  # noqa: E402

TOL = {"atr14": 1e-7, "sma50_manual": 1e-7, "sma50_ima": 1e-7, "std50": 1e-7, "z50": 1e-5, "adx14": 1e-2, "plus_di": 1e-2, "minus_di": 1e-2}


def python_side(h4: pd.DataFrame) -> pd.DataFrame:
    c = h4.close
    out = pd.DataFrame({"time": h4.time})
    out["atr14"] = ind.atr(h4, 14).values
    out["sma50_manual"] = ind.sma(c, 50).values
    out["std50"] = c.rolling(50).std(ddof=0).values
    out["z50"] = ind.zscore(c, 50).values
    a, p, m = ind.adx_mt5(h4, 14)
    out["adx_mt5"], out["pdi_mt5"], out["mdi_mt5"] = a.values, p.values, m.values
    w, wp, wm = ind.adx(h4, 14)
    out["adx_wilder"], out["pdi_wilder"], out["mdi_wilder"] = w.values, wp.values, wm.values
    return out


def compare(diag_csv: Path, h4: pd.DataFrame, warmup_bars: int = 300) -> dict:
    d = pd.read_csv(diag_csv)
    d["bar1_time"] = pd.to_datetime(d["bar1_time"], format="%Y.%m.%d %H:%M")
    py = python_side(h4)
    m = d.merge(py, left_on="bar1_time", right_on="time", how="left", suffixes=("", "_py"))
    m = m[m.atr14_py.notna() | m.atr14.notna()]
    res = {"n_bars_mt5": int(len(d)), "n_matched_to_python_series": int(m.time.notna().sum())}
    pairs = {"atr14": "atr14_py", "sma50_manual": "sma50_manual_py", "std50": "std50_py", "z50": "z50_py"}
    # columnas del lado Python (tras merge los nombres coinciden con sufijo _py cuando chocan)
    for mt, pyc in pairs.items():
        if pyc not in m:
            continue
        v = m[(m[mt] != 0) & m[pyc].notna()]
        diff = (v[mt] - v[pyc]).abs()
        res[mt] = {"n": int(len(v)), "max_abs_diff": float(diff.max()) if len(v) else None, "pct_within_tol": float((diff <= TOL[mt]).mean() * 100) if len(v) else None}
    v = m[(m["sma50_ima"] != 0) & m["sma50_manual_py"].notna()]
    res["sma50_ima"] = {"n": int(len(v)), "max_abs_diff": float((v.sma50_ima - v.sma50_manual_py).abs().max()) if len(v) else None}
    for name, (a_mt, a_w, col) in {"adx14": ("adx_mt5", "adx_wilder", "adx14"), "plus_di": ("pdi_mt5", "pdi_wilder", "plus_di"), "minus_di": ("mdi_mt5", "mdi_wilder", "minus_di")}.items():
        v = m[(m[col] != 0) & m[a_mt].notna()].iloc[warmup_bars // 6:] if len(m) > warmup_bars // 6 else m
        v = v[v.time.notna()]
        res[name] = {"n": int(len(v)), "max_abs_diff_vs_formula_MT5_EMA": float((v[col] - v[a_mt]).abs().max()) if len(v) else None,
                     "median_abs_diff_vs_formula_MT5_EMA": float((v[col] - v[a_mt]).abs().median()) if len(v) else None,
                     "max_abs_diff_vs_Wilder": float((v[col] - v[a_w]).abs().max()) if len(v) else None,
                     "closest_implementation": ("MT5_EMA" if len(v) and (v[col] - v[a_mt]).abs().median() < (v[col] - v[a_w]).abs().median() else "Wilder")}
    # senal: z<=-2 -> +1, z>=2 -> -1, filtrada por ADX<25 (formula MT5)
    sig_py = np.where(m.z50_py <= -2.0, 1, np.where(m.z50_py >= 2.0, -1, 0))
    sig_py_f = np.where(m.adx_mt5 < 25.0, sig_py, 0)
    sig_mt = np.where(m["reason"].astype(str).str.contains("ADX_FILTER|NO_SIGNAL|OPEN|SKIP|ORDER_FAILED|IN_POSITION|CLOSE", regex=True), m.signal_dir, 0)
    raw_mt = m.signal_dir.to_numpy()
    res["signals"] = {"raw_z_signal_agree_pct": float((np.sign(raw_mt) == sig_py).mean() * 100),
                      "n_raw_signals_mt5": int((raw_mt != 0).sum()), "n_raw_signals_python": int((sig_py != 0).sum()),
                      "n_after_adx_filter_python_mt5formula": int((sig_py_f != 0).sum()),
                      "reasons": m["reason"].astype(str).str.replace(r"CLOSE_\w+\|", "", regex=True).value_counts().head(8).to_dict()}
    return res


if __name__ == "__main__":
    csv = Path(sys.argv[1])
    h4p = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data/raw/hist/EURUSDm_H4_native_2022_2026.csv"
    h4 = pd.read_csv(h4p, parse_dates=["time"])
    out = compare(csv, h4)
    (ROOT / "research" / f"PARITY_BAR_DIAG_{csv.stem}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))

"""V9 Lote A - congela y verifica la referencia XAU H4 (y H1) de V8: parametros exactos, hashes SHA-256 de EA e informes oficiales, resultados oficiales.
Si `--verify`, solo comprueba que nada cambio respecto a results/v9/XAU_FROZEN.json."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "results" / "v4_runs"
OUT = ROOT / "results" / "v9"
OUT.mkdir(parents=True, exist_ok=True)
FROZEN = OUT / "XAU_FROZEN.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def runs():
    sel = {"H4_RR2": "V8H4A1_RR2.0_ohlc_1m_012", "H4_RR3": "V8H4A1_RR3.0_ohlc_1m_013", "H1_RR1.5": "V8A0_RR1.5_ohlc_1m_005", "H1_RR3": "V8A0_RR3.0_ohlc_1m_006"}
    out = {}
    for k, suf in sel.items():
        d = next(p for p in RUNS.iterdir() if p.name.endswith(suf.split("_ohlc_1m_")[0] + "_ohlc_1m_" + suf.split("_ohlc_1m_")[1]) and "V8_XAU_BREAKOUT" in p.name)
        s = json.load(open(d / "stats.json")); s = s.get("stats", s)
        out[k] = dict(run_id=d.name, report_sha256=sha(d / "report.htm"), trades_sha256=sha(d / "trades.csv"), stats_sha256=sha(d / "stats.json"), net_profit=s["total_net_profit"], profit_factor=s["profit_factor"],
                      trades=int(s["total_trades"]), equity_dd_pct=s["equity_dd_max_pct"], history_quality=s["history_quality"])
    return out


def build():
    ea = ROOT / "mql5" / "REMIX_V8_XAU_BREAKOUT.mq5"
    fz = dict(
        estado="CONGELADA - retrospectiva, clase C, NO validada independientemente; ticks reales no disponibles (9% calidad)",
        ea_source=str(ea.relative_to(ROOT)), ea_sha256=sha(ea),
        h4_params=dict(symbol="XAUUSDm", timeframe="H4", Variant="1 (VARIANT_B_CLOSE_OUT: primera vela que cierra fuera del rango de Lookback velas, continuacion)", Lookback=20, PierceATR="n/a", ATR_N=14, CooldownBars=6, SL_ATR=1.0,
                       RR="2.0 y 3.0 (prefijados)", MaxHoldBars=40, FixedLot=0.01, MarginPct=5.0, RiskPctCap=3.0, deposit=3000, leverage=500, model="OHLC 1 min", period="2024-01-01..2026-10-31"),
        h1_params=dict(symbol="XAUUSDm", timeframe="H1", Variant="0 (VARIANT_A_V7: pico que cierra dentro, a favor del pico)", Lookback=96, PierceATR=0.1, ATR_N=14, CooldownBars=12, SL_ATR=1.0, RR="1.5 y 3.0", MaxHoldBars=40, FixedLot=0.01),
        reserva_prospectiva="datos >= 2026-11-01 no usados para desarrollar; solo evaluacion de esta definicion exacta", official_runs=runs())
    return fz


def main():
    if "--verify" in sys.argv:
        old = json.load(open(FROZEN)); new = build()
        diffs = [k for k in ("ea_sha256",) if old[k] != new[k]] + [f"{k}.{h}" for k, v in old["official_runs"].items() for h in ("report_sha256", "trades_sha256", "stats_sha256") if v[h] != new["official_runs"][k][h]]
        print("VERIFICACION:", "OK, sin cambios" if not diffs else f"CAMBIOS en {diffs}")
        sys.exit(1 if diffs else 0)
    fz = build()
    if FROZEN.exists():
        print("ya existe; usa --verify"); return
    FROZEN.write_text(json.dumps(fz, indent=1, ensure_ascii=False), encoding="utf-8")
    rows = []
    for k, r in fz["official_runs"].items():
        p = fz["h4_params"] if k.startswith("H4") else fz["h1_params"]
        rows.append(dict(linea="A_XAU_CORE", config=k, **{f"p_{a}": b for a, b in p.items()}, **r, ea_sha256=fz["ea_sha256"], estado="retrospectivo / clase C / pendiente de validacion", reserva=fz["reserva_prospectiva"]))
    pd.DataFrame(rows).to_csv(ROOT / "research" / "V9_XAU_H4_BASELINE.csv", index=False)
    print(json.dumps({k: (v["net_profit"], v["profit_factor"], v["trades"]) for k, v in fz["official_runs"].items()}), fz["ea_sha256"][:16])


if __name__ == "__main__":
    main()

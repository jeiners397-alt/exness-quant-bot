"""V9 - paridad Python vs MT5 del control negativo M5 B_BREAKOUT (EA V8 variante 1, Lookback 30, Cooldown 10, hold 12, RR 1.5, cada tick). Mismas senales, mismo coste."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from research import v9_scalp_study as S
from research import v8_xau_h1_reference as R1
from research import v8_parity as P

V = S.V
ROOT = S.ROOT


def main():
    rid = next(p.name for p in (ROOT / "results" / "v4_runs").iterdir() if p.name.endswith("V9M5B_RR1.5_every_tick_014"))
    V.HZ = S.CFG["M5"]["HZ"]; V.MAXH = 12; V.COOL = 10; R1.MAXH = 12
    d = S.load("XAUUSDm", "M5")
    idx, dr = S.families(d, "M5")["B_BREAKOUT"]; ok = idx > 100
    idx, dr, _ = V.dedupe(idx[ok], dr[ok], None)
    T = R1.trades(d, idx, dr, 1.5); T.insert(0, "variant", "M5B"); T.insert(1, "rr", 1.5)
    T.to_csv(R1.OUT / "xau_h1_reference_M5B_rr1.5.csv", index=False)
    P.FLOOR = "5min"
    r = P.compare("V9M5B_RR1.5_every_tick", "M5B", 1.5, rid)
    r["python_expR_net"] = round(T.R_net.mean(), 4); r["python_sumR_net"] = round(T.R_net.sum(), 1)
    pd.DataFrame([r]).to_csv(ROOT / "research" / "V9_M5_PARITY.csv", index=False)
    print(json.dumps(r, default=str, indent=1))


if __name__ == "__main__":
    main()


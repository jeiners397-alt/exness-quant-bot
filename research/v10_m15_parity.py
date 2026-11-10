"""V10 - paridad Python vs MT5 del control M15 (EA V8 variante 1: primera vela que cierra fuera del rango de 96 velas, Cooldown 16, hold 96, RR 3, modelo OHLC 1 min)."""
from __future__ import annotations

import json

import pandas as pd

from research.v10_common import R1, ROOT
from research import v10_m15 as M
from research import v8_parity as P


def main():
    rid = next(p.name for p in (ROOT / "results" / "v4_runs").iterdir() if p.name.endswith("V10M15B_RR3_015"))
    d = M.prep(); idx, dr = M.fam_breakout96(d)
    R1.MAXH = 96
    T = R1.trades(d, idx, dr, 3.0); T.insert(0, "variant", "M15B"); T.insert(1, "rr", 3.0)
    T.to_csv(R1.OUT / "xau_h1_reference_M15B_rr3.0.csv", index=False)
    P.FLOOR = "15min"
    r = P.compare("V10M15B_RR3", "M15B", 3.0, rid)
    r["python_expR_net"] = round(T.R_net.mean(), 4); r["python_sumR_net"] = round(T.R_net.sum(), 1)
    pd.DataFrame([r]).to_csv(ROOT / "research" / "V10_M15_PARITY.csv", index=False)
    print(json.dumps(r, default=str, indent=1))


if __name__ == "__main__":
    main()

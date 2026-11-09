"""Lanza UNA prueba en el Strategy Tester via INI. NUNCA cierra el terminal (ShutdownTerminal=0).

Uso: python scripts/04_run_tester.py --run-id T001 --strategy 1 --symbol EURUSDm --tf M15 --from 2025.01.01 --to 2025.03.31 --model 4 --sizing 0
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from remix_lab import mt5_tester as mt, load_config, RESULTS_DIR  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--run-id", required=True)
ap.add_argument("--strategy", type=int, default=1)
ap.add_argument("--symbol", default="EURUSDm")
ap.add_argument("--tf", default="M15")
ap.add_argument("--from", dest="d_from", default="2025.01.01")
ap.add_argument("--to", dest="d_to", default="2025.03.31")
ap.add_argument("--model", type=int, default=4)           # 4 = ticks reales
ap.add_argument("--sizing", type=int, default=0)          # 0 estricta, 1 lote minimo
ap.add_argument("--wait", type=int, default=900)
a = ap.parse_args()

cfg = load_config()
if a.d_to.replace(".", "-") > cfg["splits"]["in_sample_end"]:
    sys.exit("RECHAZADO: el periodo invade el holdout.")
dp = mt.data_path()
out = RESULTS_DIR / "tester" / a.run_id
out.mkdir(parents=True, exist_ok=True)
rep_rel = f"REMIX\\{a.run_id}"
rep_html = dp / f"{rep_rel}.htm"
for ext in (".htm", ".html", ".png"):
    p = dp / f"{rep_rel}{ext}"
    if p.exists():
        p.unlink()
inputs = {"Strategy_ID": a.strategy, "RiskPercent": cfg["account"]["risk_pct"], "SizingPolicy": a.sizing,
          "ExportDeals": "true"}
ini = mt.build_ini(out / f"{a.run_id}.ini", symbol=a.symbol, period=a.tf, from_date=a.d_from, to_date=a.d_to,
                   model=a.model, deposit=cfg["account"]["initial_capital"], leverage=500, report=rep_rel,
                   inputs=inputs, shutdown=False)
meta = dict(run_id=a.run_id, started_utc=datetime.now(timezone.utc).isoformat(), args=vars(a), inputs=inputs,
            ea_sha256=__import__("hashlib").sha256(mt.EA_SRC.read_bytes()).hexdigest())
(out / "meta.json").write_text(json.dumps(meta, indent=2))
print("INI:", ini)
mt.run_tester_nowait = None
import subprocess  # noqa: E402
subprocess.Popen(f'"{mt.TERMINAL_EXE}" /config:"{ini}"')
t0 = time.time()
while time.time() - t0 < a.wait:
    if rep_html.exists() and rep_html.stat().st_size > 0:
        time.sleep(3)
        print("INFORME:", rep_html)
        (out / rep_html.name).write_bytes(rep_html.read_bytes())
        print(mt.parse_html_report(rep_html))
        sys.exit(0)
    time.sleep(5)
print("TIMEOUT sin informe. Revise el log del Tester:", dp / "Tester" / "logs")
sys.exit(2)

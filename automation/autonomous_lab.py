"""Orquestador del laboratorio V4 con checkpoints. Etapas: pruebas unitarias -> compilacion -> test MT5 aislado -> informe -> clasificacion ->
cola de respaldo. Cada etapa registra su estado; si una precondicion falta (p. ej. cuenta para el Tester) se registra BLOQUEADO, no se simula.
Limites: <=20 experimentos por lote, <=2 procesos MT5 (por defecto 1), tiempo maximo por experimento. Solo Strategy Tester."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation import drive_backup, experiment_selector as sel  # noqa: E402
from automation.compile_ea import compile_ea  # noqa: E402
from automation.parse_mt5_report import parse_report  # noqa: E402
from automation.run_mt5_test import run_id, run_test  # noqa: E402

CK = ROOT / "results" / "v4_runs" / "CHECKPOINT.json"


def ck_load() -> dict:
    return json.loads(CK.read_text(encoding="utf-8")) if CK.exists() else {"done": {}}


def ck_save(d: dict) -> None:
    CK.parent.mkdir(parents=True, exist_ok=True)
    CK.write_text(json.dumps(d, indent=1), encoding="utf-8")


def unit_tests() -> bool:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "tests"], cwd=ROOT, capture_output=True, text=True)
    print(r.stdout[-300:])
    return r.returncode == 0


def run_mt5_experiment(*, ea_src: Path, expert: str, symbol: str, period: str, strategy: str, inputs: dict, from_date: str, to_date: str,
                       deposit=3000.0, leverage=500, model="ohlc_1m", timeout=1800) -> dict:
    ck = ck_load()
    c = compile_ea(ea_src)
    if not c["ok"]:
        return {"stage": "compile", "status": "FALLO_COMPILACION", "detail": c["error_lines"]}
    rid = run_id(symbol, period, strategy, len(ck["done"]) + 1)
    meta = run_test(rid=rid, expert=expert, symbol=symbol, period=period, from_date=from_date, to_date=to_date, inputs=inputs, strategy=strategy,
                    deposit=deposit, leverage=leverage, model=model, timeout=timeout, ea_version=c["sha256_src"][:12])
    out = ROOT / "results" / "v4_runs" / rid
    if meta["status"] in ("OK", "SIN_OPERACIONES"):
        meta["parsed"] = parse_report(Path(meta["report"]), out)["stats"]
        for f in out.glob("*"):
            if f.suffix in (".csv", ".json", ".htm", ".set"):
                drive_backup.enqueue(f, "04", rid)
    ck["done"][rid] = {"status": meta["status"], "utc": datetime.now(timezone.utc).isoformat()}
    ck_save(ck)
    from automation import drive_sync                  # respaldo automatico tras cada experimento
    drive_sync.sync_after_batch(rid)
    return meta


if __name__ == "__main__":
    b = sel.select_batch()
    print(f"{len(b)} hipotesis planificadas en el lote (max {sel.MAX_PER_BATCH}):")
    for r in b:
        print(" ", r["exp_id"], r["hypothesis"])

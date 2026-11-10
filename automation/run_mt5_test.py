"""Ejecutor automatico del Strategy Tester de MT5 en una instancia AISLADA (portable). Nunca toca ni cierra el terminal principal de Exness.

Flujo: genera .set + .ini (formato oficial [Tester]/[TesterInputs]) -> lanza `terminal64.exe /portable /config:<ini>` -> vigila proceso e informe
-> clasifica el resultado (OK / SIN_OPERACIONES / SIN_INFORME / INFORME_INCOMPLETO / TIMEOUT / ERROR_INICIO) y guarda metadatos.
SOLO Strategy Tester: no usa mt5.order_send ni abre operaciones fuera del probador."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAB = Path(os.environ.get("REMIX_LAB_TERMINAL", r"C:\REMIX_MT5_LAB\terminal"))
MAIN_TERMINAL_DIR = Path(r"C:\Program Files\MetaTrader 5 EXNESS")
RUNS = ROOT / "results" / "v4_runs"

MODEL = {"every_tick": 0, "ohlc_1m": 1, "open_prices": 2, "real_ticks": 4}


def sha_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip() or "NO_GIT"
    except Exception:
        return "NO_GIT"


def run_id(symbol: str, period: str, strategy: str, seq: int = 1) -> str:
    return f"RUN_{datetime.now(timezone.utc):%Y%m%d}_{symbol}_{period}_{strategy}_{seq:03d}"


def write_set(path: Path, inputs: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\r\n".join(f"{k}={v}" for k, v in inputs.items()) + "\r\n", encoding="utf-16")
    return path


def build_ini(path: Path, *, expert: str, symbol: str, period: str, from_date: str, to_date: str, deposit=3000.0, currency="USD", leverage=200,
              model=1, report: str, inputs: dict | None = None, set_name: str | None = None, shutdown=True) -> Path:
    """INI oficial. Las entradas van en [TesterInputs] (clave=valor) y ademas se genera un .set equivalente."""
    L = ["[Tester]", f"Expert={expert}", f"Symbol={symbol}", f"Period={period}", f"Model={model}", f"ExecutionMode={os.environ.get('V8_EXECMODE', '0')}", "Optimization=0",
         f"FromDate={from_date}", f"ToDate={to_date}", "ForwardMode=0", f"Deposit={deposit}", f"Currency={currency}", f"Leverage={leverage}",
         f"Report={report}", "ReplaceReport=1", f"ShutdownTerminal={1 if shutdown else 0}", "Visual=0"]
    if set_name:
        L.append(f"ExpertParameters={set_name}")
    L += ["", "[TesterInputs]"] + [f"{k}={v}" for k, v in (inputs or {}).items()]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\r\n".join(L) + "\r\n", encoding="utf-16")
    return path


def _lab_procs() -> list[int]:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"],
                         capture_output=True, text=True).stdout.strip()
    if not out:
        return []
    d = json.loads(out)
    d = d if isinstance(d, list) else [d]
    return [x["ProcessId"] for x in d if str(x.get("ExecutablePath", "")).lower().startswith(str(LAB).lower())]


def main_terminal_alive() -> bool:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Select-Object -ExpandProperty ExecutablePath"],
                         capture_output=True, text=True).stdout
    return str(MAIN_TERMINAL_DIR).lower() in out.lower()


def classify(report_path: Path, started: float) -> tuple[str, str]:
    if not report_path.exists():
        return "SIN_INFORME", f"no existe {report_path}"
    if report_path.stat().st_mtime < started - 2:
        return "SIN_INFORME", "el informe es anterior al lanzamiento (no regenerado)"
    b = report_path.read_bytes()
    t = b.decode("utf-16", errors="ignore") if b[:2] in (b"\xff\xfe", b"\xfe\xff") else b.decode("utf-8", errors="ignore")
    if "Strategy Tester Report" not in t and "Informe del Probador" not in t and "Total Net Profit" not in t and "Beneficio neto total" not in t:
        return "INFORME_INCOMPLETO", "sin cabecera/estadisticas"
    m = re.search(r"(Total Trades|Total de operaciones)[^0-9]*?(\d+)", re.sub(r"<[^>]+>", " ", t))
    if m and int(m.group(2)) == 0:
        return "SIN_OPERACIONES", "informe valido con 0 operaciones (ausencia de senales, no fallo tecnico)"
    return "OK", ""


def run_test(*, rid: str, expert: str, symbol: str, period: str, from_date: str, to_date: str, inputs: dict, strategy: str = "",
             deposit=3000.0, leverage=200, model="ohlc_1m", timeout=1800, ea_version: str = "", extra_meta: dict | None = None) -> dict:
    assert LAB.exists() and (LAB / "terminal64.exe").exists(), "instancia aislada ausente"
    assert str(LAB).lower() != str(MAIN_TERMINAL_DIR).lower(), "el terminal principal no se usa"
    out_dir = RUNS / rid
    out_dir.mkdir(parents=True, exist_ok=True)
    report_name = f"REMIX\\{rid}"
    ini = out_dir / f"{rid}.ini"
    set_path = LAB / "MQL5" / "Profiles" / "Tester" / f"{rid}.set"
    write_set(set_path, inputs)
    write_set(out_dir / f"{rid}.set", inputs)
    build_ini(ini, expert=expert, symbol=symbol, period=period, from_date=from_date, to_date=to_date, deposit=deposit, leverage=leverage,
              model=MODEL[model], report=report_name, inputs=inputs, set_name=f"{rid}.set")
    cfg_hash = sha_text(ini.read_text(encoding="utf-16"))
    (LAB / "REMIX").mkdir(exist_ok=True)
    live_ini = LAB.parent / "ini" / f"{rid}.ini"            # ruta SIN espacios: MT5 no carga /config con espacios entre comillas
    live_ini.parent.mkdir(exist_ok=True)
    live_ini.write_bytes(ini.read_bytes())
    main_before = main_terminal_alive()
    report_html = LAB / f"{report_name}.htm"
    for p in (report_html, report_html.with_suffix(".html")):
        if p.exists():
            p.unlink()
    started = time.time()
    status, detail = "ERROR_INICIO", ""
    proc = subprocess.Popen([str(LAB / "terminal64.exe"), "/portable", f"/config:{live_ini}"], cwd=str(LAB))
    try:
        while True:
            if proc.poll() is not None:
                break
            if time.time() - started > timeout:
                status, detail = "TIMEOUT", f"supero {timeout}s"
                break
            time.sleep(5)
    finally:
        if proc.poll() is None:                                   # solo se termina el PID lanzado por nosotros y si es de la instancia aislada
            if proc.pid in _lab_procs():
                proc.terminate()
                try:
                    proc.wait(30)
                except Exception:
                    proc.kill()
    elapsed = time.time() - started
    rep = next((p for p in (report_html, report_html.with_suffix(".html")) if p.exists()), report_html)
    if status != "TIMEOUT":
        status, detail = classify(rep, started)
    if rep.exists():
        (out_dir / "report.htm").write_bytes(rep.read_bytes())
    # logs del tester (solo lectura)
    logs = sorted((LAB / "Tester" / "logs").glob("*.log"), key=lambda p: p.stat().st_mtime) if (LAB / "Tester" / "logs").exists() else []
    if logs:
        (out_dir / "tester_log.txt").write_bytes(logs[-1].read_bytes())
    meta = dict(run_id=rid, utc=datetime.now(timezone.utc).isoformat(), symbol=symbol, period=period, strategy=strategy, expert=expert,
                ea_version=ea_version, inputs=inputs, capital=deposit, currency="USD", leverage=leverage, model=model, from_date=from_date,
                to_date=to_date, git_commit=git_commit(), config_hash=cfg_hash, status=status, detail=detail, elapsed_s=round(elapsed, 1),
                report=str(out_dir / "report.htm") if rep.exists() else None, isolated_instance=str(LAB), main_terminal_alive_before=main_before,
                main_terminal_alive_after=main_terminal_alive(), **(extra_meta or {}))
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    return meta


if __name__ == "__main__":
    print("usar desde automation.autonomous_lab o ver docs/MT5_AUTOMATION_VERIFICATION.md")

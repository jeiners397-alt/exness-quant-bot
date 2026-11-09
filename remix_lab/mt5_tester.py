"""Automatizacion del Strategy Tester: compilar con MetaEditor, generar INI, lanzar y leer resultados.

No modifica la instalacion de Exness ni EAs existentes: el EA se despliega SOLO como
<data>\\MQL5\\Experts\\REMIX\\REMIX_STRATEGY_RESEARCH_LAB_V1.mq5 (carpeta nueva) y nunca
sobrescribe un archivo que no sea el propio.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path

from . import ROOT

EA_NAME = "REMIX_STRATEGY_RESEARCH_LAB_V1"
EA_SRC = ROOT / "mql5" / f"{EA_NAME}.mq5"
TERMINAL_DIR = Path(r"C:\Program Files\MetaTrader 5 EXNESS")
METAEDITOR = TERMINAL_DIR / "MetaEditor64.exe"
TERMINAL_EXE = TERMINAL_DIR / "terminal64.exe"

PERIOD_NAMES = {"M1": "M1", "M5": "M5", "M15": "M15", "M30": "M30", "H1": "H1", "H4": "H4", "D1": "D1"}


def data_path() -> Path:
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize fallo: {mt5.last_error()}")
    p = Path(mt5.terminal_info().data_path)
    mt5.shutdown()
    return p


def deploy_ea(dp: Path) -> Path:
    dst_dir = dp / "MQL5" / "Experts" / "REMIX"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / EA_SRC.name
    shutil.copy2(EA_SRC, dst)           # solo nuestro archivo, en nuestra carpeta
    return dst


def compile_ea(dst: Path) -> dict:
    """Compila con MetaEditor. Devuelve errores/avisos parseados del log."""
    log = dst.with_suffix(".compile.log")
    if log.exists():
        log.unlink()
    # cadena unica: MetaEditor exige /compile:"ruta con espacios" (comillas solo en el valor)
    cmd = f'"{METAEDITOR}" /compile:"{dst}" /log:"{log}"'
    subprocess.run(cmd, timeout=180)        # el codigo de salida de MetaEditor no es fiable; se lee el log
    txt = ""
    for _ in range(20):
        if log.exists():
            txt = log.read_bytes().decode("utf-16", errors="ignore") if log.read_bytes()[:2] in (b"\xff\xfe", b"\xfe\xff") \
                else log.read_text(errors="ignore")
            if "Result" in txt or "result" in txt:
                break
        time.sleep(0.5)
    m = re.search(r"Result:\s*(\d+)\s*errors?,\s*(\d+)\s*warnings?", txt, re.I)
    ex5 = dst.with_suffix(".ex5")
    return dict(log=txt, errors=int(m.group(1)) if m else None, warnings=int(m.group(2)) if m else None,
                ex5_exists=ex5.exists(), ex5=str(ex5))


def build_ini(path: Path, *, symbol, period, from_date, to_date, model=1, deposit=100.0, currency="USD",
              leverage=500, report="REMIX\\report", inputs: dict | None = None, shutdown=True, expert_rel=None):
    """INI de Strategy Tester. model: 0 cada tick, 1 OHLC 1 min, 2 solo precios apertura, 4 ticks reales."""
    expert = expert_rel or f"REMIX\\{EA_NAME}"
    lines = ["[Tester]", f"Expert={expert}", f"Symbol={symbol}", f"Period={period}", f"Model={model}",
             "ExecutionMode=0", "Optimization=0", f"FromDate={from_date}", f"ToDate={to_date}",
             "ForwardMode=0", f"Deposit={deposit}", f"Currency={currency}", f"Leverage={leverage}",
             f"Report={report}", "ReplaceReport=1", f"ShutdownTerminal={1 if shutdown else 0}", "Visual=0",
             "", "[TesterInputs]"]
    for k, v in (inputs or {}).items():
        lines.append(f"{k}={v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-16")   # MT5 acepta UTF-16 LE con BOM
    return path


def run_tester(ini: Path, timeout=1800):
    return subprocess.run([str(TERMINAL_EXE), f"/config:{ini}"], timeout=timeout)


def parse_html_report(path: Path) -> dict:
    """Extrae metricas basicas del informe HTML del tester (UTF-16)."""
    raw = path.read_bytes()
    txt = raw.decode("utf-16", errors="ignore") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", errors="ignore")
    txt = re.sub(r"<[^>]+>", "|", txt)
    txt = re.sub(r"\|+", "|", txt)
    out = {}
    for key, pat in {
        "total_net_profit": r"Total Net Profit:\|([-\d\s.,]+)", "profit_factor": r"Profit Factor:\|([-\d.,]+)",
        "total_trades": r"Total Trades:\|(\d+)", "max_drawdown": r"Equity Drawdown Maximal:\|([-\d\s.,]+)",
        "history_quality": r"History Quality:\|([\d%\s.]+)",
    }.items():
        m = re.search(pat, txt)
        out[key] = m.group(1).strip() if m else None
    return out

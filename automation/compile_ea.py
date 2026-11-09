"""Compilacion automatica de EAs MQL5 con MetaEditor (instancia aislada portable por defecto).

No se confia en el codigo de salida: se lee el log (UTF-16), se cuentan errores/avisos, se verifica que el EX5 exista, sea mas
reciente que el fuente y se registran los hashes. Resultado en logs/compile_registry.csv."""
from __future__ import annotations

import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAB_TERMINAL = Path(os.environ.get("REMIX_LAB_TERMINAL", r"C:\REMIX_MT5_LAB\terminal"))   # copia portable aislada


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def locate_metaeditor(terminal_dir: Path = LAB_TERMINAL) -> Path:
    for n in ("MetaEditor64.exe", "metaeditor64.exe"):
        p = terminal_dir / n
        if p.exists():
            return p
    raise FileNotFoundError(f"MetaEditor no encontrado en {terminal_dir}")


def compile_ea(src: Path, terminal_dir: Path = LAB_TERMINAL, portable: bool = True, timeout: int = 240, subdir: str = "REMIX") -> dict:
    src = Path(src).resolve()
    me = locate_metaeditor(terminal_dir)
    dst_dir = terminal_dir / "MQL5" / "Experts" / subdir if portable else None
    if dst_dir is None:
        raise ValueError("solo se admite compilar dentro de la instancia aislada (portable)")
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    log = dst.with_suffix(".compile.log")
    for p in (log, dst.with_suffix(".ex5")):
        if p.exists():
            p.unlink()
    t0 = time.time()
    cmd = f'"{me}" /portable /compile:"{dst}" /log:"{log}"'
    subprocess.run(cmd, timeout=timeout)                        # el codigo de salida de MetaEditor NO es fiable
    txt = ""
    for _ in range(40):
        if log.exists():
            b = log.read_bytes()
            txt = b.decode("utf-16", errors="ignore") if b[:2] in (b"\xff\xfe", b"\xfe\xff") else b.decode("utf-8", errors="ignore")
            if re.search(r"Result:", txt, re.I):
                break
        time.sleep(0.5)
    m = re.search(r"Result:\s*(\d+)\s*errors?,\s*(\d+)\s*warnings?", txt, re.I)
    ex5 = dst.with_suffix(".ex5")
    errors = int(m.group(1)) if m else None
    warnings = int(m.group(2)) if m else None
    ex5_ok = ex5.exists() and ex5.stat().st_mtime >= t0 - 2 and ex5.stat().st_mtime >= dst.stat().st_mtime - 2
    err_lines = [l.strip() for l in txt.splitlines() if re.search(r"\berror\b", l, re.I) and "Result" not in l]
    warn_lines = [l.strip() for l in txt.splitlines() if re.search(r"\bwarning\b", l, re.I) and "Result" not in l]
    res = dict(source=str(src), deployed=str(dst), ex5=str(ex5), errors=errors, warnings=warnings, ex5_exists=ex5.exists(), ex5_fresh=bool(ex5_ok),
               sha256_src=sha256(src), sha256_deployed=sha256(dst), sha256_ex5=sha256(ex5) if ex5.exists() else "",
               ex5_mtime=datetime.fromtimestamp(ex5.stat().st_mtime, timezone.utc).isoformat() if ex5.exists() else "",
               error_lines=err_lines[:20], warning_lines=warn_lines[:20], ok=bool(m) and errors == 0 and bool(ex5_ok), log=txt)
    _register(res)
    return res


def _register(res: dict) -> None:
    f = ROOT / "logs" / "compile_registry.csv"
    f.parent.mkdir(exist_ok=True)
    new = not f.exists()
    with f.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["utc", "source", "errors", "warnings", "ex5_fresh", "sha256_src", "sha256_ex5", "ok"])
        w.writerow([datetime.now(timezone.utc).isoformat(), Path(res["source"]).name, res["errors"], res["warnings"], res["ex5_fresh"],
                    res["sha256_src"], res["sha256_ex5"], res["ok"]])


if __name__ == "__main__":
    r = compile_ea(Path(sys.argv[1]))
    print({k: v for k, v in r.items() if k != "log"})
    sys.exit(0 if r["ok"] else 1)

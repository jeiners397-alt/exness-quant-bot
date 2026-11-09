"""Escaner OFICIAL de MT5: Optimization=3 ("All Symbols Selected in Market Watch", https://www.metatrader5.com/en/terminal/help/start_advanced/start).
Pasos: (1) deja en Market Watch SOLO los simbolos pedidos (symbol_select, verificado con symbols_get(group)); (2) escribe el INI; (3) lanza la instancia aislada;
(4) vigila el fin; (5) verifica cuantos simbolos/pasadas se procesaron (logs del Tester + cache .opt) y (6) intenta recuperar metricas. Si el escaner no permite
exportar las metricas necesarias de forma automatica, se usa el metodo alternativo: multi_market_batch_runner (una ejecucion oficial por simbolo)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

import MetaTrader5 as mt5

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation.run_mt5_test import LAB, MODEL, build_ini, write_set  # noqa: E402

OUT = ROOT / "results" / "v5_scanner"


def select_market_watch(symbols: list[str]) -> dict:
    """Deja seleccionados exactamente `symbols` en el Market Watch de la instancia aislada y devuelve la lista verificada."""
    assert mt5.initialize(path=str(LAB / "terminal64.exe"), portable=True), mt5.last_error()
    # la deseleccion es ASINCRONA: se repite hasta que el Market Watch contenga solo lo pedido (maximo ~2 min)
    for _ in range(40):
        extra = [s.name for s in (mt5.symbols_get() or []) if s.select and s.name not in symbols]
        if not extra:
            break
        for n in extra:
            mt5.symbol_select(n, False)
        time.sleep(3)
    failed = [s for s in symbols if not mt5.symbol_select(s, True)]
    time.sleep(2)
    sel = sorted(s.name for s in (mt5.symbols_get() or []) if s.select)
    mt5.shutdown()
    return dict(requested=symbols, selected=sel, failed_select=failed, exact_match=sorted(symbols) == sel)


def stop_lab() -> None:
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | Where-Object { $_.ExecutablePath -like 'C:\\REMIX_MT5_LAB\\*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"])
    time.sleep(3)


def run_scan(tag: str, symbols: list[str], expert: str, inputs: dict, period: str, from_date: str, to_date: str, model="ohlc_1m", deposit=3000.0, leverage=500, timeout=3600) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    mw = select_market_watch(symbols)
    stop_lab()                                                   # el Tester necesita la instancia sin otra conexion de Python
    (OUT / f"{tag}_marketwatch.json").write_text(json.dumps(mw, indent=1), encoding="utf-8")
    ini = LAB.parent / "ini" / f"{tag}.ini"
    ini.parent.mkdir(exist_ok=True)
    # INI oficial: Optimization=3 (todos los simbolos seleccionados en Market Watch). Symbol= es obligatorio por sintaxis, pero el modo 3 recorre el Market Watch.
    build_ini(ini, expert=expert, symbol=symbols[0], period=period, from_date=from_date, to_date=to_date, deposit=deposit, leverage=leverage, model=MODEL[model],
              report=f"REMIX\\{tag}", inputs=inputs, set_name=f"{tag}.set")
    txt = ini.read_text(encoding="utf-16").replace("Optimization=0", "Optimization=3")
    ini.write_text(txt, encoding="utf-16")
    write_set(LAB / "MQL5" / "Profiles" / "Tester" / f"{tag}.set", inputs)
    (OUT / f"{tag}.ini").write_bytes(ini.read_bytes())
    cache_before = {p: p.stat().st_mtime for p in (LAB / "Tester").rglob("*.opt")}
    t0 = time.time()
    proc = subprocess.Popen([str(LAB / "terminal64.exe"), "/portable", f"/config:{ini}"], cwd=str(LAB))
    status = "OK"
    while proc.poll() is None:
        if time.time() - t0 > timeout:
            status = "TIMEOUT"; stop_lab(); break
        time.sleep(5)
    # verificacion: pasadas procesadas segun logs del Tester y archivos .opt nuevos
    logs = sorted((LAB / "Tester" / "logs").glob("*.log"), key=lambda p: p.stat().st_mtime)
    text = ""
    if logs:
        b = logs[-1].read_bytes()
        text = b.decode("utf-16", errors="ignore") if b[:2] == b"\xff\xfe" else b.decode("utf-8", errors="ignore")
    passes = len(re.findall(r"pass \d+ returned|\bpass\b.*?(?:finished|done)", text, re.I))
    opts = [str(p) for p, m in ((p, p.stat().st_mtime) for p in (LAB / "Tester").rglob("*.opt")) if m > t0 - 2 or p not in cache_before]
    per_symbol = sorted(set(re.findall(r"final balance[^\n]*", text)))[:50]
    res = dict(tag=tag, status=status, seconds=round(time.time() - t0, 1), market_watch=mw, n_symbols_requested=len(symbols), new_opt_files=opts,
               passes_detected_in_log=passes, tester_log_tail=text.splitlines()[-25:], final_balance_lines=len(per_symbol))
    (OUT / f"{tag}_result.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    (OUT / f"{tag}_tester.log").write_text(text[-60000:], encoding="utf-8")
    return res


if __name__ == "__main__":
    print("usar run_scan(...) o research/v5_scanner_probe.py")

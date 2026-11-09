"""Deja la copia portable (C:\\REMIX_MT5_LAB\\terminal) SIN cuenta, SIN graficos con EAs y SIN credenciales. Solo toca esa carpeta.
El Strategy Tester trabaja sin conexion con el historial/ticks copiados. Es defensa para que la instancia aislada no pueda operar nunca en la cuenta demo."""
import os
import shutil
from pathlib import Path

LAB = Path(os.environ.get("REMIX_LAB_TERMINAL", r"C:\REMIX_MT5_LAB\terminal")).resolve()
assert str(LAB).lower().startswith("c:\\remix_mt5_lab"), "solo la copia aislada"


def isolate() -> dict:
    done = {}
    acc = LAB / "config" / "accounts.dat"
    if acc.exists():
        acc.unlink(); done["accounts.dat"] = "borrado"
    charts = LAB / "MQL5" / "Profiles" / "Charts"
    if charts.exists():
        shutil.rmtree(charts)
    (charts / "Default").mkdir(parents=True, exist_ok=True)
    done["charts"] = "vaciados"
    for ini in (LAB / "config").glob("*.ini"):
        raw = ini.read_bytes()
        enc = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8"
        lines = raw.decode(enc, errors="ignore").splitlines()
        keep = [l for l in lines if not l.strip().lower().startswith(("login=", "password=", "server=", "environment=", "lastexpert=", "expert="))]
        if len(keep) != len(lines):
            ini.write_bytes(("\r\n".join(keep) + "\r\n").encode(enc if enc != "utf-16" else "utf-16"))
            done[ini.name] = f"{len(lines) - len(keep)} claves de cuenta/EA eliminadas"
    return done


if __name__ == "__main__":
    print(isolate())

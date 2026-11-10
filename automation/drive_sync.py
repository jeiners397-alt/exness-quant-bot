"""Sincronizacion de resultados REMIX (V4, V5, V6...) hacia Google Drive para escritorio (G:\\).

Principios:
- Copia (nunca mueve) a la carpeta REMIX EXISTENTE de Drive; no crea otra carpeta raiz.
- Nunca sobrescribe: carpeta unica por sincronizacion (SYNC_ID) o carpeta por RUN_ID; si el destino existe con otro hash se agrega __<sha8>.
- Lista blanca de extensiones + exclusiones (credenciales, .env, .mcp, logs privados/masivos, datos historicos, temporales) + escaneo de secretos.
- Integridad: SHA-256 origen == SHA-256 de la copia releida desde G:. Estado LOCAL_COPIED_VERIFIED.
- Estado de nube: solo CLOUD_CONFIRMED cuando se registra confirmacion externa (conector de Drive: existe en la carpeta con mismo tamano);
  hasta entonces la copia queda como COPIED_LOCAL_PENDING_CLOUD. Este modulo no inventa confirmaciones.
Uso:  python -m automation.drive_sync --label V5_PENDING        (sincroniza)
      python -m automation.drive_sync --confirm-cloud confirm.json (registra confirmaciones de nube)
      python -m automation.drive_sync --selftest                   (archivo de verificacion pequeno)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BK = ROOT / "backup"
MANIFEST = BK / "DRIVE_BACKUP_MANIFEST.csv"
SYNC_LOG = BK / "DRIVE_SYNC_LOG.csv"
DRIVE_DESKTOP_ROOT = Path("G:/Mi unidad/REMIX FOREX V1 \u2014 Adaptive Quantitative Trading System")
F04 = "04_Backtests y resultados"
F05 = "05_Informes y auditor\u00edas"
BASE_FIELDS = ["name", "local_path", "type", "size_bytes", "sha256", "date_utc", "upload_state", "drive_id", "drive_link", "experiment_id", "drive_folder"]
NEW_FIELDS = ["sync_id", "drive_desktop_path", "copy_sha256", "copy_verified", "cloud_state", "cloud_confirmed_utc", "cloud_evidence", "method"]
FIELDS = BASE_FIELDS + NEW_FIELDS

ALLOWED_EXT = {".htm", ".html", ".csv", ".json", ".md", ".set", ".ini", ".xlsx", ".txt"}
EXCLUDE_NAMES = ("tester_log", ".env", ".mcp", "accounts.dat", "credential", "password", "secret", "token", "id_rsa", "terminal.ini", "common.ini")
EXCLUDE_DIRS = {"data", "raw", ".git", ".claude", "__pycache__", "tmp", "temp", "cache", "node_modules", ".venv", "v5_scanner"}
MAX_BYTES = 30 * 1024 * 1024
SECRET_RX = [re.compile(r"(?i)\b(password|passwd|api[_-]?key|secret|bearer)\b\s*[=:]\s*[^\s<\"']{6,}"),
             re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"), re.compile(r"\b(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b"),
             re.compile(r"(?im)^\s*(Login|Password|Server)\s*=")]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_sync_id(label: str) -> str:
    return f"SYNC_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{re.sub(r'[^A-Za-z0-9_-]', '', label)[:30] or 'MANUAL'}"


def _read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in FIELDS:
            r.setdefault(k, "")
    return rows


def _write(p: Path, rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore"); w.writeheader(); w.writerows(rows)


def check_root(root: Path = DRIVE_DESKTOP_ROOT) -> None:
    """Falla si la carpeta REMIX existente no esta montada o no contiene las subcarpetas 04 y 05 (no crea una carpeta nueva)."""
    if not (root / F04).is_dir() or not (root / F05).is_dir():
        raise RuntimeError(f"Carpeta REMIX existente no encontrada/incompleta: {root}")


def excluded(p: Path) -> str:
    low = p.name.lower()
    if p.suffix.lower() not in ALLOWED_EXT:
        return "extension no permitida"
    if any(x in low for x in EXCLUDE_NAMES):
        return "nombre sensible/log masivo"
    if any(part.lower() in EXCLUDE_DIRS for part in p.relative_to(ROOT).parts[:-1]):
        return "directorio excluido"
    if p.stat().st_size > MAX_BYTES:
        return "demasiado grande"
    if p.stat().st_size == 0:
        return "vacio"
    return ""


def secret_hit(p: Path) -> str:
    if p.suffix.lower() == ".xlsx":
        return ""
    try:
        raw = p.read_bytes()
        txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", "ignore")
    except Exception:
        return "ilegible"
    for rx in SECRET_RX:
        if rx.search(txt):
            return rx.pattern[:40]
    return ""


def discover() -> list[tuple[Path, str, str, str]]:
    """(origen, carpeta Drive 04/05, subruta relativa, tipo). Las ejecuciones usan su RUN_ID (unico); lo mutable va por SYNC_ID."""
    out = []
    for runs in sorted((ROOT / "results").glob("v[0-9]*_runs")):
        ver = runs.name.split("_")[0].upper()
        for d in sorted(runs.glob("RUN_*")):
            for f in sorted(d.iterdir()):
                if f.is_file():
                    out.append((f, F04, f"AUTO_SYNC/{ver}_runs/{d.name}", "run"))
    for f in sorted((ROOT / "research").glob("*")):
        if f.is_file():
            out.append((f, F04, "research", "research"))
    for f in sorted((ROOT / "docs").glob("*.md")):
        out.append((f, F05, "docs", "report"))
    for f in sorted((ROOT / "logs").glob("compile_registry.csv")):
        out.append((f, F05, "audit", "audit"))
    for f in sorted(BK.glob("DRIVE_BACKUP_STATUS.md")):
        out.append((f, F05, "audit", "audit"))
    return out


def sync(label: str, root: Path = DRIVE_DESKTOP_ROOT, extra: list[tuple[Path, str, str, str]] | None = None, dry: bool = False) -> dict:
    check_root(root)
    sid = new_sync_id(label)
    rows = _read(MANIFEST)
    done = {(r["sha256"], r["name"]) for r in rows if r.get("drive_desktop_path")}
    stats = dict(sync_id=sid, copied=0, skipped_same=0, excluded=0, secret_blocked=0, failed=0)
    log = _read(SYNC_LOG) if SYNC_LOG.exists() else []
    for src, top, sub, typ in (extra if extra is not None else discover()):
        why = excluded(src)
        if why:
            stats["excluded"] += 1; continue
        h = sha256(src)
        if (h, src.name) in done:
            stats["skipped_same"] += 1; continue
        if secret_hit(src):
            stats["secret_blocked"] += 1; log.append(dict(name=src.name, local_path=str(src), sha256=h, note="BLOQUEADO secreto", sync_id=sid)); continue
        dest_dir = root / top / (sub if typ == "run" else f"AUTO_SYNC/{sid}/{sub}")
        dest = dest_dir / src.name
        if dest.exists():                                    # nunca sobrescribir: otro hash => sufijo __sha8
            if sha256(dest) == h:
                stats["skipped_same"] += 1; continue
            dest = dest_dir / f"{src.stem}__{h[:8]}{src.suffix}"
        if dry:
            stats["copied"] += 1; continue
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            ch = sha256(dest)
        except Exception as e:                                # noqa: BLE001
            stats["failed"] += 1; log.append(dict(name=src.name, local_path=str(src), sha256=h, note=f"ERROR {e}", sync_id=sid)); continue
        ok = ch == h
        stats["copied" if ok else "failed"] += 1
        rows.append(dict(name=src.name, local_path=str(src.relative_to(ROOT)), type=src.suffix.lstrip("."), size_bytes=src.stat().st_size, sha256=h,
                         date_utc=_utc(), upload_state="COPIED_LOCAL_PENDING_CLOUD" if ok else "COPY_HASH_MISMATCH", drive_id="", drive_link="",
                         experiment_id=sub.split("/")[-1] if typ == "run" else "", drive_folder=top[:2], sync_id=sid,
                         drive_desktop_path=str(dest.relative_to(root)).replace("\\", "/"), copy_sha256=ch, copy_verified="YES" if ok else "NO",
                         cloud_state="NOT_CONFIRMED" if ok else "", cloud_confirmed_utc="", cloud_evidence="", method="drive_desktop_copy"))
    if not dry:
        _write(MANIFEST, rows)
        _write_log(log, sid, stats)
    return stats


def _write_log(log: list[dict], sid: str, stats: dict) -> None:
    SYNC_LOG.parent.mkdir(exist_ok=True)
    new = not SYNC_LOG.exists()
    with SYNC_LOG.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["sync_id", "utc", "copied", "skipped_same", "excluded", "secret_blocked", "failed"])
        w.writerow([sid, _utc(), stats["copied"], stats["skipped_same"], stats["excluded"], stats["secret_blocked"], stats["failed"]])


def verify_copies(root: Path = DRIVE_DESKTOP_ROOT) -> dict:
    """Relee cada copia en G: y compara SHA-256 con el manifiesto (integridad local)."""
    res = dict(checked=0, ok=0, missing=0, mismatch=0)
    for r in _read(MANIFEST):
        if not r["drive_desktop_path"]:
            continue
        res["checked"] += 1
        p = root / r["drive_desktop_path"]
        if not p.exists():
            res["missing"] += 1
        elif sha256(p) == r["sha256"]:
            res["ok"] += 1
        else:
            res["mismatch"] += 1
    return res


def confirm_cloud(confirmations: list[dict]) -> int:
    """confirmations: [{drive_desktop_path, drive_id, size_bytes, evidence}] obtenidas del conector (busqueda por nombre/carpeta en la nube).
    Solo se marca CLOUD_CONFIRMED si hay drive_id real y el tamano en la nube coincide con el manifiesto."""
    rows = _read(MANIFEST)
    by = {r["drive_desktop_path"]: r for r in rows if r["drive_desktop_path"]}
    n = 0
    for c in confirmations:
        r = by.get(c["drive_desktop_path"])
        if not r or not c.get("drive_id") or len(c["drive_id"]) < 10 or int(c["size_bytes"]) != int(r["size_bytes"]):
            continue
        r.update(upload_state="CLOUD_CONFIRMED", cloud_state="CLOUD_CONFIRMED", drive_id=c["drive_id"], drive_link=f"https://drive.google.com/file/d/{c['drive_id']}/view",
                 cloud_confirmed_utc=_utc(), cloud_evidence=c.get("evidence", "connector size match")[:200])
        n += 1
    _write(MANIFEST, rows)
    return n


def selftest(root: Path = DRIVE_DESKTOP_ROOT) -> dict:
    """Archivo pequeno de verificacion sin datos sensibles: se crea en results/, se sincroniza y se verifica el hash de la copia."""
    d = ROOT / "results" / "v0_sync_selftest_runs" / f"RUN_SELFTEST_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    d.mkdir(parents=True)
    f = d / "SYNC_SELFTEST.txt"
    f.write_text(f"REMIX drive_sync verificacion {_utc()}\nSin datos sensibles.\n", encoding="utf-8")
    st = sync("SELFTEST", root, extra=[(f, F04, f"AUTO_SYNC/V0_SELFTEST/{d.name}", "run")])
    return dict(file=str(f), **st)


def sync_after_batch(label: str) -> dict | None:
    """Gancho para runners (V6...): nunca interrumpe la investigacion; devuelve estadisticas o None si Drive no esta disponible."""
    try:
        return sync(label)
    except Exception as e:                                    # noqa: BLE001
        print(f"[drive_sync] no sincronizado ({e}); queda pendiente para la proxima sincronizacion", file=sys.stderr)
        return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="MANUAL"); ap.add_argument("--dry", action="store_true"); ap.add_argument("--verify", action="store_true")
    ap.add_argument("--confirm-cloud"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        print(json.dumps(selftest(), indent=1))
    elif a.confirm_cloud:
        print("confirmados:", confirm_cloud(json.loads(Path(a.confirm_cloud).read_text(encoding="utf-8-sig"))))
    elif a.verify:
        print(json.dumps(verify_copies()))
    else:
        print(json.dumps(sync(a.label, dry=a.dry), indent=1))

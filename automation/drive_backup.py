"""Cola y manifiesto de respaldo a Google Drive. Un archivo solo figura como SUBIDO cuando se registra un ID real devuelto por Drive
(`mark_uploaded`). La transferencia la realiza el conector de Drive de Claude Code (create_file) o Drive para escritorio; este modulo no
guarda credenciales ni inventa subidas."""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BK = ROOT / "backup"
QUEUE = BK / "DRIVE_UPLOAD_QUEUE.csv"
MANIFEST = BK / "DRIVE_BACKUP_MANIFEST.csv"
STATUS = BK / "DRIVE_BACKUP_STATUS.md"
FIELDS = ["name", "local_path", "type", "size_bytes", "sha256", "date_utc", "upload_state", "drive_id", "drive_link", "experiment_id", "drive_folder"]

DRIVE_ROOT = "10iMMgFDjMbk1CYpyMvC4dxrdyz7cBj5P"
FOLDERS = {"01": "1TqZ_mY589qK_E6EKl1jqSsHdcO-RGM7d", "02": "16oIZrN_VNxrsHSrkQ72GvCwKrs3QT2QN", "03": "1PuMyX9DJ0HDnd9g_zndUD7vdj1F4AYCt",
           "04": "1bhDJMGeJleKxqBbmrwO328bTDxGCjoaX", "05": "1Z-AplyTcSmEiGqUu09GSRD6Rtf4qIIkf"}
FORBIDDEN = (".env", ".mcp", "password", "token", "secret", "accounts.dat", ".ini")      # nunca se encolan


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _write(p: Path, rows: list[dict]) -> None:
    BK.mkdir(exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)


def enqueue(path: Path, folder: str, experiment_id: str = "") -> dict | None:
    path = Path(path)
    low = path.name.lower()
    if any(x in low for x in FORBIDDEN) or not path.exists():
        return None
    rows = _read(QUEUE)
    h = sha256(path)
    if any(r["sha256"] == h and r["name"] == path.name for r in rows):
        return None
    r = dict(name=path.name, local_path=str(path), type=path.suffix.lstrip("."), size_bytes=path.stat().st_size, sha256=h,
             date_utc=datetime.now(timezone.utc).isoformat(), upload_state="PENDING", drive_id="", drive_link="", experiment_id=experiment_id,
             drive_folder=folder)
    rows.append(r); _write(QUEUE, rows)
    return r


def mark_uploaded(name: str, sha: str, drive_id: str, link: str) -> None:
    """Registra la subida SOLO con un ID real de Drive."""
    assert drive_id and len(drive_id) > 10, "ID de Drive invalido: no se registra como subido"
    rows = _read(QUEUE)
    hit = False
    for r in rows:
        if r["name"] == name and r["sha256"] == sha:
            r.update(upload_state="UPLOADED", drive_id=drive_id, drive_link=link); hit = True
    assert hit, "elemento no esta en la cola"
    _write(QUEUE, rows)
    up = [r for r in rows if r["upload_state"] == "UPLOADED"]
    keys = {(r["name"], r["sha256"]) for r in up}
    extra = [r for r in _read(MANIFEST) if (r["name"], r["sha256"]) not in keys]       # conserva filas de drive_sync (columnas extra)
    allf = list(FIELDS) + [k for r in extra for k in r if k not in FIELDS]
    with MANIFEST.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(allf)), restval="", extrasaction="ignore"); w.writeheader(); w.writerows(up + extra)
    write_status()


def verify_local(rows: list[dict] | None = None) -> list[str]:
    bad = []
    for r in rows or _read(QUEUE):
        p = Path(r["local_path"])
        if not p.exists():
            bad.append(f"{r['name']}: falta"); continue
        if sha256(p) != r["sha256"]:
            bad.append(f"{r['name']}: hash cambiado")
    return bad


def write_status() -> None:
    q = _read(QUEUE)
    up = [r for r in q if r["upload_state"] == "UPLOADED"]
    pend = [r for r in q if r["upload_state"] != "UPLOADED"]
    L = ["# Estado del respaldo en Google Drive (V4)", f"Actualizado: {datetime.now(timezone.utc).isoformat()}", "",
         f"- Subidos y verificados con ID real: **{len(up)}**", f"- Pendientes: **{len(pend)}**", "",
         "## Subidos"] + [f"- {r['name']} -> {r['drive_link']} (id {r['drive_id']}, sha256 {r['sha256'][:12]}...)" for r in up] + \
        ["", "## Pendientes (NO respaldados)"] + [f"- {r['name']} ({r['size_bytes']} B) -> carpeta {r['drive_folder']}" for r in pend]
    (BK / "DRIVE_BACKUP_STATUS.md").write_text("\n".join(L) + "\n", encoding="utf-8")

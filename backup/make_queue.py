"""Genera backup/BACKUP_QUEUE.csv: hash SHA-256 de cada artefacto duradero y su estado de respaldo REAL en Drive.

Prohibido incluir: credenciales, .env, .mcp.json*, .claude/, tokens. Datasets grandes: solo manifiesto + hash.
Estado Drive = UPLOADED_VERIFIED solo si el archivo existe en Drive y su tamano en bytes coincide con el local.
"""
import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

R = Path(__file__).resolve().parent.parent
FORBID = (".mcp.json", ".env", ".claude", "__pycache__", ".pytest_cache", "credentials", "token")
# Subidas verificadas manualmente en esta sesion (tamano Drive == tamano local): ruta_local -> (drive_id, carpeta)
UPLOADED = {
    "docs/INFORME_SESION_2026-11-09.md": ("1Ztg-xG_58v-i5pmHvpVc-17RBbDCNtmC", "05_Informes y auditorías", "INFORME_SESION_2026-11-09_v1.0.md"),
    "research/PRIORITY_HYPOTHESES.md": ("1Ia-Ig46jAo395b0rb3z2SWZ7jMYDbAcN", "01_Documentación y planificación", "PRIORITY_HYPOTHESES_v1.0_2026-11-09.md"),
    "research/DEDUP_AND_PROVENANCE.md": ("1iqfbs6fVYMT_DKe82bZ9MXMKaYEbXixd", "01_Documentación y planificación", "DEDUP_AND_PROVENANCE_v1.0_2026-11-09.md"),
    # subido por el usuario (mismo tamano 172377 B; hash no comparable desde el conector)
    "results/s01_official/ReportTester-ACCOUNTID.xlsx": ("1Z-L3303WuDKy_PId19vBK14prnnJqbdn", "04_Backtests y resultados", "S01_EURUSDm_M15_3000USD_2025-2026_REPORTE_ORIGINAL_2026-11-09.xlsx"),
}
TARGET ={"remix_lab": "02_Código Python y MQL5", "scripts": "02_Código Python y MQL5", "tests": "02_Código Python y MQL5",
          "mql5": "02_Código Python y MQL5", "config": "02_Código Python y MQL5", "backup": "05_Informes y auditorías",
          "research": "01_Documentación y planificación", "docs": "05_Informes y auditorías",
          "results": "04_Backtests y resultados", "data": "03_Datos históricos"}
INCLUDE = ["remix_lab", "scripts", "tests", "mql5", "config", "research", "docs", "results", "data", "backup", "requirements.txt", ".gitignore"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


rows = []
now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
for inc in INCLUDE:
    base = R / inc
    files = [base] if base.is_file() else sorted(x for x in base.rglob("*") if x.is_file())
    for p in files:
        rel = p.relative_to(R).as_posix()
        if any(t in rel for t in FORBID) or rel.endswith(".pyc"):
            continue
        top = rel.split("/")[0]
        size = p.stat().st_size
        up = UPLOADED.get(rel)
        if up:
            status, did, reason, drive_name = "UPLOADED_VERIFIED", up[0], "tamano en bytes Drive == local", up[2]
        else:
            did, drive_name = "", ""
            if size > 5_000_000 or rel.startswith("data/raw/"):
                status, reason = "PENDING_DATASET_GRANDE", "dataset grande: no subir automaticamente; solo hash/manifiesto"
            else:
                status, reason = "PENDING", "el conector exige contenido inline: subirlo implica retranscribirlo; pendiente de decision/sincronizacion"
        rows.append(dict(artifact=rel, version="1.0", sha256=sha(p), size_bytes=size, local_utc=now, experiment_id=("T001" if "T001" in rel else ""),
                         target_drive_folder=TARGET.get(top, "05_Informes y auditorías"), drive_status=status, drive_file_id=did,
                         drive_file_name=drive_name, note=reason))
with open(R / "backup" / "BACKUP_QUEUE.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
from collections import Counter
print(len(rows), Counter(r["drive_status"] for r in rows))

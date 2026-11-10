# Sincronización automática a Google Drive (Drive para escritorio)

Módulo: `automation/drive_sync.py`. Destino: `G:\Mi unidad\REMIX FOREX V1 — Adaptive Quantitative Trading System` (la carpeta original; se verifica que existan `04_Backtests y resultados` y `05_Informes y auditorías`, no se crea ninguna otra raíz).

## Qué hace
- **Copia, no mueve**: los archivos locales y el proyecto Python/MQL5 quedan intactos.
- Origen → destino: `results/v{N}_runs/RUN_*` (informe HTML oficial, trades.csv, deals.csv, stats.json, meta.json, .ini, .set) → `04/AUTO_SYNC/V{N}_runs/<RUN_ID>/`; `research/*` (matrices, estudios de eventos, robustez, ranking, registro de experimentos) → `04/AUTO_SYNC/<SYNC_ID>/research/`; `docs/*.md` e informes de auditoría → `05/AUTO_SYNC/<SYNC_ID>/…`.
- **Sin sobrescribir**: carpeta por RUN_ID (único) o por SYNC_ID (sello UTC); si el destino existe con otro hash se guarda como `nombre__<sha8>`; los archivos con hash ya sincronizado se omiten.
- **Exclusiones**: `.env`, `.mcp*`, `accounts.dat`, nombres con password/token/secret/credential, `tester_log*` (logs privados de hasta 218 MB), `terminal.ini/common.ini`, `data/`, `raw/`, `.git`, `.claude`, caché/temporales, `*.opt`, extensiones fuera de lista blanca, archivos >30 MB; además escaneo de secretos (contraseñas, tokens tipo Telegram/GitHub/OpenAI, líneas de inicio de sesión de configuración de MT5): un hallazgo bloquea el archivo.
- **Integridad**: SHA-256 del origen = SHA-256 de la copia releída desde `G:` (`--verify`).
- **Estados honestos** (`backup/DRIVE_BACKUP_MANIFEST.csv`, columnas `upload_state`, `copy_verified`, `cloud_state`, `drive_id`, `cloud_evidence`):
  - `UPLOADED`: 11 filas históricas subidas por el conector (copias condensadas, no byte a byte).
  - `COPIED_LOCAL_PENDING_CLOUD`: copiado y hash verificado en `G:`; la nube aún no está confirmada.
  - `CLOUD_CONFIRMED`: solo si hay `drive_id` real y el tamaño en la nube coincide (confirmación vía conector: `python -m automation.drive_sync --confirm-cloud archivo.json`).
- **Automático tras cada lote**: `multi_market_batch_runner.run_batch(...)` (parámetro `sync_label`, por defecto `V6_BATCH`) y `autonomous_lab.run_mt5_experiment` llaman a `drive_sync.sync_after_batch()` en un `finally`; si Drive no está disponible solo avisa y los archivos se sincronizan en la siguiente ejecución. Cualquier runner V6 debe usar `run_batch` o llamar a ese gancho.

## Comandos
```
python -m automation.drive_sync --label V6_LOTE_01     # sincroniza
python -m automation.drive_sync --dry                  # simula
python -m automation.drive_sync --verify               # relee copias y compara SHA-256
python -m automation.drive_sync --selftest             # archivo de verificación sin datos sensibles
python -m automation.drive_sync --confirm-cloud c.json # registra confirmaciones de nube
```

## Evidencia de la ejecución (2026-11-09)
| Comprobación | Resultado |
|---|---|
| Ruta `G:\Mi unidad\REMIX FOREX V1 — …` | existe, contiene 01–05 y los archivos subidos antes por el conector (misma carpeta que el ID raíz) |
| Sincronización V4+V5 pendientes | `SYNC_20261109T233941Z_V4_V5_PENDING`: 682 copiados, 124 excluidos (logs, extensiones no permitidas), 0 secretos, 0 fallos |
| Archivo de verificación | `SYNC_SELFTEST.txt` (79 B) → visible en la nube con ID `13e0xD-vnD1yg3OzOwZzd6fJHEaeylwrM`, tamaño idéntico |
| Integridad local | 683/683 copias con SHA-256 idéntico, 0 faltantes, 0 diferentes |
| Nube confirmada vía conector | 4 archivos (selftest, `EVENT_STUDY_RESULTS.csv`, dos `.set` de runs); el resto sigue `COPIED_LOCAL_PENDING_CLOUD` hasta confirmarlo |
| Pruebas | 131 pasan (6 nuevas en `tests/test_drive_sync.py`) |

Limitación: la confirmación de nube archivo por archivo cuesta contexto (cada búsqueda del conector devuelve metadatos); por eso solo se confirmó una muestra. Drive para escritorio sube en segundo plano; el estado del cliente no es consultable por script sin leer sus bases internas (que contienen datos de cuenta y no se tocan).

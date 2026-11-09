# Verificación del respaldo en Google Drive (V4)

Carpeta destino: `REMIX FOREX V1 — Adaptive Quantitative Trading System` (id `10iMMgFDjMbk1CYpyMvC4dxrdyz7cBj5P`). Estructura existente reutilizada: 01 Documentación (`1TqZ_mY589qK_E6EKl1jqSsHdcO-RGM7d`), 02 Código, 03 Datos, 04 Backtests y resultados (`1bhDJMGeJleKxqBbmrwO328bTDxGCjoaX`), 05 Informes y auditorías (`1Z-AplyTcSmEiGqUu09GSRD6Rtf4qIIkf`). No se creó ninguna carpeta nueva.

El mecanismo: `automation/drive_backup.py` mantiene `backup/DRIVE_UPLOAD_QUEUE.csv` (hash SHA-256, tamaño, carpeta) y solo pasa un archivo a `DRIVE_BACKUP_MANIFEST.csv` cuando se registra un ID real devuelto por Drive. La transferencia se hace con el conector de Drive de Claude Code (crea archivos nuevos con nombre único; no edita existentes). Estado real: ver `backup/DRIVE_BACKUP_STATUS.md`.

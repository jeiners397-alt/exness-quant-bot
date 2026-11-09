# Estado de respaldos — 2026-11-09 (UTC)

## Flujo: Claude Code → archivos locales → Google Drive → verificación
| Paso | Estado |
|---|---|
| Permisos de escritura en Drive | **Parcial.** Se pueden **crear archivos nuevos** (las carpetas del proyecto aceptan `create_file`; el archivo creado queda con `canEdit:true`). **No se pueden editar archivos existentes** (`canEdit:false`). Cada respaldo es un archivo nuevo con versión y fecha en el nombre |
| Límite técnico | `create_file` exige el contenido **en línea** (no admite ruta local). Subir un archivo de N KB obliga a reescribirlo en el contexto: inviable para código y CSV grandes dentro de un plan Pro |
| GitHub | **No configurado.** El directorio no es un repositorio git y el conector de GitHub no conectó. No se usó. Una copia local o en GitHub no se presenta como respaldo de Drive |
| Drive para escritorio | No instalado ni configurado (no autorizado). Sería el mecanismo adecuado para sincronizar carpetas completas sin pasar por el contexto |

## Respaldados en Drive y verificados (tamaño en bytes Drive == local; lectura comprobada en uno de ellos)
| Archivo (Drive) | Carpeta | ID | Bytes |
|---|---|---|---:|
| INFORME_SESION_2026-11-09_v1.0.md | 05_Informes y auditorías | 1Ztg-xG_58v-i5pmHvpVc-17RBbDCNtmC | 4 877 |
| PRIORITY_HYPOTHESES_v1.0_2026-11-09.md | 01_Documentación y planificación | 1Ia-Ig46jAo395b0rb3z2SWZ7jMYDbAcN | 5 633 |
| DEDUP_AND_PROVENANCE_v1.0_2026-11-09.md | 01_Documentación y planificación | 1iqfbs6fVYMT_DKe82bZ9MXMKaYEbXixd | 5 826 |

El hash SHA-256 del archivo en Drive **no** está disponible a través del conector; la integridad se verificó por tamaño idéntico en bytes. Los hashes locales están en `BACKUP_QUEUE.csv`.

Archivo de prueba creado por Claude (puede borrarse): `_CLAUDE_WRITE_TEST_2026-11-09.txt` (05_Informes y auditorías, id 1-YSNLqY8iftjh33dVBP6hdXFKQWqjqFY).

## Actualización Fases 1–5 (2026-11-09)
- Cola regenerada: 260 artefactos = 4 UPLOADED_VERIFIED (3 documentos + el informe original del Tester subido por el usuario, mismo tamaño 172.377 B; hash no comparable), 97 PENDING, 159 PENDING_DATASET_GRANDE (datos/ticks bajo `data/raw/`: solo hash; no se suben).
- Nada nuevo se ha subido a Drive en esta fase: **no hay respaldo en Drive de código, resultados ni informes de las Fases 1–5** hasta que se sincronice con Drive para escritorio (excluir `data/raw/`, `.claude/`, `.mcp.json*`).
- No se usó ningún método alternativo (ni GitHub ni subida masiva por el conector).

## Actualización Fase D (2026-11-09)
- Cola regenerada: 285 artefactos = 4 UPLOADED_VERIFIED (sin cambios), 120 PENDING (incluye `docs/REMIX_EURUSD_PHASE_D_REPORT.md`, `research/PHASE_D_*.csv`, `PROSPECTIVE_FREEZE_2026-11-09.json`, código y pruebas nuevos), 161 PENDING_DATASET_GRANDE (datos/ticks/historia pre-2025 bajo `data/raw/`: solo hash).
- **No se subió nada de la Fase D a Drive** (el conector solo crea archivos con contenido inline; sincronización con Drive para escritorio pendiente). No se declara respaldo.
- Hash del pre-registro prospectivo: ver `research/PROSPECTIVE_FREEZE_2026-11-09.json` (SHA-256 en `BACKUP_QUEUE.csv`); su integridad depende de no modificarlo.

## Actualización Fase E / V2 (2026-11-09)
- **GitHub (no es respaldo en Drive):** rama `remix-eurusd-v2` del repositorio público `jeiners397-alt/exness-quant-bot`, commit `3ef3a6a` (sobre `89c2920`); rama base `remix-eurusd-v2-base` (=89c2920) para el pull request. `main` (d82ab95) y `remix-forex-v1-fase0` (91fdef8) intactas. Auditoría de secretos previa al commit: 0 hallazgos; excluidos datos pesados, ticks, `.xlsx`, `.ex5`, `.mcp*`, logs.
- **Drive:** sin cambios; nada de la Fase E subido. Cola: 318 artefactos (4 verificados, 152 pendientes, 162 datasets grandes solo hash).

## Pendientes (ver `BACKUP_QUEUE.csv`)
Todo lo demás: código Python/MQL5, pruebas, configuración, catálogos CSV, manifiesto, resultados y datos. Causa: límite del conector descrito arriba. Los datasets (`data/raw/*.csv`, ~20 MB) quedan como `PENDING_DATASET_GRANDE`: solo hash y manifiesto, sin subida automática.

## Excluido siempre
`.mcp.json*`, `.env`, `.claude/`, credenciales, tokens, informes del tester con datos de cuenta, cachés (`.gitignore`).

## Para completar los respaldos (decisión del usuario)
1. Instalar y configurar **Google Drive para escritorio** y sincronizar `REMIX_FOREX_V1/` (excluyendo `data/raw/`, `.claude/`, `.mcp.json*`); o
2. Autorizar la subida de los archivos pendientes a través del conector (coste de contexto elevado), empezando por `research/*.csv`; o
3. Configurar un repositorio GitHub privado con rama independiente `remix-lab` (sin tocar la rama principal ni el código Binance).

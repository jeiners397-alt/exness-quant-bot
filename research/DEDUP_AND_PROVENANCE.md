# REMIX FOREX V1 — Deduplicación y procedencia de catálogos
Versión 1.0 · 2026-11-09 UTC · generado con `research/tools/build_catalogs.py`, `dedup_pairs.py`, `build_manifest.py`

## 1. Conteos confirmados contra los archivos originales

| Fuente | Estrategias/hipótesis | Indicadores | Cómo se verificó |
|---|---:|---:|---|
| A · REMIX (matriz XLSX) | 100 | 100 | Parser sobre la lectura del conector; N° 1–100 contiguos, 9 columnas en las 200 filas |
| B · REVERSE EDGE Z24 (`ESTADO_*` v. 21:01) | 100 | 200 | Lectura completa; IDs 1–100 y 1–200 |
| C · SPOT EDGE S1 (JSON) | 200 | 200 | JSON de estrategias parseado: 200/200; indicadores leídos completos |
| C · extras | 36 | — | `03_EXTRAS_36_HIPOTESIS.csv` leído completo |
| C · web | 12 | — | `04_NUEVAS_12_WEB.csv` leído completo |
| **Total (sin deduplicar)** | **448** | **500** | coincide con la auditoría previa |
| LAB (S01–S04, especificación del usuario) | 4 (aparte) | — | no pertenecen a ninguna fuente |

La suma 448/500 **no** es número de ideas independientes. Tampoco indica rentabilidad: ningún winrate, rendimiento ni *ranking* de las fuentes se importó como evidencia.

## 2. Dos niveles de deduplicación (ambos basados en nombre/definición declarada, no en prueba matemática)

**Nivel 1 — Familia (`concept_group`).** Reglas regex revisables agrupan por concepto (p. ej. `DONCHIAN_BREAKOUT`, `SQUEEZE_BREAKOUT`). Resultado: **152 familias** de estrategias y **185 familias** de indicadores. Es una agrupación gruesa: `OSC_ZERO_CROSS` reúne 79 estrategias distintas de cruces de osciladores y **no son duplicados** entre sí.

**Nivel 2 — Candidatos a duplicado (`DUP_CANDIDATES_*.csv`).** Pares de fuentes distintas con nombre normalizado idéntico o similitud ≥ 0,82:
- Estrategias: 57 pares (23 con nombre normalizado idéntico), 99 entradas implicadas, 43 clústeres (33 de 2, 9 de 3, 1 de 6).
- Indicadores: 128 pares (89 idénticos), 193 entradas implicadas, 82 clústeres.
- Cota optimista: **≥ 392 estrategias y ≥ 389 indicadores** tras fusionar esos clústeres. No incluye duplicados internos de una misma fuente ni variantes con nombre muy distinto.

**Conclusión honesta:** el número de estrategias matemáticamente independientes está entre ~150 (familias) y ~390 (nombres), y no se puede fijar sin comparar reglas una a una. Los 43+82 clústeres quedan en `decision = PENDIENTE_REVISION_MATEMATICA`.

Única equivalencia matemática reconocida: **SMMA ≡ media suavizada de Wilder (RMA)** (`SMMA_RMA_WILDER`, 2+ entradas). Se marca `EQUIV_MATEMATICA_CONOCIDA`.

## 3. Procedencia y problemas detectados

1. **Tres versiones de `ESTADO_ESTRATEGIAS_100` y `ESTADO_INDICADORES_200`** en tres carpetas, con tamaños distintos (20 362/20 544/20 645 B y 32 352/33 539/33 740 B): hay deriva entre versiones. Se usó la más reciente (21:01 del 2026-11-06). No se diferenciaron las otras dos.
2. **Defecto de datos en `ESTADO_INDICADORES_200`**: la columna `funcion_ta_opcional` está desplazada entre las filas 54 y 70 (p. ej. *Connors RSI → macd*, *PPO → connors*, *TSI → ppo*, *Klinger → smi*). Esa columna no se usa.
3. **Fuente A ≠ Fuente B**: los dos «100 estrategias» son listas distintas (A: order flow, gamma/opciones, SMC/ICT, cuantitativa, price action; B: *scalping/indicadores* con estimaciones de winrate). Solapan en conceptos, no en identidad.
4. **Entradas de azar/riesgo incluidas por diseño** en B (91–100) y C (≈ 183–200). Se marcan `CONTROL_NEGATIVO_O_RIESGO_INCOMPATIBLE`; el criterio para C es «máximo de winrate estimado ≤ 30 %», usado solo para señalar candidatos a control, no como evidencia.
5. **Fuente C y extras son *Binance Spot*, típicamente LONG-only**: 248 de las 448 entradas requieren rediseño antes de operarse SHORT en CFD (`long_only_spot_redesign_needed = 1`). Se conservan, no se descartan.
6. **Fuente D (Exness)**: ver §4.

## 4. Fuente D — datos Exness (`Bot_Trading_Binance_Data/Exness data`)

| Archivo | Hallazgo |
|---|---|
| `exness_mt5_extractor.log` (leído completo) | Extracción 2026-10-18 desde **este mismo terminal y cuenta demo** (build 6249, `maxbars=100000`). 11 símbolos con sufijo `m`: BTC, ETH, SOL, XRP, XAU, XAG, US30, USTEC, EUR, GBP, JPY. M1/M5/H1/H4, ≈ 100 mil filas máx. por serie |
| `exness_institutional_v1.db` (536 MB) | **No descargado ni inspeccionado**: el conector no expone esquema y es `octet-stream`. Por el log, es un volcado OHLC de MT5 más etiquetas BUY/SELL/HOLD **derivadas de indicadores** (no operaciones reales) |
| `exness_news_events.csv` | Solo la cabecera (`datetime_utc,event,impact,currency`): **0 eventos**. No es calendario de noticias |

Implicaciones: (a) la base no aporta histórico de EURUSD/XAUUSD más largo que el que ya se extrae con Python; (b) el límite `maxbars=100000` explica que el M5 local empiece a mediados de 2025; (c) los módulos de noticias no tienen datos.
**Recomendación:** no descargar la base; si se necesita, volver a extraer desde MT5 y registrar el hash.

## 5. Archivos de este informe
`SOURCE_MANIFEST.csv` · `CATALOG_STRATEGIES.csv` · `CATALOG_INDICATORS.csv` · `EXNESS_COMPATIBILITY_MATRIX.csv` · `DUP_CANDIDATES_strategies.csv` · `DUP_CANDIDATES_indicators.csv` · `build_stats.json` · `dup_stats.json`

## 6. Límites de esta clasificación
- La clase de compatibilidad es una **heurística por reglas** (palabras clave + estado de la fuente), no una revisión estrategia por estrategia. Debe tratarse como borrador auditable.
- Quedan sin leer: `FUENTE_ORIGINAL_*` (B), `LISTA_ORIGINAL_*` (C), rankings, protocolos, código Binance y 7 ZIP. Subcarpetas Z24/Z25/Z25B/Z1/COLAB sin enumerar.
- Los IDs de Drive del manifiesto se copiaron de los listados del conector; deben verificarse antes de automatizar enlaces.

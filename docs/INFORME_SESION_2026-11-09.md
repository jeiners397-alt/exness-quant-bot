# REMIX FOREX V1 — Informe de sesión 2026-11-09 (UTC)

## A. Auditoría de Google Drive
- **Acceso:** lectura OK en toda la carpeta REMIX y en las carpetas de Binance/Exness. **Escritura OK solo para archivos nuevos** (prueba: `_CLAUDE_WRITE_TEST_2026-11-09.txt`, `canEdit:true` en el archivo creado; las carpetas siguen con `canEdit:false`). No se puede editar un archivo existente: cada respaldo es un archivo nuevo versionado.
- **Inventario:** `research/SOURCE_MANIFEST.csv` (84 filas): 11 leídas completas, 39 solo metadatos, 7 ZIP no procesables, 1 base de 536 MB no descargada, 16 carpetas sin enumerar.
- **Leídos completos:** auditoría del 09-nov, matriz REMIX (XLSX), JSON de 200 estrategias y 200 indicadores (C), `ESTADO_ESTRATEGIAS_100` y `ESTADO_INDICADORES_200` (B, versión más reciente), extras 36, web 12, log del extractor Exness, CSV de noticias.
- **Pendientes de inspección:** las 8 especificaciones `.md`, `INFORME_DISENO_Y_RESEARCH_V1`, `FUENTE_ORIGINAL_*` (B), `LISTA_ORIGINAL_*` (C), rankings, protocolos Binance, código Binance (`analizar_atr_costes.py`, `backtest_engine.py`), cuadernos Colab, 7 ZIP, subcarpetas Z24/Z25/Z25B/Z1/COLAB, y la base `.db`.

## B. Catálogo consolidado
| | Estrategias | Indicadores |
|---|---:|---:|
| Entradas brutas (A+B+C+extras+web) | **448** | **500** |
| Familias conceptuales | 152 | 185 |
| Cota de únicos tras fusionar nombres idénticos/similares | ≥ 392 | ≥ 389 |
| Clústeres de duplicados candidatos | 43 | 82 |

Compatibilidad Exness (estrategias; heurística de reglas, borrador):

| Clase | n |
|---|---:|
| Implementable con datos MT5 | 254 |
| Implementable con condiciones | 101 |
| Requiere datos externos | 50 |
| Control negativo / riesgo incompatible | 26 |
| No evaluable actualmente | 17 |

248 de 448 proceden de Binance Spot (LONG-only) y requieren rediseño para CFD. Detalle y límites: `research/DEDUP_AND_PROVENANCE.md`.

## C. Hipótesis prioritarias
16 hipótesis (12 de señal + meta-prueba de régimen + 3 controles), justificadas por viabilidad, no por promesas de rentabilidad: `research/PRIORITY_HYPOTHESES.md`. Order flow, gamma, funding/OI y noticias se mantienen aparte por falta de datos.

## D. Estado del laboratorio (comprobado en esta sesión)
- Python 3.14.8, MetaTrader5 5.0.6231, numpy 2.5.3, pandas 2.3.3. **18/18 pruebas unitarias OK** (re-ejecutadas hoy).
- EA `REMIX_STRATEGY_RESEARCH_LAB_V1.mq5`: compilado, **0 errores, 0 avisos**; hash SHA-256 del `.mq5` local = desplegado.
- Conexión MT5: cuenta **DEMO** Exness-MT5Trial11 (comprobado `trade_mode = DEMO` antes de cualquier descarga).
- Datos (EURUSDm/XAUUSDm): M15 y H1 desde 2025-01-01; **M5 desde 2025-07-07 (EUR) y 2025-06-12 (XAU)** por el límite `maxbars=100000` del terminal. Sin duplicados, OHLC inválidos ni NaN; sin huecos > 4 días.
- Limitaciones: ADX Wilder (Python) vs `iADX` (MT5) sin verificar paridad; comisión de la cuenta no verificada (0 por defecto); swap modelado solo en modo puntos; DD solo sobre operaciones cerradas; spread de barra ≠ spread de tick.

## E. Primer backtest
**Python (S01, EURUSDm, M15, 2025-01-01→2025-03-31, solo en muestra, parámetros por defecto no optimizados):**

| Política de lote | Operaciones | Riesgo real medio | PF | Exp. (R) | Neto (USD) | DD máx. | Costes |
|---|---:|---:|---:|---:|---:|---:|---:|
| `strict` (política pedida) | **0** (49 señales rechazadas: lote mínimo excede el riesgo) | — | — | — | 0 | — | — |
| `min_lot` (solo diagnóstico) | 49 | 2,69 % | 1,09 | +0,058 | +5,13 | 22,8 % | 4,41 |
| `ideal` (lote teórico, no ejecutable) | 49 | 0,50 % | 1,11 | +0,058 | +1,34 | 3,8 % | 0,97 |

Con 49 operaciones y +0,058 R, **no hay evidencia de ventaja**; es una validación técnica del simulador, no una prueba de rentabilidad.

**Strategy Tester (T001, ticks reales, política estricta): NO EJECUTADO.** Se generó el INI y se lanzó `terminal64.exe /config:…` con `ShutdownTerminal=0`. El terminal ya abierto (PID 34572) ignoró la segunda instancia: sin informe ni rastro en los logs. El terminal **no se cerró ni se tocó**. Opciones en §G.

## F. Respaldos
Ver `backup/BACKUP_STATUS.md` y `backup/BACKUP_QUEUE.csv`. Los respaldos en Drive solo cuentan los verificados; el resto está en cola con motivo.

## G. Próximos pasos
1. **Desbloquear el Tester** (necesita su decisión; ver opciones en la conversación).
2. Paridad Python↔MT5 de S01 (comparar listas de operaciones) con una prueba técnica etiquetada.
3. Controles (aleatorio, MACD, SMA 5/20) y S01–S04 por defecto, solo en muestra; después rejilla acotada → walk-forward → congelar → **una** evaluación del holdout.
4. Leer las 8 especificaciones y `FUENTE_ORIGINAL_*`/`LISTA_ORIGINAL_*` para contrastar el catálogo.
5. Decidir sobre el capital: con 100 USD el lote mínimo bloquea casi toda la operativa de SL > 5 pips.

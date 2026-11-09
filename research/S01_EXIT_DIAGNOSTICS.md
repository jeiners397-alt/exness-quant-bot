# S01 — Diagnóstico de pérdidas y salidas (Fase C, 2026-11-09)

Fuentes verificadas: export de deals del EA (`results/s01_official/REMIX_deals_S01_EURUSDm_PERIOD_M15.csv`, SHA-256 B5DB2514…F48C, 670 deals) e informe oficial `ReportTester-ACCOUNTID.xlsx` (SHA-256 397280368…D504, copia en `results/s01_official/`). Scripts: `research/s01_audit.py`, `s01_mae_mfe.py`, `run_exit_variants.py`, `remix_lab/exit_variants.py`.
Todo el periodo ene-2025→oct-2026 ya fue observado: es **exploratorio, no OOS**. Hipótesis probadas en esta fase sobre S01: 10 variantes de salida (+V0). No se ha seleccionado ningún parámetro.

## 1. Los 117 cierres «sin etiqueta» sí son cierres horarios (verificado)
- Código del EA (`OnTick`): primera barra con hora ≥ `S01_ExitH`(17) → `ClosePosition()`.
- Los 117 cierres tienen comentario vacío y hora de cierre 17:00:00–17:00:06 (todos). Ningún cierre SL/TP ocurre a ≥17 h. Comisión, swap y fee: 0,00 en los 670 deals (el modelo del Tester no los cargó; **no demuestra que la cuenta real no los tenga**).

## 2. Por qué TP+SL pierde y el conjunto gana
| Salida | N | Ganadoras | PnL USD | R medio |
|---|---:|---:|---:|---:|
| TP | 82 | 82 | +1.758,57 | +1,517 |
| SL | 136 | 0 | −1.932,48 | −1,005 |
| Horaria | 117 | 72 (61,5 %) | +314,41 | +0,189 |

- Entre las que llegan a TP o SL, P(TP)=82/218=**37,6 %**; con RR 1,5 el punto de equilibrio es **40 %** → TP+SL = −173,91 USD (≈ −0,08 R por operación).
- Las horarias (35 % de las operaciones) son operaciones que **no tocaron ni −1R ni +1,5R**: son las supervivientes; su media positiva (+0,19 R) es la deriva del precio a favor de la ruptura. Condicional a haber sobrevivido, no es una ventaja demostrable independiente.
- Validación de la reconstrucción en R: SL mediana −1,000 (p5–p95: −1,013…−1,000), TP mediana +1,502. El riesgo real por operación fue 0,275–0,500 % (mediana 0,465 %; redondeo del lote hacia abajo); 6 operaciones con lote mínimo 0,01.

## 3. Significancia (¿hay ventaja?)
Expectativa +0,0294 R/operación, desviación 1,044 R, **t = 0,52**; IC95 bootstrap por bloques de 10: **[−0,093 ; +0,142] R**. El cero está dentro del intervalo. Sin las 5 mejores operaciones el neto es +11,21 USD; la mejor operación aporta solo 1,5 % del beneficio bruto (no depende de un valor extremo, pero tampoco de una ventaja demostrada). PF 1,065 con N=335 no distingue de 1.

## 4. LONG vs SHORT y periodos
| | N | Win% | PnL | PF | R medio |
|---|---:|---:|---:|---:|---:|
| LONG | 166 | 47,6 | +144,17 | 1,147 | +0,059 |
| SHORT | 169 | 44,4 | −3,67 | 0,997 | +0,001 |

Diferencia no significativa con esta muestra. Por trimestre: 2025Q4 −202,65 USD (PF 0,53; win 31,9 %) y 2026Q1 −101,53 (PF 0,69); el resto de trimestres es positivo (PF 1,14–1,70). En 2025Q4+2026Q1: 92 operaciones, R medio −0,24; **SHORT −0,31 R (win 33 %)** y LONG −0,14 R; con P(TP|TP o SL)=16/67=24 % frente a 66/151=44 % en el resto. Es dependencia de periodo/régimen: no hay muestra para atribuirlo a un factor concreto.
Por amplitud del rango asiático (cuartiles; bordes en `S01_AUDIT_STATS.json`): R medio −0,014 (estrecho) → +0,082 (ancho). Tendencia monótona pero pequeña; no es un filtro validado.

## 5. Calidad de datos (hallazgo importante)
- El terminal solo devuelve ticks desde **2026-01-01 22:05**; para todas las muestras de 2025 `copy_ticks_range` devuelve 0 (`research/TICK_PROBE.csv`). Esto coincide con «45 % ticks reales» (≈10 de 22 meses): **2025 se simuló con ticks generados a partir de barras**, 2026 con ticks reales.
- En los ticks reales de 2026 (07–10 h, 261.632 ticks) el spread es **exactamente 8 puntos en el percentil 1, 50, 99 y máximo**: el feed de Exness en cuenta demo parece cotizar spread fijo en ese tramo, o el histórico está normalizado. No se puede afirmar que el spread real de ejecución sea constante. En barras 2025 el spread mediano es 9 puntos. No hay ticks cruzados (ask<bid = 0).
- Lagunas: máximo entre ticks 84–392 s en días de muestra (periodos asiáticos/baja liquidez).
- Costes: comisión y swap cero en el reporte; slippage no modelado (Tester: sin latencia). El efecto de 10 puntos de slippage en stops se ha medido en barras (§7).
- Beneficio en pips deshabilitado: no verificable desde este informe; el cálculo de R se hizo con `lotes × 100000 × distancia` (EURUSD, contrato 100.000 verificado en `symbol_specs.json`), y reproduce SL=−1,00 R.

## 6. MAE/MFE (`S01_MAE_MFE_ANALYSIS.csv`)
- 153 operaciones con **ticks reales** (Bid/Ask, secuencia exacta, con tiempos a MFE/MAE) y 182 de 2025 con **cota por barras M15** (`method=BAR_BOUND`: extremos de barra, sin orden intrabarra ni tiempos).
- Operaciones SL (136): MFE ≥0,25 R en 49 %, ≥0,5 R en 24 %, ≥0,75 R en 14 %, ≥1,0 R en 7 % (9). Con ticks reales (59 SL): 47 %, 25 %, 17 %, 8 %. Mediana de MFE de las perdedoras: 0,23 R.
- TP: MAE mediano 0,27–0,29 R. Horarias: MFE mediano 0,69–0,79 R, MAE 0,54–0,59 R.
- Sí existe un subconjunto de pérdidas que primero avanzó (24 % superó 0,5 R), pero esto **no implica que un trailing lo habría evitado**: se simuló cronológicamente (§7) y no mejoró.

## 7. Variantes de salida (entradas fijas = las 335 oficiales; barras M15, orden conservador)
Paridad V0 (Fase A): **335/335 motivos de cierre coinciden con MT5**; ΣR 9,12 vs 9,86 oficial; diferencia mediana por operación 0,000 R; |media| 0,002 R.

| Var. | Descripción | Exp R | ΔR vs V0 | IC95 Δ (bloques) | Δ 2025 / 2026 |
|---|---|---:|---:|---|---|
| V0 | original | +0,027 | — | — | — |
| V1a | BE a +0,5R | −0,051 | −0,078 | [−0,136 ; −0,011] | −0,071 / −0,086 |
| V1b | BE a +1,0R | +0,015 | −0,012 | [−0,037 ; +0,016] | −0,024 / +0,002 |
| V2a | trail ATR×1,5 (act. +1R) | −0,011 | −0,038 | [−0,082 ; +0,006] | −0,053 / −0,020 |
| V2b | trail ATR×2,5 | +0,007 | −0,020 | [−0,054 ; +0,018] | −0,028 / −0,011 |
| V3 | trail estructural 4 barras | +0,014 | −0,013 | [−0,049 ; +0,026] | −0,025 / +0,001 |
| V4a | cierre 13 h | +0,007 | −0,021 | [−0,091 ; +0,044] | +0,025 / −0,075 |
| V4b | cierre 15 h | +0,014 | −0,013 | [−0,044 ; +0,017] | 0,000 / −0,028 |
| V4c | duración máx. 4 h | −0,050 | −0,077 | [−0,157 ; −0,007] | −0,034 / −0,128 |
| V4d | sin continuación a 1,5 h | +0,038 | +0,011 | [−0,046 ; +0,060] | +0,047 / −0,032 |
| V5 | parcial 50 % a +1R (lotes ≥0,02) | +0,020 | −0,007 | [−0,029 ; +0,015] | −0,013 / −0,001 |

**Conclusión: ninguna variante mejora a V0 de forma significativa** (con 10 comparaciones, α de Bonferroni=0,005). V1a y V4c empeoran con IC que excluye 0. V4d (+0,011) es indistinguible de ruido y cambia de signo entre 2025 y 2026. Con slippage de 10 puntos en stops, V0 baja a +0,007 R y V4d a +0,027 R.
Limitación: en barras M15 el BE/trailing solo actúa desde la barra siguiente y el SL se evalúa primero (sesgo en contra de BE/trailing). Habría que repetir con ticks reales las 153 operaciones de 2026 antes de descartarlos definitivamente; con 2025 sin ticks no se puede hacer mejor que la cota por barras.

## 8. Qué NO se ha hecho todavía
Repetición con ticks de las variantes (2026), comparación Python–MT5 de la señal (entradas/hora/precio) con el Tester, regímenes, S02–S04 en MT5, controles aleatorios, walk-forward, PBO/DSR. Ver `docs/INFORME_FASE_C_2026-11-09.md`.

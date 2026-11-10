# V8 — Informe de validación

## Regla de promoción aplicada (fijada antes de ver resultados)
HTF (muestras pequeñas): candidata si n_IS≥30, expectativa IS>0 y t_IS≥2; confirmada en OOS (n≥15, expectativa>0, t≥1,65). **Clase B** exige además t_IS ≥ √(2 ln N), expectativa a coste ×1,5 > 0 e IC95 OOS que excluya 0. **Clase A** exige evidencia independiente: **no asignable**, porque todo el periodo 2024-01→2026-10 se vio en V4/V5/V7 y la reserva (≥ 2026-11-01) contiene hoy ≈ 9 días.

## Multiplicidad
| Conjunto | N pruebas | t* = √(2 ln N) |
|---|---|---|
| V7 (M15 + H1) | 2.200 | 3,92 |
| V8 lote B (H4/D1) | 890 | 3,69 |
| V8 sensibilidad (54) + entradas/salidas (30) | 84 | — |
| **Acumulado V7+V8** | **3.174** | **4,02** |

## Clases (lote B, 890 pruebas): D 466 · F 270 · C 151 · G 3 · **B 0 · A 0**
Mejor t_all entre mercados con n suficiente: XAUUSDm H4 `D_EXTREME_REVERSION` invertido t=3,33 (débil en 2026) y D1 `B_MOMENTUM` t=3,06 (n=63); H4 `A1_BREAKOUT20` t=2,88. **Ninguna alcanza 3,69 (ni 4,02 acumulado).** Se esperan ≈ 22 pruebas con t>1,96 unilateral por azar entre 890 (hay 37, la mitad en un único mercado: lo que sugiere un efecto específico del oro en el periodo, no descartable como régimen).

## Pista principal: XAUUSDm H4 `A1_BREAKOUT20` (clase C)
| Evidencia | Resultado |
|---|---|
| Reproducción oficial (MT5, 98 % calidad) | TP 2R: +1.622,79 USD, PF 1,49; TP 3R: +2.172,77, PF 1,57; DD 8,1–8,4 % |
| IS / OOS (R por operación, ejecuciones oficiales) | TP 2R: +0,160 (n 131) / +0,267 (n 117); TP 3R: +0,199 / +0,408 |
| Por año (TP 2R) | 2024 +0,15 · 2025 +0,18 · 2026 +0,33 R (las tres positivas) |
| Bootstrap por bloques (L=8, 5.000) | TP 2R IC95 [+0,04, +0,40]; TP 3R [+0,05, +0,55] — **sin corregir por selección** |
| Quitar las 5 mejores operaciones | +0,17 R (2R); +0,24 R (3R): no depende de outliers |
| Sensibilidad (ventana 10–55, SL 0,75–1,5 ATR, RR 1,5–3) | 54/54 celdas con expectativa >0; la referencia prefijada no es la óptima |
| Costes ×2 (modelado) | PF 1,47 (2R), 1,55 (3R) |
| Control aleatorio con igual mezcla direccional | p = 0,04 (no excluye una parte del efecto por la tendencia alcista del oro) |
| Otros mercados con la misma regla (EURUSD, USTEC, BTC, ETH) | sin candidatas con muestra suficiente: el efecto es específico de XAUUSD en esta muestra |
| Salidas alternativas | ninguna mejora que sobreviva al OOS; la mejor-por-IS colapsa (+0,34 → +0,05 R) |
| Ticks reales | cobertura 9 %: **no validado** |

**Por qué sigue siendo clase C y no B:** (1) t_all=2,6–2,9 < 3,69/4,02 tras 3.174 pruebas; (2) el periodo del backtest es el periodo de selección, el OOS 2025-07→2026-10 se había visto; (3) mercado único y régimen alcista de fuerte tendencia del oro; (4) 2026 aporta la mayor parte del beneficio; (5) sin ticks reales. Las dos filas TP 2R/3R y las reglas H1/H4 comparten el mismo mercado y periodo: no son evidencia independiente entre sí.

## XAUUSDm H1 (hipótesis V7)
Reproducida con paridad 97,8 %. PF 1,17 (1,5R) y 1,31 (3R). La variante de 1,5R pierde en 2026 (−92 USD) y gana en 2025 (+477): inestable. Clase C sin cambios.

## Ticks reales (Fase 9)
El probador cargó ticks reales solo para el 9 % del historial del símbolo (el resto es sintético). La sonda de lectura de ticks del bróker (`copy_ticks_range`, muestras de 1 h por mes) **no devolvió datos en más de 10 min** y se abortó: estado `ERROR_DATOS` en `V8_TICK_AVAILABILITY.csv`; no hay caché local de ticks. **No se sustituyó por ninguna fuente externa y no se presenta validación con ticks reales.**

## Reserva prospectiva
Los parámetros de la pista H4 quedan **congelados**: variante `VARIANT_B_CLOSE_OUT`, `Lookback=20`, `CooldownBars=6`, `SL_ATR=1,0`, `RR∈{2;3}`, `MaxHoldBars=40`, lote 0,01, XAUUSDm H4. Los datos ≥ 2026-11-01 no se han usado para desarrollar reglas y solo servirán para evaluar esta definición exacta. Con ≈ 0,33 operaciones por día de negociación harían falta ≈ 6 meses (≥ 100 operaciones) para una potencia razonable; cualquier lectura anterior es evidencia preliminar.


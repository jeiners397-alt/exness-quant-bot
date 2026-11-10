# V9 — Informe de validación

## Protocolo (fijado antes de ver resultados)
DEV 2024-01-01→2024-12-31 · SEL 2025-01-01→2025-12-31 · VAL 2026-01-01→2026-10-31 (una sola evaluación por candidata congelada) · reserva prospectiva ≥ 2026-11-01 (no usada). Candidata: expectativa DEV > 0, t_DEV ≥ 2, n_DEV ≥ 200; confirmación SEL: expectativa > 0, t ≥ 1,65, n ≥ 200. B: además t_DEV ≥ √(2 ln N), coste ×1,5 positivo e IC95 SEL que excluya 0. A: B + VAL positiva (t ≥ 2, n ≥ 100). F: n < 200. Control: entradas aleatorias de igual hora y tercil de ER.

## Multiplicidad
| Conjunto | N | t* |
|---|---|---|
| V9 estudio de eventos (4 mercados) | 500 | 3,53 |
| V9 total (+ políticas de cesta/cobertura y modos de entrada) | 545 | — |
| **Acumulado V7+V8+V9** | **3.719** | **4,05** |

## Resultado: 0 candidatas A/B; C: 1; D/F: el resto
Mejor t_DEV entre todas las pruebas con n ≥ 200: 0,47 (G_SESSION_ORB M5 TP 3R, DEV +0,03 R / SEL +0,07 R / **VAL −0,11 R**). Ninguna regla de scalping tiene retorno bruto distinguible de 0 (−0,015…+0,014 R), ni siquiera antes de costes.

## Walk-forward, bootstrap, Monte Carlo
Sin candidata no hay nada que remuestrear. La partición DEV→SEL→VAL es el walk-forward efectivo (con cortes anuales). Para la línea A se mantienen los resultados de V8 (bootstrap por bloques y Monte Carlo en `V8_*`); no se repiten con parámetros distintos.

## Paridad Python ↔ MT5 (lecciones de V8 aplicadas)
- Horarios: servidor = UTC, comprobado; las velas M1/M5 del terminal coinciden con las del Python (mismo origen).
- Bid/Ask en stops: cortos activados por ASK; la paridad M5 (7.346 señales Python / 7.237 operaciones MT5, 97,2 % coincidentes, dirección 100 %, salidas 95,5 %) lo refleja en una diferencia de −0,016 R por operación (−0,091 Python vs −0,075 MT5 en dinero).
- Mercado cerrado: 195+12 señales no ejecutables a las 22–23 UTC (Python no las excluye).
- Velas parciales: no aplican en M1/M5 (se usan todas las barras como MT5).
- Cooldown: la importación de módulos fijaba un enfriamiento distinto (10 vs 6) y cambió la baseline H4 del simulador de cestas (196 vs 246 señales). Detectado por la discrepancia con V8, corregido y cubierto por un test.

## Ticks reales
Sonda segmentada (12 muestras de 5 min, límite de 100 s por muestra): ticks reales solo en las 3 muestras más recientes (≈ desde 2026-05; íntegras: 0 bid/ask inválidos; 7–18 marcas de tiempo repetidas por muestra = varios ticks en el mismo ms; huecos máx. 1,4 s); las 9 anteriores `ERROR_DATOS` (`V9_TICK_AVAILABILITY.csv`). Sin ticks reales no se puede declarar rentable un scalper intrabar; V9 no declara ninguno.

## Línea A
Sin cambios respecto a V8: clase C, retrospectiva, pendiente de reserva prospectiva. Hashes verificados.



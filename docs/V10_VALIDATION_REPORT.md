# V10 — Informe de validación

## Protocolo (fijado antes de ver resultados)
DEV 2024-01-01→2024-12-31 · SEL 2025 · VAL 2026-01-01→2026-10-31 · **reserva ≥ 2026-11-01 sin usar** (test automático: ningún dato OHLC, evento ni serie FRED llega a esa fecha). Controles aleatorios con semilla fija. Clase A solo con validación independiente (DEV, SEL y VAL coherentes, |t| ≥ t\* en global y VAL, n_VAL ≥ 100).

## Multiplicidad
| Conjunto | N | t\* |
|---|---|---|
| V10 | 86 | 2,98 |
| **Acumulado V7+V8+V9+V10** | **3.805** | **4,06** |

## Línea XAU H4 congelada (`V10_ROBUSTNESS_RESULTS.csv`)
| Prueba | Resultado |
|---|---|
| Bootstrap por bloques (8 op.) | IC95 expR [+0,065; +0,543] R; P(exp ≤ 0) = 0,006; IC95 PF [1,15; 2,09] |
| **Deflated Sharpe Ratio** (SR/op. 0,159; var(SR) entre pruebas H4/D1 de V8 = 0,0169) | N=1: 0,996 · **N=54: 0,010** · N=890: 0,000 · **N=3.719: 0,000** (SR₀ = 0,469 ≫ 0,159) |
| **PBO (CSCV, 54 configuraciones, S=8, 70 divisiones)** | **0,53**: la mejor configuración en la muestra queda por debajo de la mediana fuera de la muestra en más de la mitad de las divisiones |
| Costes ×0 / ×1 / ×2 / ×3 del spread | +2.221 / +2.173 / +2.125 / +2.077 USD (PF 1,59→1,54): insensible al spread |
| Swap ×2 | +2.039 USD (PF 1,53) |
| Sin las 1/3/5/10 mejores operaciones | +1.896 / +1.556 / +1.254 / **+601** (PF 1,50/1,41/1,33/**1,16**) |
| Sin el mejor mes / sin los 3 mejores | +1.512 / **+432** |
| Por tramo | DEV +0,28 R (t 1,41) · SEL +0,12 (t 0,64) · VAL +0,57 (t 2,38); DEV+SEL: +0,20 R (t 1,45), PF 1,28 |
| Tendencia 50 d | a favor +0,49 R (n 172, t 3,35) · en contra −0,08 R (n 60) |
| Retardo / latencia | **no evaluado** (el parámetro del probador no produce cambios comprobables) |
| Controles aleatorios (D, D-S, E1, E2) | p = 0,027 / 0,027 / 0,028 / 0,017 sin corrección; D-L p = 0,16 |

**Interpretación.** El IC por bloques excluye cero, pero ese IC no corrige por haber elegido esta definición entre ≥ 54 (y 3.719 acumuladas) candidatas: tras la deflación la probabilidad de que el SR verdadero supere el de la mejor de N pruebas por azar es ≈ 0. PBO 0,53 no permite descartar el sobreajuste. Los controles aleatorios dan p ≈ 0,02–0,03 en 5 contrastes (Bonferroni 0,01: no se cumple). **Clase C.**

## Paridad Python ↔ MT5 y modelo del probador
- H4: 98–99 % de señales (V8). **M15 (V10): 97,1 % de señales, 100 % de dirección, 98,2 % de salidas**; diferencias: 32 entradas de Python con mercado cerrado (retcode 10018) y 4 solo del EA.
- Modelo **OHLC 1 minuto**; calidad de historial 98 % de barras. Ticks reales: **solo ≈ desde 2026-05** (V9 los midió: 3 de 12 muestras); la validación completa con ticks reales **no es posible** con los datos disponibles y no se declara. Bid/Ask: los stops cortos se activan por ASK en MT5 (Python usa BID: diferencia conocida, ≈ 0,016 R).
- Horarios: servidor = UTC; las marcas de los anuncios macro comprobadas con el pico de volatilidad (horario de verano incluido).

## Hallazgo de integridad (clase E)
`trades.csv` de V8/V9 cruza horas de cierre de operaciones solapadas (43 de 248 en H4). Totales correctos; V10 usa el registro del EA. Los resultados de V8/V9 que dependían de fechas por operación (rentabilidad diaria por fecha de cierre) se recalcularon: la media diaria no cambia (0,070 %/día).

## Qué falta para una validación independiente
Evaluar la **definición exacta** congelada con datos ≥ 2026-11-01 (≈ 6 meses para ≈ 100 operaciones a 0,34/día). Cualquier hipótesis nueva de V10 (tendencia 50 d, VIX en alza, consolidación, M15 alineada con H4) se generó con datos ≤ 2026-10-31 y **contamina el histórico**: solo puede probarse prospectivamente y se registra como nueva generación.

# Paridad Python–MT5 de REMIX EURUSD V2 / L2 (S05 H4) — informe de diferencias

Fuentes: auditoría de ChatGPT (issue #1 de `jeiners397-alt/exness-quant-bot`), export oficial del Strategy Tester del usuario (`results/v2_official/REMIX_V2_deals_M05_EURUSDm_PERIOD_H4.csv`, log de señales del EA y reporte `.xlsx`), y diario del Tester (`Agent-…\logs`). Cuenta demo, EURUSDm, H4, 2025-01-01→2026-11-01, 3.000 USD, 0,5 %, política estricta, parámetros L2 sin tocar. Solo simulación.

## 1. Resultado
| Paso (acumulativo) | Op. Python | Op. MT5 | Entradas coincidentes | Solo Python | Solo MT5 | Primera divergencia | Neto Python | Swap Python |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| 0 Estado de la auditoría (serie recortada a 2025, sin compuertas, ADX Wilder) | 48 | 30 | **19** | 29 | 11 | 2025-01-02 00:00 | +82,15 | −8,85 |
| 1 + calentamiento previo a 2025 | 50 | 30 | 20 | 30 | 10 | 2025-01-01 20:00 | +96,48 | −9,41 |
| 2 + compuertas de spread (0,15×SL y 30 pts) en la barra de entrada | 50 | 30 | 20 | 30 | 10 | 2025-01-01 20:00 | +96,48 | −9,41 |
| 3 + ADX con la fórmula de MT5 | 27 | 30 | 25 | 2 | 5 | 2025-01-01 20:00 | +27,07 | −6,61 |
| 4 + reentrada en la barra de salida | 27 | 30 | 25 | 2 | 5 | 2025-01-01 20:00 | +27,07 | −6,61 |
| 5 + `max_bars` por tiempo calendario (comportamiento del EA V2) | 30 | 30 | 27 | 3 | 3 | 2025-01-01 20:00 | −35,37 | −5,94 |
| 6 + modelo de sesión (spread del primer tick y mercado cerrado) | 30 | 30 | **30** | **0** | **0** | ninguna | **−32,83** | −5,66 |

Oficial MT5: 30 operaciones, **−33,39 USD** (−27,74 movimientos, −5,65 swaps). (El «+83,55» de la auditoría usaba la regla de swap antigua; con el swap corregido el paso 0 da +82,15; mismas 48/19/29/11.)

Con el paso 6, sobre las **30 operaciones emparejadas**: dirección 30/30; precio de entrada idéntico 30/30; lotes 30/30; motivo de salida 30/30 (SL/TP/max_bars); barra H4 de salida 30/30; distancia SL y TP: diferencia mediana 0,3 pt; swap −5,66 vs −5,65 USD; neto −32,83 vs −33,39 USD (**diferencia +0,56 USD**, 1,7 %).

**Esto es paridad de operaciones y de resultado de la muestra oficial, no «paridad completa»:** el modelo de sesión (paso 6) es empírico y se apoya en 8 observaciones; la fórmula de ADX es la del indicador de referencia de MetaQuotes, no se ha comparado numéricamente con el `iADX` nativo (ver §4).

## 2. Errores encontrados y corregidos
| # | Error | Evidencia | Corrección | Efecto (entradas coincidentes) |
|---|---|---|---|---|
| A | Python no aplicaba las compuertas de spread del EA | `MaxSpreadFracSL`, `MaxSpreadPoints` en `OpenTrade`; 2 `SKIP_SPREAD` en el log MT5 | `BacktestConfig.max_spread_frac_sl/max_spread_points`, evaluadas en la **barra de entrada** con información de ese instante (contadores por motivo) | 0 por sí sola (el spread de las barras H4 es 8–9 pts): ver F |
| B | Calentamiento: Python recortaba a 2025 antes de calcular SMA50/ATR/ADX | primera señal MT5 el 2-ene; Python el 20-ene | Indicadores sobre histórico previo (H4 nativo desde 2022); solo se admiten entradas desde 2025-01-01 (la señal de la última barra previa sí puede entrar, como en el Tester) | 19 → 20 |
| C | **ADX distinto:** Python usaba Wilder (1/n, DM y TR suavizados por separado); el ADX de MetaQuotes suaviza los cocientes 100·DM/TR con **EMA α=2/(n+1)** | `MQL5\Indicators\Examples\ADX.mq5` y `MovingAverages.mqh::ExponentialMA` del propio terminal | `indicators.adx_mt5` (verificado con una implementación independiente; difiere materialmente de Wilder) | 20 → 25; 50 → 27 operaciones (23 operaciones «fantasma» de Python eran por el ADX) |
| D | **Bug del EA V2:** `S05_MaxBars` se medía como `(t − t_entrada)/período` (tiempo calendario), contando también las horas sin mercado | cierres adelantados 1–2 días tras fin de semana en el log | Python reproduce el comportamiento del V2 con `max_bars_mode="calendar"`; **V2.1 cuenta barras reales con `iBarShift`** (igual que la definición de L2) | 25 → 27 |
| E | Python re-entraba una barra tarde tras una salida a la apertura | `OnTick` cierra y evalúa en la misma barra | `reenter_after_open_exit` | 0 en esta muestra |
| F | **Reapertura de fin de semana:** el primer tick tiene spread muy ancho (40–116 pts; la barra H4 en `rates` dice 8–9) y en horario de verano el mercado está «cerrado» para operar hasta las 22:00 | log del EA: `SKIP_SPREAD` 54 y 68 pts; diario del Tester: 4/4 cierres a las 21:05 fallaron con `[Market closed]` (ret 10018) y se ejecutaron a las 00:00; los de las 22:05 funcionaron | `gate_spread` (spread de la primera barra M15 dentro de la H4) y `no_trade_at_open` (hueco de mercado con primer dato M15 antes de las 22:00) | 27 → 30 |
| G | **Swap:** Python no cobraba la noche del viernes | −0,11 USD (1 noche, 0,02 lotes) en operaciones viernes→lunes; jue→dom = 2 noches | `_swap_nights`: lun–vie 1×, mié 3×, sáb/dom 0 | swap −5,66 vs −5,65 (antes −5,94) |

El resultado oficial de MT5 no se ha modificado y los parámetros estratégicos de L2 no se han tocado.

## 3. Diferencias pendientes
1. **1 operación:** 2025-11-13 corto, `max_bars` en la reapertura del domingo: MT5 cerró a las 22:05 con spread de 70 pts; el proxy de Python (primera barra M15, 48 pts) da 22 pts menos de coste → −0,66 USD. Impacto total ≤ 0,56 USD en el neto.
2. **Ticks de 2025 generados:** las horas de salida SL/TP dentro de la barra difieren (precisión por tick vs por barra) sin efecto relevante en el precio (mediana 0 pts).
3. **Deslizamiento / relleno:** no modelado (el Tester no aplica latencia).
4. **Fórmula del `iADX` nativo:** asumida igual a la de referencia. El V2.1 exporta ADX/+DI/−DI por barra (`ExportBarDiag`) para comprobarlo vela a vela con `scripts/compare_bar_diag.py`. Hasta entonces, la equivalencia numérica del ADX es una inferencia respaldada por el emparejamiento 30/30, no una medida.
5. **Modelo de sesión** válido para EURUSDm/Exness según 8 eventos; no generalizable sin más datos.

## 4. Consecuencias para la investigación (importante)
La pista L2 se había identificado con el ADX de Wilder. Con el ADX que realmente ejecuta el EA (fórmula MT5), L2 con parámetros idénticos queda (`research/L2_ADX_IMPACT.csv`, barras H4, 3.000 USD, 0,5 %):

| ADX | Periodo | N | PF | Exp R | IC95 | p control |
|---|---|---:|---:|---:|---|---:|
| Wilder | 2018–2026 | 221 | 1,21 | +0,097 | [−0,04; +0,23] | 0,005 |
| MT5 | 2018–2021 | 46 | 1,00 | +0,007 | [−0,38; +0,45] | — |
| MT5 | 2022–2024 | 61 | 1,30 | +0,128 | [−0,09; +0,34] | — |
| MT5 | 2025–2026 | 28 | 1,25 | +0,113 | [−0,17; +0,38] | — |
| MT5 | 2018–2026 | 134 | 1,19 | +0,084 | [−0,09; +0,27] | 0,040 |

La consistencia entre periodos de L2 **empeora** con el ADX de MT5 (2018–21 ≈ 0). Sigue sin ventaja demostrada (IC con cero, t = 0,92 frente a t* de multiplicidad ≈ 3). La fila 2025–2026 de este cuadro (+36,78 USD, barras reales) y el resultado oficial del V2 (−33,39 USD) difieren sobre todo por el bug D: con `max_bars` en barras reales el mismo sistema da +27 USD (V2.1, esperado por Python).

## 5. Qué falta para declarar paridad completa
Ejecutar V2.1 (ver `docs/V2_1_TESTER_INSTRUCTIONS.md`) y comparar: (a) `REMIX_V21_bars_*.csv` con `compare_bar_diag.py` (ADX, ATR, SMA, z, señal, vela a vela); (b) `REMIX_V21_deals_*.csv` con `results/v2_1_expected/` (27 operaciones, +27,30 USD esperados por Python).

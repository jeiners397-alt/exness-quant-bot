# V8 — Auditoría de la hipótesis XAUUSDm H1 (Lote A)

## 1. Corrección de una descripción errónea de V7
Los informes V7 y la orden V8 describen la candidata como *"ruptura de las 96 velas previas con cierre fuera del nivel, entrada de continuación"*. **El código de V7 no hacía eso.** La definición real (`research/v7_event_study.py::ev_sweep_96`, variante `inverted`) es:

> Vela *i* cerrada: `high_i > max(high[i-96..i-1]) + 0,1·ATR` **y `close_i < ese máximo`** (pico que **cierra de vuelta dentro** del rango). V7 `primary` = reversión (corto); `inverted` = **largo** (a favor del pico). Simétrico en mínimos.

Es decir: un pico fallido (sweep) operado *a favor* del pico. La ruptura con cierre fuera es otra hipótesis (variante B del EA, con ventana 96: IS +0,03 R/t 0,36; OOS +0,30 R). La reprodujimos y registramos aparte; **no** fue la que produjo el resultado V7. `docs/V7_*` mantienen su texto original (no se sobrescribe); esta corrección prevalece.

## 2. Qué se implementó
`mql5/REMIX_V8_XAU_BREAKOUT.mq5` (compila 0 errores / 0 avisos). Parametrizado (`Variant`, `Lookback`, `PierceATR`, `CooldownBars`, `SL_ATR`, `RR`, `MaxHoldBars`). Solo velas cerradas (señal en la vela 1, entrada a mercado en la apertura de la vela 0); SL = 1 ATR(14) de la vela de señal; TP prefijado 1,5R y 3R; salida temporal a 40 velas; lote fijo 0,01; margen agregado ≤ 5 % de la equidad y tope de pérdida al SL ≤ 3 % (parámetros declarados). Registra **señales** (OPEN, COOLDOWN, REJ_MARGIN, REJ_RISK, ORDER_FAIL_…), **operaciones** (R, MFE, MAE, spread, margen, riesgo, sesión, motivo de salida) en `results/v8/<run>/ea_signals.csv` y `ea_trades.csv`. Bloqueado fuera del probador y en cuenta real. Sin martingala.

## 3. Paridad Python ↔ Strategy Tester (`research/V8_XAU_H1_PARITY.csv`)
| Prueba | Señales Python | Operaciones MT5 | Coinciden | Solo Python | Solo MT5 | Dirección | Motivo de salida |
|---|---|---|---|---|---|---|---|
| H1, TP 1,5R | 320 | 316 | 313 (97,8 %) | 7 | 3 | 100 % | 98,1 % |
| H1, TP 3R | 320 | 315 (+1 abierta al final) | 313 (97,8 %) | 7 | 2 | 100 % | 99,4 % |
| H4 (lote B), TP 2R | 243 | 248 | 242 (99,6 %) | 1 | 6 | 100 % | 99,6 % |
| H4 (lote B), TP 3R | 243 | 248 | 242 (99,6 %) | 1 | 6 | 100 % | 99,6 % |

**Todas las discrepancias tienen causa identificada:**
1. *Solo Python (H1, 7)*: 6 entradas en horas 22–23 UTC / 02:00 con mercado cerrado (retcode 10018, `ORDER_FAIL_10018`) — **Python asumía operaciones no ejecutables** (1,9 % de las señales; sus R netos suman +3,9 R, es decir, inflaban la expectativa de Python); 1 rechazada por tope de riesgo 3 % (ATR extremo, coherente en H4).
2. *Solo MT5 (H1, 3 / 2)*: 2 al inicio (Python no dispone de 96 velas previas, su serie empieza el 2024-01-01) y 1 al final (Python descarta señales sin 40 velas posteriores).
3. *H4*: la primera versión de Python **descartaba las velas H4 parciales** (<8 velas M15) y daba 227/233 coincidencias con 21 operaciones solo-MT5. Conservar las velas parciales —como hace MT5— da 4.537 barras = las 4.537 del probador y 242/243. Se corrigió el estudio del lote B con esa regla y se **rehizo entero** (los números de este informe son los corregidos).
4. *R por operación*: idéntico en SL-SL y TP-TP. Diferencia de resultado: 5 operaciones que Python cierra en TP y MT5 en SL (−2,5 R cada una) porque en cortos el SL se activa con el ASK y Python usa barras BID, y 1 salida temporal; suma de R neto de Python 54,8 vs MT5 47,0 sobre las 313 comunes (−0,025 R por operación = coste de spread real que Python aproxima restando spread/ATR).

Conclusión de paridad: **Python y MT5 producen las mismas señales (97,8 %–99,6 %) y las diferencias de resultado son de modelado de costes, no de lógica.**

## 4. Qué NO demuestra esta auditoría
El periodo del backtest (2024-01-01→2026-10-31) es exactamente el periodo en el que la regla se seleccionó (IS 2024-01→2025-06, OOS 2025-07→2026-10, ambos vistos en V4/V5/V7). Reproducir el beneficio histórico **no es una validación**. Ver `V8_VALIDATION_REPORT.md`.

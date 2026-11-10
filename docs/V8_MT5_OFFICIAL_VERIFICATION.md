# V8 — Verificación oficial en el Strategy Tester

Todas las pruebas: instancia aislada `C:\REMIX_MT5_LAB\terminal` (portable; el terminal principal PID 34572 no se tocó y siguió vivo), cuenta demo hedging, **3.000 USD**, apalancamiento 1:500, XAUUSDm, 2024-01-01→2026-10-31, lote fijo 0,01, EA `REMIX_V8_XAU_BREAKOUT` (sha256 fuente `430a8976…`, 0 errores/0 avisos en MetaEditor). Informes HTML originales, `trades.csv`, `deals.csv`, `stats.json`, `.set`, `.ini` en `results/v4_runs/<RUN_ID>/` (no se sobrescribe ninguno). Detalle en `research/V8_XAU_H1_OFFICIAL_RESULTS.csv`.

| Run | TF | Modelo | Operaciones | Neto USD | % | PF | DD equidad | Calidad histórico |
|---|---|---|---|---|---|---|---|---|
| 005 | H1 TP1,5R | OHLC 1 min | 316 | +395,57 | 13,2 | 1,17 | 6,96 % | 98 % |
| 006 | H1 TP3R | OHLC 1 min | 316 | +877,28 | 29,2 | 1,31 | 6,75 % | 98 % |
| 007 | H1 TP1,5R | cada tick generado (195 M ticks) | 316 | +389,21 | 13,0 | 1,17 | 6,97 % | 98 % |
| 008 | H1 TP1,5R | ticks reales | 316 | +390,93 | 13,0 | 1,17 | 6,91 % | **9 %** |
| 009–011 | H1 TP1,5R | OHLC 1 min + ExecutionMode 500/−1/2000 | 316 | +395,57 (idéntico) | | | | |
| 012 | H4 TP2R | OHLC 1 min | 248 | +1.622,79 | 54,1 | 1,49 | 8,11 % | 98 % |
| 013 | H4 TP3R | OHLC 1 min | 248 | +2.172,77 | 72,4 | 1,57 | 8,40 % | 98 % |

Verificaciones: símbolo, TF, periodo, capital, apalancamiento y modelo constan en cada `meta.json`; margen máximo usado 0,35 % de la equidad (límite 5 %); pérdida máxima al SL por operación 93 USD (3,1 %) — el lote mínimo 0,01 fija el riesgo según el ATR.

## Modelos de ticks (Fase 16)
- OHLC 1 min vs cada tick generado: 395,57 vs 389,21 USD (−1,6 %) con 316 operaciones idénticas → el modelo de 1 min es suficiente para H1/H4 con SL de 1 ATR.
- **Ticks reales: calidad de histórico 9 %.** El probador solo dispone de ticks reales para una fracción pequeña del periodo (el resto lo genera). Esta ejecución **no** puede presentarse como validación con ticks reales: estado `ERROR_DATOS (cobertura parcial)`. No se sustituyó por ninguna fuente externa. Resultado numéricamente igual al generado (390,93).
- Sonda de ticks del bróker (`research/V8_TICK_AVAILABILITY.csv`, solo lectura): ver estado en el informe de validación.

## Retrasos de ejecución
`ExecutionMode` = 500 ms / aleatorio (−1) / 2.000 ms produjo resultados **bit a bit idénticos** al caso sin retraso: la opción no tiene efecto medible en este build/modelo. No se declara prueba de latencia; el retraso se **modela** como sobrecoste (ver `V8_TRANSACTION_COSTS_SCENARIOS.csv`).

## Función oficial de optimización
No se ejecutó optimización completa/genética/forward de MT5: ningún candidato alcanzó la regla de promoción, y la rejilla de sensibilidad de 54 celdas (ventana × SL × RR) se calculó con el simulador validado contra el probador (paridad 99,6 %), registrando todas las celdas. Una optimización sobre el mismo periodo no añadiría evidencia independiente.

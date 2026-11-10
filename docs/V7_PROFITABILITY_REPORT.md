# V7 — Informe de rentabilidad diaria y distancia al objetivo del 1 % diario

Capital 3.000 USD, margen ≤ 5 % por instrumento (controlado en el EA de V4/V5), objetivo aspiracional 1 % diario neto. **Ninguna estrategia de V4, V5 o V7 se aproxima al objetivo.**

## Mejor evidencia disponible (informes oficiales de MT5, V5; solo beneficio realizado)
Fuente: `research/V7_DAILY_SUMMARY_V5_RUNS.csv` (66+13 ejecuciones) y `research/DAILY_PROFITABILITY_ANALYSIS.csv` (filas diarias de los dos mejores runs).

| Run (oficial MT5) | Retorno acum. 2,8 años | Media por día de negociación | Media por día calendario | Fracción del objetivo 1 % | DD realizado |
|---|---|---|---|---|---|
| ETHUSDm M15 F1 (el mejor del lote) | +26,1 % | 0,063 % | 0,024 % | **6,3 %** | −8,4 % |
| ETHUSDm M15 F1, solo 2025 | +11,8 % | 0,060 % | 0,011 % | 6,0 % | −8,4 % |
| ETHUSDm M15 F1, solo 2026 | +6,0 % | 0,044 % | 0,006 % | 4,4 % | −6,6 % |
| ETHUSDm M5 F1 | +4,0 % | 0,018 % | 0,005 % | 1,8 % | −9,9 % |

El mejor caso de las 79 ejecuciones oficiales rinde ≈ 0,06 % por día de negociación (16× menos que el objetivo), con intervalo de confianza que incluye 0 (V5) y sin superar la corrección por múltiples pruebas. Alcanzar 1 % diario equivale a ≈ 1.200 % anual compuesto; cualquier estrategia sin ventaja bruta mayor que el coste solo lo "alcanzaría" subiendo el riesgo, que en V5 amplificó las pérdidas (DD hasta 95 %). No se manipuló el riesgo.

## V7 (estudio de eventos)
No hay estrategia con expectativa neta positiva validada, así que no se construyó curva diaria V7. Orden de magnitud: aun con la pista XAUUSD H1 (≈ +0,15 a +0,25 R por operación, ~160 operaciones por 1,5 años ≈ 0,4 operaciones/día de negociación y 0,5 % de riesgo por operación), (≈ 0,3 operaciones por día calendario × 0,2 R × 0,5 % de riesgo) la rentabilidad esperada sería ≈ 0,03 % por día, es decir ≈ 3 % del objetivo, y es una pista no validada.

## Limitaciones de las métricas
- El beneficio flotante intradía y el drawdown intradía no se exportan en el informe HTML: figuran `NO_DISPONIBLE`. El DD indicado es de equidad al cierre de cada día.
- Sharpe/Sortino diarios, IC95 de la media, peor día, racha negativa y tiempo bajo el agua están en el CSV resumen; "probabilidad de pérdidas extremas" se estima solo como frecuencia empírica de días < −2 %.

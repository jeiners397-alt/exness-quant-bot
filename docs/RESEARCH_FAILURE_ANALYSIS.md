# Análisis de fallos y descartes (V5, primer lote)

Se distingue **diagnóstico confirmado** (hay medición) de **hipótesis** (sin medición).

## Diagnósticos confirmados
1. **Los costes dominan**: en el estudio de eventos el retorno medio *bruto* es ≈0 (−0,04 a +0,04 ATR) y el *neto* de spread es −0,12 a −0,19 ATR por evento (132 pruebas). Las 66 ejecuciones oficiales reflejan lo mismo: mediana de PF 0,85–0,95 en las 6 combinaciones familia×TF.
2. **F3 (reversión a la media |z|≥2,5) es la peor** en ambas temporalidades (mediana neto −1.006/−1.696; 0 positivas en M15): sin ventaja en ningún mercado salvo AUDUSD M5 (+77, t≈0,3).
3. **M5 no mejora a M15**: mediana peor en F2 y F3, similar en F1. Entrar antes no equivale a mayor rentabilidad.
4. **El riesgo por operación no crea ventaja**: al subir de 0,25 % a 2 % las pérdidas y el drawdown escalan (DD hasta 95 %); con ventaja ≤0, más lote solo acelera la pérdida.
5. **Ejecución correcta**: en 79/79 filas el símbolo/timeframe del log del EA coinciden con los pedidos, y en cada informe la suma de operaciones = Beneficio Neto oficial. No hay evidencia de error de implementación en ese sentido.
6. **Error técnico real**: la prueba con ticks reales de ETHUSDm 2026 falló por descarga de ticks cancelada (`no history data`), no por falta de señales (clase E).

## Hipótesis (no confirmadas; no repetir sin hipótesis nueva)
- Stops mal ubicados: no medido (SL fijo en múltiplos de ATR, sin comparar alternativas por familia).
- Régimen incompatible / horarios desfavorables: no medido en V5 (horario 0–24 h).
- Sobreajuste: no aplica a los parámetros (congelados, no optimizados) pero sí a la selección del "candidato" ETH entre 79 pruebas.
- Reglas sin capacidad predictiva: coherente con p_continuación ≈ 0,50, pero no es prueba causal.

## No repetir
F3 ZSCORE_REV con estos parámetros en cualquier mercado; F2 DONCHIAN_BO en índices US y forex majors (todas negativas M5/M15); F1 SWEEP_REV en forex majors e índices US.

## Pendiente de investigar (no ejecutado)
FVG, BOS/CHoCH, números redondos, estacionalidad por sesión (Londres/NY/Asia), gaps de apertura, rollover, noticias, expansión tras compresión por régimen de volatilidad, time-series momentum a horizontes largos, sensibilidad de spread/slippage, walk-forward con reoptimización, ticks reales.

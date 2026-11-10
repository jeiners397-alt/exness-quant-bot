# V7 — Análisis de fallos (lote 1)

**Diagnóstico medido**
1. **El coste es del mismo tamaño que cualquier efecto bruto.** Retorno bruto medio a 1,5R ≈ 0 en las 12 familias; coste 0,11–0,25 ATR (M15) → neto −0,09…−0,28 R. En H1 el coste baja a 0,084 ATR pero el bruto sigue siendo ≈ −0,03 R.
2. **Los patrones no superan al azar condicionado**: control (misma hora y tercil de ER) −0,19 R frente a −0,255 R de los eventos en IS.
3. **Continuación 0,47–0,53 a 10 velas** en todas las familias: sin sesgo direccional explotable detectado con estas definiciones.
4. **Inestabilidad IS↔OOS**: de las 65 pruebas M15 con expectativa OOS positiva, 60 tenían IS ≤ 0 (p. ej. USTEC FVG: IS t −2,42, OOS t +2,59). Un efecto real no cambia de signo entre mitades; esto es ruido o dependencia de régimen no identificada.
5. **XAGUSDm es inviable en M15**: coste 0,40 ATR por operación.
6. **Diversificación ilusoria**: índices US (ρ 0,75–0,95) y cripto (0,82) se mueven juntos; sumar backtests de esos mercados duplicaría el riesgo.

**Hipótesis (no medidas)**: la ventaja puede existir en horizontes más largos (H4/D1) donde el coste/ATR es mínimo, o ser condicional a eventos macro, o requerir datos de microestructura que el bróker no ofrece. No se pueden afirmar.

**No repetir sin hipótesis nueva**: reversión por Z-Score o RSI extremo en M15 (incluso filtrada por régimen); ruptura Donchian y BOS/CHoCH en M15 de cualquier mercado; ORB en índices y Forex; FVG en Forex.

**Siguientes hipótesis (lote 2 propuesto)**: (a) H4/D1 en XAU, índices y cripto con las mismas familias (menor coste/ATR; menos eventos, pide más datos que 2,8 años); (b) congelar la regla XAUUSD H1 *ruptura de 96 velas en continuación* y evaluarla solo con datos posteriores a 2026-11-01; (c) tiempo de salida y trailing sobre esa regla únicamente, con RR fijado de antemano.

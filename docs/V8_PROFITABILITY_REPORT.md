# V8 — Rentabilidad y distancia al objetivo del 1 % diario

Capital 3.000 USD, lote 0,01 (mínimo real; no se impuso 0,10), margen máximo usado 0,35 % de la equidad (límite 5 %). Beneficio **realizado**, neto de spread, swap y comisión (0 en Exness Standard). Fuentes: informes oficiales del Strategy Tester y `ea_trades.csv`; cálculo diario en `research/V8_DAILY_PROFITABILITY.csv`. **Son resultados retrospectivos en el periodo de selección, no beneficios obtenidos en una cuenta.**

| Run (oficial MT5) | Neto | Retorno | % medio por día de negociación | % medio por día calendario | Geométrico diario | Días neg. (L-V) | Peor día | DD balance | Máx. tiempo bajo el agua |
|---|---|---|---|---|---|---|---|---|---|
| H1 TP1,5R | +395,57 | 13,2 % | 0,017 % | 0,0125 % | 0,0120 % | 19,5 % | −2,66 % | 6,3 % | 173 d |
| H1 TP3R | +877,28 | 29,2 % | 0,031 % | 0,0247 % | 0,0237 % | 23,8 % | −2,63 % | 5,0 % | 141 d |
| H4 TP2R | +1.622,79 | 54,1 % | 0,055 % | 0,0433 % | 0,0418 % | 17,3 % | −1,92 % | 5,5 % | 160 d |
| H4 TP3R | +2.172,77 | 72,4 % | 0,070 % | 0,0548 % | 0,0527 % | 19,9 % | −1,84 % | 10,8 % | 175 d |

(La tabla diaria H1 TP3R usa las 315 operaciones registradas por el EA: 27,9 % vs 29,2 % oficial; la operación 316 queda abierta al final del test y se cierra a la fuerza fuera del registro.)

## Frente al 1 % diario
- El mejor caso (H4 TP3R, in-sample) rinde **0,070 % por día de negociación = 7 % del objetivo**; al ritmo de esa media harían falta ≈ 14 días de negociación para acumular un 1 %, pero con una dispersión alta: la mejor racha es una cifra del pasado, no una tasa esperable. El mejor resultado en V5 era 0,063 %/día (ETH M15), con intervalo que incluía 0.
- Alcanzar 1 % diario sostenido equivale a ≈ 1.200 % anual compuesto. Con el lote mínimo 0,01 sobre 3.000 USD el riesgo ya es 0,3–3,1 % por operación (la pérdida al SL de 1 ATR de oro es 10–93 USD): **subir riesgo para acercarse a la meta no es válido** (en V5 amplificó pérdidas hasta DD 95 %). No se manipuló.
- Frecuencia: 248 operaciones en 740 días de negociación (H4) = 0,33/día; el 1 % diario exigiría una expectativa por operación mayor en un orden de magnitud o una frecuencia mucho mayor con la misma ventaja neta, y no hay evidencia de ninguna de las dos.

## Costes (V8_TRANSACTION_COSTS*.csv)
Spread mediano XAU 160 puntos = 0,039 ATR(M15) → 0,0093 ATR(H4); swap observado: −30 USD (H1 1,5R), −53 (H1 3R), −96 (H4 2R), −134 (H4 3R) sobre las ejecuciones largas (swap_long −499 puntos/noche; swap_short 0 en el servidor). Escenarios MODELADOS sobre las operaciones del tester (no ejecuciones): costes +50 % → H4 3R +2.149 USD; ×2 → +2.125; ×3 → +2.078 (PF 1,55 a ×2). El sobrecoste de spread es pequeño frente a la ventaja bruta *si la ventaja existe*: la incertidumbre es estadística (¿existe fuera de la muestra?), no de costes. Comisión: no hay dato histórico verificable (Exness Standard declara 0); deslizamiento: el probador no lo aplica.

## Incertidumbre
Bootstrap por bloques de la expectativa por operación (R, incluye swap): H4 3R IC95 [+0,05, +0,55]; H4 2R [+0,04, +0,40]; H1 3R [+0,07, +0,42]; H1 1,5R [+0,01, +0,28]. Reordenaciones Monte Carlo del P&L: DD p95/p99 = 15,4 %/18,8 % (H4 3R), 12,9 %/15,9 % (H1 3R). Estos intervalos suponen operaciones independientes e **ignoran la selección** entre 3.174 pruebas: no son intervalos de confianza válidos de la ventaja real.

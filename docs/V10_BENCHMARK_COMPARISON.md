# V10 — Comparación contra referencias simples (XAUUSD H4)

Periodo 2024-01-02 → 2026-10-30, lote/tamaño equivalente a 0,01 (1 oz), capital 3.000 USD. Operaciones: motor Python idéntico al de V8 (verificado: reproduce la referencia V8 operación a operación). Series de exposición continua: PnL por barra H4 (mark-to-market). Controles aleatorios: 600 repeticiones, semilla fija. `research/V10_XAU_H4_BENCHMARKS.csv`.

| Referencia | n | Neto USD | expR | PF | DD máx USD (% de 3.000) | Exposición | Sharpe diario* |
|---|---|---|---|---|---|---|---|
| **Estrategia H4 (oficial MT5)** | 248 | +2.173 | +0,30 | 1,57 | 390 (13,0) | — | — |
| Estrategia H4 (referencia Python) | 243 | +2.210 | +0,35 | 1,59 | 377 (12,6) | 43 % | 1,37 (MTM, sin spread) |
| B. solo LONG | 160 | +1.491 | +0,44 | 1,66 | 481 (16,0) | 27 % | |
| C. solo SHORT | 83 | +719 | +0,18 | 1,48 | 426 (14,2) | 17 % | |
| D. entradas aleatorias (misma hora, frecuencia y % LONG) | 243 | +464 (media) | +0,12 | 1,12 | 775 (25,8) | | |
| D-L. aleatorias solo LONG | 160 | +742 | +0,30 | 1,29 | | | |
| D-S. aleatorias solo SHORT | 83 | −190 | −0,20 | 0,91 | | | |
| E1. mismas barras de ruptura, dirección aleatoria | 243 | +609 | +0,17 | 1,15 | | | |
| E1b. mismas barras, dirección invertida (fade) | 243 | −1.070 | −0,14 | 0,77 | 1.242 (41,4) | | |
| E2. barras aleatorias del mismo régimen (ER30 × ATR%), dirección aleatoria | 243 | +450 | +0,10 | 1,11 | | | |
| F. momentum simple 20 velas, 1 posición, mismas salidas | 470 | +2.538 | +0,18 | 1,30 | 783 (26,1) | 87 % | |
| A1. comprar y mantener 1 oz | 1 | +1.812 | — | — | 1.673 (55,8) | 100 % | 0,62 |
| A3. comprar y mantener, volatilidad igualada a la estrategia (0,66 oz) | 1 | +1.201 | — | — | 1.109 (37,0) | 100 % | 0,62 |
| G1. largo siempre, tamaño ∝ 1/ATR (volatilidad escalada) | — | +3.792 | — | — | 1.210 (40,4) | 100 % | 1,55 |
| G2. TSMOM 20 velas con tamaño 1/ATR | — | +1.923 | — | — | 915 (30,5) | 100 % | 0,80 |

\* Sharpe de la serie diaria de PnL (√252). Las filas MTM no incluyen spread de entrada; no son directamente comparables con las filas de operaciones en PF/expR.

## Lectura (medida, no supuesta)
1. **¿Es solo la tendencia del oro?** En gran parte sí. El oro subió +87,7 % y una entrada aleatoria con la misma hora y la misma proporción LONG (65 %) ya gana +0,12 R; las aleatorias solo LONG ganan +0,30 R y las solo SHORT pierden −0,20 R. La regla de ruptura LONG (+0,44 R) **no se distingue de las aleatorias LONG** (p = 0,16).
2. **¿Aporta la dirección de la ruptura?** Sí, es lo más sólido: con las mismas barras y la dirección aleatoria se obtiene +0,17 R (el 97,2 % de los 600 sorteos queda por debajo de +0,35 R, p ≈ 0,03); **invertida pierde −0,14 R**. En SHORT la ruptura (+0,18 R) supera a las aleatorias SHORT (−0,20 R; p = 0,027) porque estas pierden contra la tendencia. Frente al control por régimen (E2) p = 0,017.
   *Advertencia:* son 5 contrastes sin corrección por multiplicidad; con 5 comparaciones el umbral de Bonferroni al 5 % es p = 0,01 y ninguno lo cumple.
3. **Riesgo.** Por unidad de drawdown la estrategia es mejor que todas las referencias: neto/DD 5,6 frente a 1,1 (comprar y mantener) y 3,1 (largo 1/ATR). Pero el **Sharpe diario de largo-siempre 1/ATR (1,55) supera al de la estrategia (1,37, sin spread)** y su neto es mayor (+3.792 USD) con mucho más drawdown (40 % de 3.000). La estrategia tiene el 43 % de exposición.
4. **Cola.** CVaR 5 % por operación −1,14 R (el SL limita la pérdida a ≈ −1 R); la ruptura invertida y comprar y mantener tienen colas mucho peores (DD 41 % y 56 %).
5. **Costes.** El spread es 1,1 % del R; irrelevante. El swap sí pesa (−133,5 USD).

## Conclusión de la comparación
La línea H4 **no es solo exposición al oro**: tiene información direccional medible frente a controles (dirección invertida pierde), buena relación neto/DD y baja exposición. **Tampoco está demostrada**: la mayor parte del neto coincide con lo que da cualquier entrada LONG en un oro alcista, el valor incremental sobre las aleatorias es ≈ +0,13…+0,20 R con p ≈ 0,02–0,03 sin corrección, y una referencia sencilla de volatilidad escalada obtiene más Sharpe. No se afirma que supere a ninguna referencia más allá de lo medido aquí.

# V10 — Rentabilidad y distancia al 1 % diario

Capital 3.000 USD, lote 0,01, margen usado < 1 % de la equidad (máximo 5 % permitido; no se usó). Beneficio realizado neto de spread y swap (comisión 0), por fecha de cierre **del registro del EA** (`position_id`). Definición idéntica a V9: retorno diario = beneficio cerrado / balance previo; «día de negociación» = lunes–viernes (2024-01-01 → 2026-10-31). `research/V10_DAILY_PROFITABILITY.csv`. **Todo es retrospectivo: ningún valor es un beneficio obtenido en cuenta.**

| Sistema (oficial MT5) | Op./día | Neto USD | % medio/día negoc. | % medio/día calend. | Geom./día | Días negativos* | Peor día | DD balance | Máx. bajo el agua | Días a +1 % a ese ritmo |
|---|---|---|---|---|---|---|---|---|---|---|
| XAU H4 TP 3R (congelada) | 0,33 | +2.172,77 | **0,070 %** | 0,055 % | 0,053 % | 19,9 % | −1,84 % | 10,8 % | 178 d | 14 |
| XAU H4 TP 2R (congelada) | 0,33 | +1.622,79 | 0,055 % | 0,043 % | 0,042 % | 17,3 % | −1,92 % | 5,5 % | 174 d | 18 |
| XAU M15 ruptura 96 (control) | 1,45 | +643,99 (informe: +656,97) | 0,020 % | 0,020 % | 0,019 % | 54,9 % | −2,17 % | 8,7 % | 218 d | 50 |
| XAU M5 ruptura 30 (control V9) | 9,78 | −1.467,78 | −0,097 % | −0,062 % | — | — | −3,90 % | 49,6 % | 1.027 d | no aplica |
| Referencia: comprar y mantener 1 oz | — | +1.811 | 0,068 % | 0,058 % | — | — | — | 55,8 % (MTM) | — | — |

\* % de días lun–vie con resultado cerrado negativo. El neto del EA para M15 (643,99) difiere del informe (656,97) porque el registro del EA omite una posición cerrada por el probador al final; se cita el informe en `V10_OFFICIAL_MT5_RESULTS.csv`.

## Lectura
- **La línea H4 llega al 7 % de la meta del 1 % diario** (0,070 %/día); con el DD de balance del 10,8 % y 178 días bajo el agua. Comprar y mantener 1 oz obtiene el mismo promedio diario (0,068 %) con un drawdown de 56 %. Ni el 0,07 % es un resultado esperable hacia delante: el tramo 2026 aporta el 66 % del neto.
- **Más operaciones no mejoran nada:** M15 (1,45 op./día) rinde 0,020 %/día; M5 (9,8 op./día) pierde 0,097 %/día. El spread de 0,16 USD sobre ≈ 1,45 operaciones al día en M15 cuesta ≈ 0,008 %/día frente a un neto de 0,020 %/día: el coste ya consume un tercio del rendimiento bruto.
- Subir de 0,070 % a 1 % diario con el mismo edge exigiría multiplicar el tamaño ≈ 14× (≈ 0,14 lotes de media): la pérdida por operación pasaría de ≈ 23 USD (0,8 % de 3.000) a ≈ 320 USD (≈ 11 %) y el drawdown de balance de 10,8 % a ≈ 150 %, es decir, ruina. **No se subió el riesgo, no hay martingala, no se forzaron operaciones.**
- Un 1 % diario compuesto equivaldría a +1.100 % por año; ningún dato de este proyecto lo respalda.

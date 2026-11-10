# V9 — Rentabilidad y distancia al 1 % diario

Capital 3.000 USD, lote 0,01, margen máx. usado < 1 % de la equidad. Beneficio realizado neto de spread y swap (comisión 0). `research/V9_DAILY_PROFITABILITY.csv`. Todo retrospectivo; **ningún dato es un beneficio obtenido en cuenta**.

| Sistema (oficial MT5) | Operaciones/día negoc. | Neto | % medio / día negoc. | Geométrico/día | Días negativos | Peor día | DD balance | Días para +1 % a ese ritmo |
|---|---|---|---|---|---|---|---|---|
| A · XAU H1 TP1,5R (V8) | 0,43 | +395,57 | 0,017 % | 0,012 % | 19,5 % | −2,66 % | 6,3 % | 58 |
| A · XAU H1 TP3R (V8) | 0,43 | +877,28 | 0,033 % | 0,024 % | 23,8 % | −2,63 % | 5,0 % | 31 |
| A · XAU H4 TP2R (V8) | 0,34 | +1.622,79 | 0,055 % | 0,042 % | 17,3 % | −1,92 % | 5,5 % | 18 |
| A · XAU H4 TP3R (V8) | 0,34 | +2.172,77 | 0,070 % | 0,053 % | 19,9 % | −1,84 % | 10,8 % | 14 |
| B · scalping M5 (control negativo) | 9,8 | −1.467,78 | **−0,097 %** | negativo | — | — | 49,6 % | no aplica |

## Frente a la meta
- La línea A en su mejor caso es el 7 % de la meta del 1 % diario y es in-sample (clase C).
- El scalping, con 10 operaciones/día, **resta** 0,097 % por día: más frecuencia solo multiplica el coste (spread $0,16 × 9,8 operaciones/día). Un 1 % diario con este spread exigiría ≈ 30 USD/día, es decir ≈ 3 USD netos por operación a 10 operaciones/día (≈ 1,1 ATR(M5) por operación con lote 0,01), cuando el retorno bruto medido es ≈ 0 ATR.
- No se subió riesgo, no hay martingala, no se forzaron operaciones, no se ocultaron pérdidas en cestas (el DD incluye flotante en `V9_BASKET_TRADING.csv`).

## Coste diario del scalping (medido)
M5: coste/ATR 0,070 → con ≈ 9,8 operaciones/día y riesgo medio ≈ $2,7 por operación (1 ATR M5 con 0,01 lote) ≈ $1,9 de coste en spread por día de negociación, es decir 0,06 % de 3.000 USD por día solo en spread; M1: 0,166 ATR (×2,4).

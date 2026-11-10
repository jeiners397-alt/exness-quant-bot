# V9 — Preservación de XAU (línea A, XAU CORE)

**Estado: CONGELADA. Retrospectiva, clase C, no validada de forma independiente. Ticks reales no disponibles. Es un resultado de backtest, no un beneficio obtenido en una cuenta.**

## Referencia H4 (no se modifica ni se optimiza en V9)
| Parámetro | Valor |
|---|---|
| EA | `mql5/REMIX_V8_XAU_BREAKOUT.mq5`, SHA-256 `430a8976bb7e163c65d1a4c11a520929e71a38b06602472570cd30a465568e3e` (sin cambios desde V8; verificado) |
| Mercado/TF | XAUUSDm H4 |
| Señal | `Variant=1` (primera vela que **cierra fuera** del rango de `Lookback=20` velas; continuación) |
| Salidas | SL 1,0 ATR(14) de la vela de señal; TP 2R y 3R; salida temporal 40 velas |
| Enfriamiento | `CooldownBars=6` |
| Tamaño | lote fijo 0,01; margen agregado ≤ 5 %; tope de pérdida al SL 3 % |
| Prueba | 3.000 USD, 1:500, OHLC 1 min, 2024-01-01→2026-10-31 |

| Resultado oficial (informe MT5) | Neto | PF | Operaciones | DD equidad | SHA-256 informe HTML |
|---|---|---|---|---|---|
| TP 2R (run 012) | +1.622,79 USD | 1,49 | 248 | 8,1 % | `0577bc21356e1736…` |
| TP 3R (run 013) | +2.172,77 USD | 1,57 | 248 | 8,4 % | `750dd750893a7f3d…` |

Referencia H1 (V8): TP 1,5R +395,57 USD (PF 1,17, informe `d8aa9e13…`), TP 3R +877,28 USD (PF 1,31, `53a833b5…`). Hashes completos de informe, `trades.csv` y `stats.json`: `results/v9/XAU_FROZEN.json` y `research/V9_XAU_H4_BASELINE.csv`.

## Verificación y reglas
- `python -m research.v9_preserve --verify` recalcula los SHA-256 del EA y de los 4 informes oficiales y falla si algo cambió (test `test_xau_h4_baseline_frozen_and_unchanged`). Resultado al cierre de V9: **OK, sin cambios**.
- La reserva prospectiva (datos ≥ 2026-11-01) **no se usó** ni se descargó en V9; solo servirá para evaluar esta definición exacta. Con ≈ 0,34 operaciones por día de negociación hacen falta ≈ 6 meses (≥ 100 operaciones).
- No se fusiona con el scalper ni se usa como argumento de rentabilidad del scalper.

## Por qué sigue en clase C (de V8)
t ≈ 2,6–2,9 frente a t* = 3,69 (V8) / 4,05 (acumulado V7+V8+V9, 3.719 pruebas); el periodo del backtest es el de selección; un solo mercado y el régimen alcista del oro 2024–2026; 2026 aporta la mayor parte del beneficio; sin ticks reales.

## Compatibilidad con otros sistemas (solo lo medido en V9)
Simulación barra a barra sobre las mismas señales H4 con cuenta compartida de 3.000 USD (`V9_BASKET_TRADING.csv`; el simulador es ≈ 30 % más optimista que MT5, así que solo se interpretan diferencias relativas):
- Hasta 2 posiciones H4 simultáneas; margen máximo 0,67 % de la equidad. Permitir varias (individual) rinde más que "una posición" (+2.102 vs +1.898 USD).
- Cobertura del perdedor: +29 USD con PF 1,64→1,52: no aporta. Cesta sin SL individual: +612 USD, PF 1,10, DD 24 % (frente a 6,9 %): empeora. Cesta con SL: +1.606, DD 14,6 %.
- La combinación H4+H1+scalper en cuenta compartida **no se simuló**: el scalper no tiene evidencia (Fase 20 exige evidencia previa).

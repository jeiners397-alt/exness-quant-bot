# Pruebas de múltiples posiciones y margen (V4)

## 1. Simulación (tests/test_margin_v4.py, 18 pruebas) y especificaciones reales (research/MARGIN_ALLOCATION_RESULTS.csv)
Ejemplo de la orden (150 USD; 40+50+45 → restante 15), tope 5 %, pendientes contadas, reservas sin doble uso, límite global, riesgo ≠ margen, rechazo sin redondeo hacia arriba, hedging vs netting, conciliación.

## 2. DENTRO del Strategy Tester (EA `REMIX_EURUSD_V4.mq5`, módulo diagnóstico `V4_DIAG_MULTI`)
Diagnóstico sintético, **no es una estrategia** (su P&L negativo no tiene significado): abre compras periódicas (M15, 2025-06-02→2025-09-01, 3.000 USD, 1:500) con SL cíclico estructural/ATR/régimen y cada 4ª señal como BUY_LIMIT, para estresar el controlador. Margen = `OrderCalcMargin` de posiciones + pendientes + la nueva; riesgo = `OrderCalcProfit` al SL.

| | EURUSDm | XAUUSDm | US30m |
|---|---|---|---|
| Entradas admitidas (mercado+pendientes) | 1.245 | 1.697 | 1.027 |
| Rechazadas por margen | 826 | 219 | 908 |
| Admisiones que superan el 5 % | **0** | **0** | **0** |
| Margen máx. tras admitir / presupuesto | 99,997 % | 99,95 % | 99,993 % |
| Mínimo del broker / paso | 0,01 / 0,01 | 0,01 / 0,01 | **0,05** / 0,01 |
| Lotes usados (mín–máx) | 0,01–0,30 | 0,01–0,07 | 0,05–0,84 |
| Lotes < mínimo / fuera de paso | 0 / 0 | 0 / 0 | 0 / 0 |
| Posiciones simultáneas máx. / pendientes máx. | 8 / 9 | 10 / 11 | 10 / 13 |
| Riesgo al SL máx. por operación | 0,5001 % | 0,5001 % | 0,5002 % |
| Distancia SL media STRUCT / ATR / REGIME | 0,00156 / 0,00127 / 0,00135 | ver `V4_DIAG_XAUUSDm.json` | ver `V4_DIAG_US30m.json` |

Notas: (a) "margen máx. 5,002 % de la equidad" que imprime el EA es medido tras el relleno, cuando la equidad ya bajó por el spread; en el momento de admitir nunca supera el presupuesto (columna `n_admitted_exceeding_budget`=0). (b) 0,01 se usó cuando cabía, pero no es tope (hasta 0,84 lotes en US30m), y US30m respeta su mínimo real 0,05. (c) Con 1:500 todos los rechazos fueron por margen en este estrés porque el EA insiste cada 3 barras; el riesgo de 0,5 % limitó el tamaño de cada operación. (d) Hedging: cuenta hedging, varias compras simultáneas con tickets distintos; netting no se ejecutó en el Tester (solo simulación).
Archivos: `research/V4_DIAG_*.json`, `V4_DIAG_*_events.csv`, informes oficiales en `results/v4_runs/RUN_*`.

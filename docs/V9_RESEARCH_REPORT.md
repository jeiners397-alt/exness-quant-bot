# REMIX V9 — Informe de investigación: scalping M1/M5 + preservación XAU

Alcance: instancia aislada `C:\REMIX_MT5_LAB\terminal` (el terminal principal no se tocó); solo Python y Strategy Tester; sin `order_send`. Rama `feature/remix-v9-scalping-discovery`.

## Lote A — preservar V8
EA XAU H4/H1 verificado por SHA-256, parámetros y resultados oficiales congelados (`V9_XAU_H4_BASELINE.csv`, `docs/V9_XAU_H4_PRESERVATION.md`). Sin re-optimización.

## Datos (Fase 15, requisito obligatorio)
- Causa del límite de V7/V8: el terminal aislado tenía `MaxBars=100000` en `config/common.ini`. Se elevó a 3.000.000 **solo en la instancia aislada** (copia de seguridad `common.ini.bak_v9`). Con eso: **XAUUSDm M1 973.336 barras y M5 198.454 barras, 2024-01-01→2026-10-30**; EURUSDm/GBPUSDm/USTECm M5 ≈ 200–211 k. Descarga segmentada por mes con caché (`data/raw/v9/cache`, no se re-descarga nada) y sin datos ≥ 2026-11-01.
- Dos errores propios corregidos: archivos de caché vacíos por una descarga anterior limitada, y `download_info.json` sobrescrito (ahora se fusiona).
- **Ticks reales (medido):** de 12 muestras de 5 min (una por trimestre), solo las 3 más recientes (2026-05-13, 2026-08-12, 2026-10-28) devolvieron ticks (1.303–2.668 ticks, 0 bid/ask inválidos; 7–18 marcas de tiempo repetidas por muestra = varios ticks en el mismo ms; huecos máx. 1,4 s); las 9 anteriores (2024-02 → 2026-02) agotaron el límite de 100 s sin datos (`ERROR_DATOS`). Coincide con la calidad del 9 % del probador: hay ticks reales únicamente para el tramo más reciente (≈ desde 2026-05). Las muestras válidas quedan en caché (`data/raw/v9/ticks`). **No se inventaron ticks**; no se declara rentable ningún scalper intrabar.

## Lotes B y C — microestructura y eventos (XAU M1 y M5; EURUSD, GBPUSD, USTEC solo M5)
Protocolo fijado de antemano: DEV 2024, SEL 2025, VAL 2026-01→10 (evaluada una sola vez por candidata). Señal al cierre de la vela *i*, entrada en la apertura de *i+1*, spread real de la vela, SL de medición 1 ATR, TP 0,5–3R, tiempo máximo 60 min, enfriamiento 10 velas, control aleatorio por hora y tercil de ER. 10 familias (A momentum, B ruptura, C barrida, D reversión, E pullback, F expansión de volatilidad, G sesión/ORB, H multi-timeframe, I ruptura+retest, J rango) × primario/invertido × 5 RR.

**Microestructura XAUUSDm (todo el periodo):**
| | M1 | M5 |
|---|---|---|
| Spread mediano | 160 pts ($0,16) | 160 pts |
| ATR mediano | $1,11 | $2,68 |
| **Coste/ATR** | **0,166** | **0,070** |
| Autocorrelación lag 1 / lag 5 | −0,0005 / −0,001 | +0,008 / +0,002 |
| Razón de varianza (5) | 0,987 | 1,013 |
| Curtosis | 95 | 60 |

Sin persistencia ni reversión explotables; el spread se dispara en 21–23 UTC (coste/ATR > 1 en otros pares). `V9_XAUUSD_SESSION_PROFILE.csv`, `V9_XAUUSD_SPREAD_ANALYSIS.csv`.

**Resultado (500 pruebas, t* = 3,53): ninguna candidata.** XAU M1: 100 D. XAU M5: 1 C (G_SESSION_ORB TP 3R: DEV +0,03, SEL +0,07, **VAL −0,11**), 79 D, 20 F. EURUSD/GBPUSD/USTEC M5: 0 candidatas.
- Retorno **bruto** medio a 1,5R ≈ 0 en las 10 familias (−0,015 a +0,014 R); el coste lo vuelve neto negativo: M1 −0,16…−0,32 R, M5 −0,05…−0,12 R (XAU), −0,26 a −0,48 (USTEC/EUR/GBP, coste/ATR 0,25–0,48).
- **M1 vs M5:** el coste/ATR es 2,4 veces menor en M5 (0,070 vs 0,166); M5 pierde menos pero tampoco tiene ventaja bruta. M1 no es viable con spread de $0,16.
- **Entrada inmediata / confirmada / retroceso** (A y B, `V9_MOMENTUM_ANALYSIS.csv`): ninguna mejora lleva la expectativa a positiva; la confirmación de una vela baja el coste efectivo en M5 B (−0,048 vs −0,091 R) pero deja de operar la mitad de las señales y sigue siendo negativa.
- **Rangos (J):** el precio vuelve al centro en el 78 % (M1) / 59–62 % (M5) de los casos pero rompe el rango casi siempre (M1 100 %, M5 90–95 %); el neto es −0,41/−0,20/−0,21 R (M1 DEV/SEL/VAL) y −0,01/−0,18/−0,09 (M5). `V9_RANGE_SCALPING.csv`.
- **Barridas (C):** sin diferencias por distancia ni sesión que superen el coste (`V9_LIQUIDITY_SWEEPS.csv`).
- Probabilidades, MFE/MAE y tiempos por familia/sesión/split: `V9_ENTRY_PROBABILITIES.csv` (1.024 filas).

## Múltiples posiciones, cesta y cobertura (`V9_BASKET_TRADING.csv`, `V9_HEDGING_ANALYSIS.csv`)
Simulador de cuenta compartida (3.000 USD, lote 0,01, spread real, equidad con flotante). Sobre XAU H4 baseline (mismas señales): individual +2.102 USD / PF 1,64 / DD 6,9 %; una posición +1.898; máx. 3 = individual (nunca hay más de 2 simultáneas); cierre en señal opuesta = individual; cobertura del perdedor (−0,7R) +2.132 / PF 1,52; **cesta sin SL individual +612 / PF 1,10 / DD 24,4 %; cesta con SL +1.606 / PF 1,45 / DD 14,6 %**. Sobre los scalpers M5 (contraste): todas las políticas pierden (individual −284 a −1.851 USD); la cesta sin SL multiplica el DD (31 %, 69 %). Conclusión: las posiciones múltiples no cambian el signo, la cesta oculta pérdidas flotantes y la cobertura no aporta; no se recomienda.

## Lote D — backtests oficiales
No hay candidatas, así que **no se construyó ningún scalper "ganador"**. Se ejecutó **1 backtest oficial de contraste** (no candidata): EA V8 variante B en M5 (ruptura de 30 velas, hold 12, RR 1,5, cada tick, 2024-01→2026-10): **7.237 operaciones, −1.467,78 USD, PF 0,91, DD 50 %**, 9,8 operaciones/día. Paridad Python–MT5: 97,2 % de señales, dirección 100 %, diferencias = 195+12 entradas con mercado cerrado/fallo de ejecución. Expectativa por operación: Python −0,091 R, MT5 −0,075 R.

## Qué no se hizo
Optimización de MT5 y walk-forward (sin candidata), ML, noticias (no hay fuente histórica verificable), order flow (no hay profundidad), ticks reales, cartera H4+H1+scalper (Fase 20 exige evidencia previa), más de 4 instrumentos.



# REMIX V5 — Multi-Market Edge Discovery: informe del primer lote (2026-11-09)

Todo en Strategy Tester (instancia aislada, cuenta demo vacía, 3.000 USD, 1:500, modelo OHLC 1 min, 2024-01-01→2026-11-01). Sin `order_send`. **Ninguna estrategia se declara rentable.**

## 1. Qué se ejecutó (datos reales)
| Fase | Resultado |
|---|---|
| Inventario | 357 símbolos reales (`research/EXNESS_MARKET_UNIVERSE.csv`): 95 forex exóticos, 111 otros CFD, 64 índices US, 35 cripto, 21 minors, 7 majors, 5 oro, 5 plata, 4 EU, 4 Asia, 3 energía, 3 otros metales. **Cobertura histórica evaluada solo en 24 símbolos** (los otros 333 figuran `NO_EVALUADO`: descargar 357 historiales cuesta ~3 símbolos/min). No se afirma que se hayan investigado todos los mercados. |
| Escáner oficial `Optimization=3` | probado; **no utilizable para este fin** (ver `MT5_MARKET_SCANNER_VERIFICATION.md`) → método alternativo: una ejecución oficial por símbolo con el ejecutor V4 |
| EA genérico `REMIX_V5_GENERIC.mq5` | compila 0/0; usa `_Symbol/_Period`, SL/TP en múltiplos de ATR, sin pips ni EURUSD; margen 5 % + riesgo 0,5 % independientes (V4) |
| Estudio de eventos M15 | 11 mercados × 4 eventos × 3 horizontes = 132 pruebas (`EVENT_STUDY_RESULTS.csv`) |
| Lote de estrategias | **66 ejecuciones oficiales** (3 familias × 11 mercados × M5/M15) + 9 de sensibilidad de riesgo + 4 de validación = **79 filas** en `MULTI_MARKET_STRATEGY_MATRIX.csv` (85.952 operaciones en las 66 del lote) |

## 2. Familias (parámetros congelados, sin optimizar por activo)
F1 SWEEP_REV (barrida de máx/mín del día previo + cierre dentro; SL tras el extremo, TP 1,5R), F2 DONCHIAN_BO (ruptura de 48/96 barras con rango ≥ ATR; SL 1,5 ATR, TP 2R), F3 ZSCORE_REV (|z|≥2,5 contra SMA50; SL 2 ATR, TP 1R). Costes: filtro (spread+2 pts)/SL ≤ 0,10. Salida temporal 48 (M15)/96 (M5) barras.

## 3. Resultados del lote (66 ejecuciones, neto USD en 2,8 años)
| Familia / TF | Mediana neto | Mediana Exp R (proxy) | Mediana PF | Positivas (de 11) |
|---|---|---|---|---|
| F1 M15 | −416 | −0,076 | 0,88 | 2 |
| F1 M5 | −327 | −0,073 | 0,88 | 2 |
| F2 M15 | −617 | −0,036 | 0,95 | 2 |
| F2 M5 | −891 | −0,063 | 0,91 | 1 |
| F3 M15 | −1.006 | −0,069 | 0,87 | 0 |
| F3 M5 | −1.696 | −0,078 | 0,85 | 1 |

Por categoría (n=66): cripto 4 positivas de 12; forex majors 1/24; oro 1/6; índices US 0/18; plata 2/6 (ambas con 33–66 operaciones). Clasificación: sobre las 79 filas: **0 prometedoras (A), 1 B (validación 2024 de ETH F1: 66 ops, PF 1,29, una sola ejecución), 77 C (negativas/marginales), 0 D, 1 E (ticks reales ETH: error de datos), 0 F** (ver CSV). Max. margen por símbolo observado 4,05 % (<5 %); lote medio 0,01–1,66.
Exp R es un *proxy* (= esperanza por operación / |pérdida media|), no la R exacta.

**Positivas (8 de 66)**: ETHUSDm F1 M15 (+783, PF 1,14, 618 ops), ETHUSDm F2 M15 (+108), ETHUSDm F1 M5 (+121), XAGUSDm F2 M5 (+54, 66 ops), XAGUSDm F2 M15 (+6, 33 ops), AUDUSDm F3 M5 (+77), XAUUSDm F1 M5 (+74, PF 1,00), BTCUSDm F1 M15 (+4). Con N=79 pruebas, el umbral t por azar es **2,96**; el mayor t es **1,52** (ETH F1 M15). **Ninguna pasa la corrección por múltiples pruebas.**

## 4. Candidato débil: F1 SWEEP_REV en ETHUSDm M15
618 ops, +783 USD, PF 1,14, R≈+0,075, IC bootstrap por bloques [−0,011; +0,160] (incluye 0), p de control por inversión de signos 0,065, 8 de 12 trimestres positivos, sin la mejor operación +754, sin las 5 mejores +641 (no depende de outliers). Validación por año con parámetros congelados: 2024 +144 (66 ops), 2025 +353, 2026 +181 (positivo en los tres; **ya vistos en el escaneo**, no independientes). BTCUSDm (mismo tipo de activo) con la misma regla: +4 (≈0) y M5 ETH solo +121 → el resultado no se replica en el activo hermano. Prueba con ticks reales de 2026: **no se pudo ejecutar** (error de datos: `no history data`, descarga de ticks cancelada; ver matriz fila `…realticks…`, clase E). Estado: **hipótesis a seguir investigando con evidencia prospectiva, no estrategia rentable**. ETH tiene mínimo de lote 0,10 y spread de 100 pts.

## 5. Estudio de eventos (132 pruebas, M15, 2024-2026, neto de spread, unidades ATR)
Retorno medio bruto ≈ 0 (E1 −0,007; E2 −0,003; E3 −0,038; E4 +0,038 ATR) y neto de costes −0,12 a −0,19 ATR: **los costes explican la pérdida**. 8 de 132 pruebas netas positivas; t máximo 1,36 (USDJPY E4 h16) frente a t* 3,12. El p de control (direcciones aleatorias en las mismas horas) es optimista porque los eventos se solapan. Probabilidad de continuación ≈ 0,48–0,52. No se hizo FVG/BOS/CHoCH, números redondos, estacionalidad por sesión, apertura Londres/NY ni gaps (pendiente, ver `RESEARCH_FAILURE_ANALYSIS.md`).

## 6. Sensibilidad del límite de riesgo al SL (F2 M15, margen 5 % fijo)
| Riesgo | EURUSDm | XAUUSDm | US30m | DD equidad máx. | Margen máx. |
|---|---|---|---|---|---|
| 0,25 % | −519 | +68 | −896 | 18–31 % | 0,6–1,2 % |
| 0,5 % (base) | −1.007 | −66 | −1.559 | – | – |
| 1,0 % | −1.780 | −973 | −2.383 | 50–80 % | 2,3–4,7 % |
| 2,0 % | −2.564 | −1.990 | −2.838 | 79–95 % | 4,8–5,0 % |
Subir el riesgo amplifica pérdidas (la ventaja es ≤0); a 2 % el margen del 5 % empieza a ser vinculante. Con 0,25 % XAUUSDm rechazó 1.780 señales porque su lote mínimo excede el riesgo permitido. El límite de seguridad NO se relajó.

## 7. Qué no se hizo / limitaciones
- Cobertura de mercados: 24 de 357 evaluados; primer lote = 11 mercados, todos con M15 desde 2024-01-01 (BTC/ETH rozan el límite de 100.000 barras del terminal). No evaluados: forex minors/exóticos, índices EU/Asia, energía, otras criptos y CFD.
- Modelo OHLC 1 min (preliminar, no válido para estrategias intrabar); ticks reales solo desde 2026 y la prueba falló.
- Periodos ya explorados en fases previas para EURUSD; sin conjunto prospectivo nuevo. Sin walk-forward formal con reoptimización (parámetros congelados, así que el análisis por año actúa como corte temporal).
- Sensibilidad a spread/slippage no ejecutada (solo filtro de coste fijo); sin pruebas de FVG/BOS/CHoCH/estacionalidad/noticias.
- Informes HTML completos (79) y CSV de operaciones: en local; en Drive solo la versión condensada.

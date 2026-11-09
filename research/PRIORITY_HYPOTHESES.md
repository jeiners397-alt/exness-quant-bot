# REMIX FOREX V1 — 16 hipótesis prioritarias
Versión 1.0 · 2026-11-09 UTC. Selección por **viabilidad técnica, datos, compatibilidad Exness, costes, causalidad, riesgo, robustez y complejidad**. No se usó ningún winrate ni ranking de las fuentes. Ninguna está validada: todas son hipótesis a contrastar con OOS.

## Restricción transversal: capital de 100 USD y lote mínimo
Con `volume_min = 0,01` y 0,5 % de riesgo (0,50 USD):
- EURUSDm: 0,01 lote ≈ 0,10 USD/pip ⇒ solo SL ≤ ~5 pips caben en el presupuesto; para un SL de 20 pips hacen falta ~400 USD.
- XAUUSDm: 0,01 lote ≈ 1 USD por 1 USD de recorrido ⇒ un SL de 5 USD exige ~1 000 USD.
- Medido: S01/EURUSDm/M15, ene–mar 2025: **49 señales, 49 rechazadas** por política estricta; el lote mínimo arriesgaría de media 2,69 %.
**Consecuencia:** la ventaja estadística se investiga en múltiplos de R con lote teórico (`ideal`, no ejecutable) y la viabilidad con 100 USD se evalúa como restricción separada. No se cambia capital ni riesgo sin autorización.

## Hipótesis (orden de ejecución propuesto)

| # | Hipótesis | IDs canónicos | Por qué entra | Riesgos conocidos |
|---|---|---|---|---|
| 1 | **London Breakout** (rango asiático) | LAB_S01 · REMIX_S081, S045, S044 · FUT_S008 | Implementada en Python y MQL5; reglas completas; solo OHLC+spread; P0 en la matriz | Hora de servidor ≈ UTC (cambio de horario de Londres); coste del spread en SL cortos |
| 2 | **Donchian + ATR** | LAB_S02 · REMIX_S097 · FUT_S016 · SPOT_S020 · EXTRA_003/004 · WEB_007 | Ya implementada; 6 fuentes la repiten (familia más recurrente) | Muchas falsas rupturas en M5/M15; sensible al spread |
| 3 | **EMA+ADX pullback** | LAB_S03 · FUT_S012, S039 · EXTRA_005 · WEB_005 | Ya implementada; filtro de tendencia explícito | ADX de MT5 vs Wilder: verificar paridad |
| 4 | **Squeeze Bollinger + momentum** | LAB_S04 · REMIX_S089, S076 · FUT_S006, S017 · EXTRA_001, 015 · WEB_003 | Ya implementada; contrapunto de volatilidad | Umbral de *squeeze* depende de ventana |
| 5 | **PDH/PDL: ruptura-retest y barrido-reversión** | REMIX_S083 · FUT_S025 · WEB_006 · EXTRA_008 | Niveles diarios 100 % causales (D1 cerrado); P0 | Definir «día» (cierre 00:00 servidor) y retardo de confirmación |
| 6 | **Apertura NY (ORB 15 min)** | REMIX_S082 · WEB_009 | Extensión natural de S01 con otra sesión; misma infraestructura | Solapa con noticias USA (sin calendario) |
| 7 | **Reversión Keltner/BB con filtro de régimen** | REMIX_S086 · FUT_S026 · FUT_S051 (línea base) | Única clase de *mean reversion* con regla clara; diversifica S01–S04 | En tendencia pierde; necesita régimen |
| 8 | **Expansión de ATR** | FUT_S013 · EXTRA_023 | Regla causal simple (rango > k·ATR previo) | Se solapa con S02/S04 |
| 9 | **Supertrend + EMA200** | REMIX_S088 · FUT_S005 | P0; seguimiento de tendencia lento, poco sensible a costes | Whipsaws en rangos |
| 10 | **Ichimoku: ruptura de Kumo** | FUT_S015 · REMIX_S093 | Regla causal con retraso del Chikou explícito | Muchos parámetros fijos |
| 11 | **Momentum de series temporales (TSMOM) D1 con filtro SMA200** | REMIX_S064 · WEB_001 · EXTRA_032 | Baja frecuencia ⇒ costes pequeños; fundamento académico; sustituye el filtro BTC por el propio activo | Pocas operaciones en 22 meses (potencia estadística baja) |
| 12 | **Filtro de régimen CHOP** (meta-prueba) | EXTRA_016 · indicador CHOP (REMIX/FUT/SPOT) | Contrasta si un filtro de régimen mejora S01–S04 **fuera de muestra**: base del motor adaptativo | Riesgo de sobreajuste; exigir mejora en OOS |
| 13 | **Pivotes Camarilla H3/L3** | FUT_S030 | Niveles calculados desde D1 previo; reglas fijas | Sensible al método de pivote |
| 14 | **Fuerza relativa entre majors FX** (adaptación) | EXTRA_012/013 · WEB_004 | Rediseño causal para universo FX; requiere descargar más símbolos | Condicional: ampliar datos |
| 15 | **CONTROL NEGATIVO: entradas aleatorias** (semilla fija) con mismo SL/TP/costes | FUT_S100 · SPOT_S200 | Mide el *piso* del simulador: debe dar R≈ −coste. Detecta sesgos del motor | — |
| 16 | **CONTROLES SIMPLES: MACD sin filtros y SMA 5/20** | FUT_S054, FUT_S086 | Líneas base de «estrategia ingenua»; si S01–S04 no las superan, no hay ventaja | — |

## Mantenidas aparte (no se evalúan con los datos actuales)
- **Order flow / footprint / CVD / delta** (p. ej. REMIX_S001–S020, FUT_S003/S004, EXTRA_019/020/026): requieren agresor real; el tick-volume de CFD **no** lo sustituye.
- **Gamma/GEX, opciones, CME, dark pool** (REMIX_S021–S040 aprox.): requieren fuentes externas con licencia.
- **Funding, Open Interest, liquidaciones, Long/Short ratio** (FUT_S019/S027/S037, SPOT_*): propios de perpetuos cripto.
- **Noticias**: el calendario está vacío (`exness_news_events.csv` solo cabecera).
- **ML/Lorentzian, ARIMA, GARCH, Kalman**: viables solo con protocolo de ajuste rolling y sin fuga; fase posterior.
- **SMC/ICT discrecional** (OB, FVG, BOS/CHoCH, Silver Bullet): exigen definición operativa causal antes de codificar; se pospone hasta cerrar 1–10.

## Orden de campaña (sin sobreoptimizar)
1. Resolver ejecución del Tester (T001) y paridad Python↔MT5 de S01.
2. Líneas base y controles (15, 16) sobre EURUSDm/XAUUSDm M15/H1, parámetros por defecto, solo en muestra.
3. Hipótesis 1–4 con parámetros predefinidos; luego 5–10.
4. Solo para las que no pierdan frente a los controles: rejilla acotada → walk-forward → congelar parámetros → **una** evaluación del *holdout* (jul–oct 2026).
5. Hipótesis 11–14 y meta-prueba de régimen (12) al final.

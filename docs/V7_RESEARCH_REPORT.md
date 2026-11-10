# REMIX V7 — Informe de investigación, lote 1 (2026-11-09)

Alcance: 10 mercados (EURUSDm, GBPUSDm, USDJPYm, XAUUSDm, XAGUSDm, US30m, US500m, USTECm, BTCUSDm, ETHUSDm — nombres exactos de Exness), velas M15 y H1 (H1 = remuestreo de M15), 2024-01 → 2026-10-31. Datos: `copy_rates_range` de la instancia aislada (`data/raw/v7/`, no se sincroniza). Todo es simulación en Python sobre datos históricos; no hubo órdenes de ningún tipo. Los datos de 2026-11-01 en adelante **no se tocaron** (reserva prospectiva).

## 1. Qué se hizo (ciclos 1–4 completos; 5–6 no procedían)
| Entregable | Contenido |
|---|---|
| `V7_MARKET_PROFILES.csv` | por mercado: barras, duplicados, huecos (>1 h, >1 día), gaps de apertura >2 ATR, spread real, coste/ATR, volatilidad diaria, asimetría, curtosis, autocorrelación 1/2/5, razón de varianza 4/16, eficiencia de tendencia, lote mínimo y contrato |
| `V7_SESSION_ANALYSIS.csv` | por hora UTC (servidor = UTC) y día de semana: retorno medio, volatilidad, spread/ATR, ER, tick volume |
| `V7_MARKET_REGIMES.csv` | 3×3 (volatilidad × tendencia): peso, probabilidad de que el momentum de 8 velas continúe, movimiento siguiente, coste/ATR |
| `V7_ENTRY_ANALYSIS.csv` (M15) y `_H1.csv` | 12 familias × 2 sentidos × 10 mercados × IS/OOS/ALL: n, continuación/reversión, retorno bruto y neto a 1/3/5/10/20/40 velas, MFE/MAE y tiempos, P(1R/1,5R/2R/3R), P(SL), expectativa neta en R para TP 0,5–3R, IC95, control aleatorio (misma hora y tercil de ER) |
| `V7_LIQUIDITY_RESEARCH*.csv` | barridas: distancia (terciles), reversión a 10 velas, expectativa, MFE, sesión |
| `V7_ROBUSTNESS_RESULTS*.csv`, `V7_STRATEGY_CANDIDATES*.csv`, `V7_EXPERIMENT_REGISTER*.csv` | las 2.200 pruebas registradas (1.200 M15 + 1.000 H1), regla de selección fijada de antemano, sensibilidad a costes ×1,5/×2/×3, clase A–G |
| `V7_FORWARD_RESULTS.csv`, `V7_PORTFOLIO_ANALYSIS.csv`, `V7_MT5_OFFICIAL_RESULTS.csv` | corte temporal IS→OOS, correlaciones de mercado, resultados oficiales MT5 recuperados de V5 |
| `DAILY_PROFITABILITY_ANALYSIS.csv` + `V7_DAILY_SUMMARY_V5_RUNS.csv` | rentabilidad diaria con informes oficiales (ver informe de rentabilidad) |

Familias: barrida del máximo/mínimo del día previo y de 96 velas; ruptura Donchian 48 (inmediata) y ruptura + retest; momentum 8 velas (>3 ATR, ER>0,6); expansión tras compresión; reversión SOLO en régimen de rango (ER30<0,2 y RSI<20/>80, no el Z-Score de V5); FVG (hueco ≥0,3 ATR, entrada al retorno); BOS y CHoCH (pivotes confirmados 3 velas después, sin look-ahead); Opening Range de Londres (08:00 UTC) y Nueva York (14:00 UTC, solo M15). Cada una se evalúa en su sentido y en el invertido. Order Blocks no se implementaron (no hay definición matemática única que no sea arbitraria); order flow: no hay profundidad de mercado en el servidor, no se inventó.

Convenciones sin look-ahead: señal al cierre de la vela *i*, entrada en la apertura de *i+1*, coste = spread real de esa vela (ida y vuelta ≈ 1 spread; Exness Standard sin comisión), SL de medición 1 ATR(14) conocido en *i*, si SL y TP caen en la misma vela se cuenta el SL.

## 2. Perfil de mercado (hechos medidos)
- **Coste por operación / ATR(M15) mediana**: XAUUSD 0,039 (el más barato), US30 0,072, USTEC 0,075, USDJPY 0,098, US500 0,127, BTC 0,091, GBPUSD 0,151, EURUSD 0,164, ETH 0,175, **XAGUSD 0,403 (inviable en M15)**. En H1 el coste medio baja a 0,084 ATR (de ≈0,19).
- **Razón de varianza a 16 velas** < 1 en Forex/metales/índices US (0,93–0,99; ligera reversión, de tamaño menor que el coste); ≈1,0 en USTEC/ETH. Autocorrelación a 1 vela: −0,015 a −0,025 en EURUSD, GBPUSD, US30, US500; ≈0 en el resto. Eficiencia de tendencia media 0,18–0,21 en todos (mercados dominados por ruido a 30 velas).
- Calidad de datos: sin duplicados relevantes; Forex/metales/índices con 151 huecos >1 día (fines de semana) y 36–99 gaps de apertura >2 ATR por mercado; BTC/ETH sin huecos. El terminal limita a 100.000 barras: BTC/ETH empiezan el 2024-01-03.
- Correlación diaria: US500–USTEC 0,95, US30–US500 0,89, BTC–ETH 0,82, XAU–XAG 0,81, EUR–GBP 0,81; USDJPY correlaciona −0,56 con EURUSD. Diversificar entre índices US o entre cripto es casi inexistente.

## 3. Resultado principal
**Ninguna de las 2.200 combinaciones supera el umbral de múltiples pruebas (t\* = 3,92) ni alcanza la clase A/B.** Detalle en `V7_VALIDATION_REPORT.md`.
- El retorno **bruto** medio por evento es ≈ 0 en las 12 familias (−0,06 a +0,07 R a 1,5R); el coste (0,11–0,25 ATR en M15) lo convierte en −0,09…−0,28 R neto. El control aleatorio condicionado (misma hora y régimen) rinde −0,19 R: los patrones no superan al azar.
- Probabilidad de continuación a 10 velas: 0,47–0,53 en todas las familias.
- M15: 2 % de las pruebas con expectativa neta IS > 0; mejor t_IS = 1,09. H1: 10 % positivas; mejor t_IS = 2,18 (esperable por azar entre 1.000 pruebas).

## 4. Dónde parecen estar las mejores entradas (solo pistas, no ventajas)
1. **XAUUSDm H1, ruptura de 96 velas con cierre fuera (barrida seguida, operada en continuación), TP 1,5R–3R**: IS +0,22/+0,30 R (t 2,18/2,04; n=161), OOS +0,14/+0,24 R (t 1,46/1,66; n=159). Mismo comportamiento en IS y OOS pero **no pasa la corrección por pruebas** (t\*=3,72), el OOS ya estaba visto en V4/V5 y las dos filas son el mismo conjunto de operaciones con distinto TP. Clase C. Se congela como hipótesis prospectiva (`research/V7_STRATEGY_CANDIDATES_H1.csv`).
2. XAUUSD tiene el menor coste relativo de los 10 (0,039 ATR en M15): es el mercado donde un efecto pequeño tiene más opciones de sobrevivir al coste.
3. USTECm FVG (M15) y XAUUSDm ORB Londres invertido muestran OOS positivo (t 2,59 y 2,06) pero IS **negativo** (t −2,42 y −1,23): inestabilidad temporal, no ventaja (clase C).
(Nota: en M15, 60 de las 65 pruebas con OOS positivo tenían IS ≤ 0.)

## 5. No realizado en este lote (declarado)
Backtests oficiales MT5 nuevos (ningún candidato superó la regla de selección, por lo que construir un EA habría sido optimizar sobre ruido); optimización completa/genética/forward de MT5; ticks reales; test de esfuerzo; M5; ML (no hay señal bruta que modelar: se justificaría con información incremental demostrada); efectos de calendario macro (no hay fuente histórica verificable disponible); comparación de modos de entrada (limit/retroceso); SL/TP dinámicos y trailing; análisis de pérdidas por operación (el estudio es de eventos, no de operaciones de un EA); recuperación tras pérdidas; Order Blocks y order flow.

Reproducir: `python research/v7_download.py` → `python research/v7_event_study.py` (`V7_TF=H1` para el lote 2) → `python research/v7_select.py` → `python research/v7_misc.py`.

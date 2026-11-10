# V9 — Informe de estrategia de scalping

**Resultado: no existe una estrategia de scalping candidata.** Ninguna de las 500 pruebas (10 familias × primario/invertido × 5 RR × XAU M1/M5 + EURUSD/GBPUSD/USTEC M5) supera la regla de selección fijada antes de mirar los datos, y la única de clase C (XAU M5 `G_SESSION_ORB` TP 3R) falla en la validación 2026 (−0,11 R). No se construyó un EA de scalping "ganador" porque no hay hipótesis con evidencia; hacerlo habría sido ajustar ruido.

## Definiciones reproducibles (`research/v9_scalp_study.py::families`)
| Fam. | Regla (información ≤ cierre de la vela de señal) | Primario |
|---|---|---|
| A momentum | cierre − cierre[−3] > 2 ATR y rango de la vela > 1,2 ATR | continuación |
| B ruptura | primera vela que cierra fuera del rango de 30 velas | continuación |
| C barrida | extremo de 60 velas superado en > 0,1 ATR y cierre dentro | reversión |
| D reversión | \|z(20)\| > 2,5 con ER30 < 0,3 | fade |
| E pullback | SMA20>SMA50 y cruce de vuelta sobre SMA20 tras tocarla | con tendencia |
| F expansión | rango > 2 ATR(prev) tras 5 velas con rango medio < 0,7 ATR | dirección de la vela |
| G sesión | ruptura del rango de los primeros 15 min de Londres (08:00) / NY (13:30 UTC), primer cierre fuera en las 2 h siguientes | continuación |
| H multi-TF | B alineada con tendencia M15 (última vela M15 **completada**) | continuación |
| I ruptura+retest | tras B, retorno al nivel en ≤ 10 velas y cierre de nuevo fuera | continuación |
| J rango | ER30 < 0,15 y anchura < 3 ATR; extremos 15 % | fade |

## Por qué fallan (medido)
1. **El coste es del tamaño del movimiento.** Coste/ATR: XAU M1 0,166, XAU M5 0,070 (H4: 0,009). Un scalper necesita un retorno bruto > 0,07 ATR por operación en M5 (0,17 en M1); el bruto medido es −0,015…+0,014 R.
2. Sin dependencia serial (autocorrelación ≈ 0, razón de varianza 0,987–1,013).
3. La condición "mejor momento" (sesión, impulso, tick volume, spread bajo) no crea ventaja: los terciles de impulso, aceleración, rango/ATR, volumen de ticks, volatilidad previa, compresión y spread no producen expectativa neta positiva sostenida (`V9_MOMENTUM_ANALYSIS.csv`; cada celda cuenta como comparación, ~5 % saldrán significativas por azar).
4. La confirmación/retroceso no mejora la expectativa: confirma lo que ya no queda por ganar.

## Posiciones múltiples, cesta, cobertura
Probadas con simulador de cuenta compartida (`V9_BASKET_TRADING.csv`). No transforman una expectativa negativa en positiva (M5: −284 a −2.029 USD en todas las políticas). La cesta sin SL individual esconde pérdidas flotantes (DD 31–69 % en M5; 24 % en H4 frente a 6,9 %). La cobertura no recupera nada y paga un segundo spread.

## Control oficial en MT5
M5 B_BREAKOUT, cada tick: **−1.467,78 USD, PF 0,91, DD 50 %, 7.237 operaciones** (≈ 9,8 al día). Confirma en el probador lo que predijo el estudio de eventos.

## Lo que sí se concluye
El camino de scalping en XAU con spread de $0,16 y las familias probadas **no tiene ventaja bruta**; M5 es menos malo que M1 sólo porque el coste relativo es menor. Las hipótesis negativas quedan registradas para no repetirse.

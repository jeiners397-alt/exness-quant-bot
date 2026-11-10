# V10 — Auditoría de la línea XAUUSD H4 (congelada)

Definición congelada (sin optimizar): XAUUSDm H4, primera vela que cierra fuera del rango de 20 velas (continuación), SL 1 ATR(14), TP 3R, cooldown 6, hold máx. 40, lote 0,01. EA `REMIX_V8_XAU_BREAKOUT.mq5` SHA-256 `430a8976…` verificado. Datos: `research/V10_XAU_H4_AUDIT.csv`, `V10_XAU_H4_DIRECTIONAL_ANALYSIS.csv`. Código: `research/v10_h4_audit.py`.

## 0. Integridad de los datos de las 248 operaciones (hallazgo técnico, clase E)
- El `trades.csv` oficial (hash verificado contra `XAU_FROZEN.json`) **empareja cierre↔apertura por orden (FIFO)**. Cuando dos posiciones coinciden, cruza hora y precio de cierre entre ellas: **43 de 248** horas de cierre difieren del registro del propio EA (`ea_trades.csv`, clave `position_id`). Ejemplo: la posición 23 (compra 2024-02-20) se cerró por SL el 22-feb; `trades.csv` se lo asigna a la 22.
- El neto (2.172,77 USD) y el recuento (248) **no cambian**; sí cambian atributos por operación (duración, fecha de cierre, R individual).
- V10 usa `ea_trades.csv` y lo concilia con el oficial: neto idéntico (±0,02 USD), 248 aperturas idénticas. Consecuencia: la rentabilidad diaria de V9 para H4 por fecha de cierre se recalcula en V10 (`V10_DAILY_PROFITABILITY.csv`; diferencia pequeña: la media diaria sigue en 0,070 %).

## 1. Resultado global (oficial MT5)
n 248 · neto +2.172,77 USD · PF 1,57 · acierto 33,5 % · ganancia media +72,02 / pérdida media −23,06 · expectativa +0,297 R (t 2,51) · DD de balance 390 USD (10,8 %), DD de equidad 8,4 %.
Bootstrap por bloques (8 op., 4.000 rep.): IC95 de la expectativa [+0,065; +0,543] R, P(exp ≤ 0) = 0,006; IC95 del PF [1,15; 2,09].

## 2. Los 20 puntos pedidos
| # | Aspecto | Resultado |
|---|---|---|
| 1 | Año | 2024: 86 op., +381 USD, +0,28 R (t 1,41) · 2025: 95 op., +362, +0,12 R (t 0,64) · **2026: 67 op., +1.429, +0,57 R (t 2,38)** |
| 2 | Mes | 56 % de los 34 meses positivos; mejor mes 2026-01 (+661 USD = 30 % del neto); **3 mejores meses = 80 % del neto**; sin ellos (2026-01, 2026-03, 2025-10) el neto cae a +432 USD |
| 3 | Dirección | LONG 162 op. +1.304 USD, +0,36 R (t 2,40), PF 1,54 · SHORT 86 op. +868, +0,19 R (t 0,94), PF 1,27. Diferencia LONG−SHORT: t 0,69 (no distinguible). SHORT por tramo: DEV +44, SEL −233, **VAL +1.057** |
| 4 | Régimen (ER30) | bajo +0,33 R · medio +0,21 · alto +0,38: sin patrón |
| 5 | Volatilidad (ATR/precio) | bajo +0,09 R (t 0,5) · **medio +0,49 (t 2,3)** · alto +0,31: no monótono |
| 6 | Sesión de entrada (UTC) | 08–12: +0,91 R (n 33, t 2,6) · 04–08: +0,53 · 20–24: +0,41 · **12–20 (n 127): +0,06 y +0,04 R** · 00–04: +0,24 |
| 7 | Tras noticias (24 h tras NFP/CPI/FOMC) | 25 op.: −0,05 R · resto 223 op.: +0,34 R (diferencia no significativa) |
| 8 | Duración | las pérdidas duran poco (≤1 d: −0,29 R) y las ganancias más (1–3 d: +0,95; >3 d: +0,98). **Sesgo de resultado: la duración se conoce después; no es un filtro.** |
| 9–10 | MFE / MAE | MFE medio 1,55 R, MAE medio 0,78 R; 54 % alcanzó ≥1 R a favor y el 31,5 % de las perdedoras llegó a ≥1 R antes del SL |
| 11 | Distancia del SL | tercil bajo (SL pequeño): −0,004 R (24 USD en 83 op.); medio +0,49; alto +0,41 |
| 12–13 | Spread / costes | spread pagado 48 USD (1,1 % del R medio); **swap −133,5 USD (casi 3× el spread)**; con spread ×3 el neto sería +2.077 (PF 1,54): el coste de ejecución no explica nada |
| 14–15 | Mayor ganadora / perdedora | +276,58 USD (12,7 % del neto) / −80,97 USD |
| 16 | Outliers | sin las 3 mejores: +1.556 (PF 1,41) · sin las 5: +1.254 (PF 1,33) · **sin las 10: +601 (PF 1,16)** |
| 17 | Rachas negativas | máx. 10 pérdidas seguidas (−244,5 USD) |
| 18 | Drawdown | 390 USD / 10,8 % (balance) |
| 19 | Recuperación | 51 días tras el peor DD; periodo máximo bajo el agua 178 días (48 operaciones) |
| 20 | Concentración temporal | ver 2; DEV+SEL (sin 2026): 181 op., +0,20 R (t 1,45), PF 1,28 |

Salidas: 164 SL (−3.801 USD), 81 TP (+5.937 USD, promedio +2,96 R), 3 por tiempo.

## 3. Dependencia de la tendencia (post hoc)
A favor de la tendencia de 50 días (cierre > media de 300 velas H4): 172 op., **+0,49 R (t 3,35), PF 1,79**; en contra: 60 op., −0,08 R (t −0,37), PF 0,90; 16 sin historial. Es una lectura retrospectiva sobre la misma muestra: **hipótesis de nueva generación** (contamina el histórico 2024-2026) y no se usa como filtro.

## 4. Lo que NO se afirma
Ninguna de estas asociaciones es causal. El tramo 2026 (oro en máximos, +87,7 % en el periodo) concentra la rentabilidad. La definición no se tocó. La evaluación decisiva (datos ≥ 2026-11-01) sigue pendiente.

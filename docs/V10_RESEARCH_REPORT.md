# REMIX V10 — Informe de investigación: ventaja económica y estadística en XAUUSD

Rama `feature/remix-v10-economic-edge-discovery` (desde `feature/remix-v9-scalping-discovery`). Instancia aislada `C:\REMIX_MT5_LAB\terminal` (terminal principal intacto); solo Python y Strategy Tester; sin `order_send`; EA V8 sin cambios (SHA-256 `430a8976…`).

## Fase 0 — continuidad
Baseline congelada verificada (`v9_preserve --verify`: OK); sin procesos del laboratorio residuales; EA y `trades.csv` oficiales con hash verificado; reserva ≥ 2026-11-01 sin usar; versiones anteriores y ramas conservadas.

## Respuesta corta
1. **No hay ventaja demostrada (ninguna clase A ni B).** Cinco hipótesis quedan en clase C (evidencia insuficiente), una en F (macro) y el resto D.
2. **La línea XAU H4 no es solo la tendencia del oro**: la dirección de la ruptura contiene información (invertida pierde −0,14 R; dirección aleatoria en las mismas barras +0,17 R vs +0,35 R; p ≈ 0,03 sin corregir) y tiene la mejor relación neto/DD de todas las referencias. **Pero** una entrada LONG aleatoria ya rinde +0,30 R en un oro alcista (+87,7 %), el DSR es ≈ 0 y el PBO 0,53, el 80 % del neto está en 3 meses y el 66 % en 2026. Sigue siendo clase C hasta evaluarla con datos ≥ 2026-11-01.
3. **El momentum de series temporales no añade información** (25 pruebas, ninguna en t\*), la macro no predice dirección (solo volatilidad ×2–4), y M15 con costes reales queda en ≈ 0 neto: +0,054 R en el mejor caso oficial (MT5 +656,97 USD, PF 1,13, t ≈ 1).

## Lotes
- **A — auditoría H4** (`docs/V10_XAU_H4_AUDIT.md`, `V10_BENCHMARK_COMPARISON.md`): 248 operaciones, hallazgo de emparejamiento FIFO en `trades.csv` (43 cruces), 20 dimensiones, 18 líneas de referencia/control.
- **B — momentum/volatilidad/regímenes** (`docs/V10_ECONOMIC_RESEARCH.md`): 38 + 12 + 5 pruebas; serie FRED guardada con hash.
- **C — macro**: 86 eventos (NFP 31, CPI 32, FOMC 23) con 4 controles cada uno; marcas de tiempo verificadas con el pico de volatilidad (horario de verano incluido); sin consenso → sin sorpresas.
- **D — M15**: coste/ATR 0,039; 22 pruebas; 0 candidatas; 1 control oficial MT5.

## Cifras
| | |
|---|---|
| Pruebas V10 / acumuladas / t\* | 86 / 3.805 / 4,06 |
| Backtests oficiales nuevos | 1 (M15 control); 3 preservados (H4 TP2/TP3, M5) |
| Mejor oficial H4 TP3 | 248 op., +2.172,77 USD, PF 1,57, DD eq. 8,4 %, +0,070 %/día |
| M15 control oficial | 1.077 op., +656,97 USD, PF 1,13, DD eq. 9,65 %, +0,020 %/día |
| DSR (N ≥ 54) / PBO | ≈ 0 / 0,53 |

## Siguiente investigación justificada
1. **Evaluación prospectiva de la definición H4 exacta** con datos ≥ 2026-11-01 (la reserva sigue intacta): es la única prueba que no puede estar sobreajustada.
2. Si se consigue una fuente verificable de consenso (Reuters/Bloomberg/FRED API con clave del usuario), repetir el estudio de anuncios con sorpresas estandarizadas.
3. Hipótesis de nueva generación a probar solo prospectivamente: VIX en alza, tendencia de 50 d, M15 alineada con H4 (registradas como contaminadas).
4. Ticks reales solo con la ventana ≈ 2026-05 en adelante.

## Archivos
`research/V10_*.csv` (14) · `docs/V10_*.md` (7) · `research/v10_*.py` (6 módulos + paridad) · `tests/test_v10.py` · `data/raw/v10/` (series FRED con hash, HTML del calendario FOMC).

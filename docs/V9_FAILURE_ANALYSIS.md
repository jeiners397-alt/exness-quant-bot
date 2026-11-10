# V9 — Análisis de fallos

## Resultados negativos
1. **Scalping XAU M1/M5: 0 candidatas en 500 pruebas.** Bruto ≈ 0 (−0,015…+0,014 R), neto −0,05…−0,32 R. Coste/ATR 0,166 (M1) y 0,070 (M5).
2. **EURUSD, GBPUSD, USTEC (M5):** coste/ATR 0,25–0,48 y neto −0,26…−0,48 R: peores que XAU. Sin candidatas.
3. **Rango (J):** el precio vuelve al centro en el 59–78 % de los casos pero rompe el rango casi siempre; neto negativo en los tres periodos.
4. **Sesión/ORB (G):** la "mejor" (M5 TP 3R) es DEV +0,03, SEL +0,07, **VAL −0,11**: sin ventaja.
5. **Confirmación y retroceso** no corrigen la expectativa; la cesta sin SL, la cobertura y las posiciones múltiples tampoco.
6. **Control oficial MT5 (M5 B_BREAKOUT, cada tick): −1.467,78 USD, PF 0,91, DD 50 %.**
7. **Ticks reales:** 12 muestras trimestrales de 5 min (subproceso, límite 100 s): solo las 3 más recientes (desde ≈ 2026-05) devolvieron ticks; las 9 anteriores `ERROR_DATOS`.

## Errores técnicos y su corrección
| Hallazgo | Efecto | Corrección |
|---|---|---|
| `MaxBars=100000` en el terminal aislado | V7/V8 solo veían 100 k barras (M1: 3 meses) | Elevado a 3 M en la instancia aislada (backup `.bak_v9`); caché mensual |
| Caché con archivos vacíos tras una descarga interrumpida | Falsa carencia de datos M1 anteriores a 2026-07 | Detectado por el recuento (91 k barras), purgado y re-descargado; no se escriben archivos vacíos |
| `download_info.json` sobrescrito al descargar otros símbolos | KeyError del estudio | Ahora se fusiona |
| Enfriamiento global (`V.COOL`) cambiado al importar el módulo de scalping | Baseline H4 con 196 señales (+2.557 USD, "mejor" que MT5) en vez de 246 | Se fija `V.COOL = 6` explícitamente con aserción; test |
| Paridad M5 con redondeo horario (`floor("1h")`) | 8 % de coincidencias falsas | `FLOOR` por TF (`5min`), 97,2 % |
| Simulador de cestas ≈ 30 % más optimista que MT5 en H4 (+2.102 vs +1.623) | Sobreestima el beneficio absoluto | Se usa solo para diferencias relativas; documentado |
| Terminal aislado residual impide nuevos tests | `SIN_INFORME` | Se detiene solo ese PID (ruta bajo `C:\REMIX_MT5_LAB`) |
| `copy_ticks_range` se cuelga | Bloqueaba la sesión | Subproceso con límite de tiempo + terminación del proceso aislado |

## Para no repetir
Familias A–J de scalping con estas definiciones en XAU M1/M5; ORB en M1; rango/fade en M1; cestas sin SL; cobertura del perdedor.

## Siguientes hipótesis justificadas (no ejecutadas)
(a) Reserva prospectiva ≥ 2026-11-01 sobre la referencia XAU H4 congelada (≈ 6 meses); (b) M15 en XAU (coste/ATR ≈ 0,039) como puente entre scalping y H1, con la misma metodología DEV/SEL/VAL; (c) ticks reales si se logra una fuente verificable.


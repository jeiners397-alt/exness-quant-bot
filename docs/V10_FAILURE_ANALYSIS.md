# V10 — Análisis de fallos y resultados negativos

## Resultados negativos (también registrados en `V10_EXPERIMENT_REGISTER.csv`)
1. **Momentum (25 pruebas TSMOM en D1/H4/H1/M15):** sin significación a t\* = 4,06; 24/25 con |t| < 2; efectos de 0,01–0,09 σ del orden del coste. La única con |t| ≥ 2 (M15 L=16 h=96) es lo esperado por azar.
2. **Reversión tras extremos:** H1 y M15 sin efecto; H4 y D1 con n < 100.
3. **Momentum condicionado por volatilidad y eficiencia:** sin diferencias.
4. **Regímenes económicos** (tasa real, nominal, inflación implícita, dólar, VIX con retardo 2 d): ninguna relación estable con el retorno futuro del oro a 5 días.
5. **Noticias (NFP/CPI/FOMC):** la volatilidad se multiplica por 2–4, pero la dirección no es predecible con la información disponible; estrategias de continuación/reversión sobre T+15 min: −0,24 y +0,08 ATR (n = 86, t ≈ 0).
6. **XAU M15 (22 pruebas):** 13 D, 3 C, 6 F; ninguna candidata. Las versiones invertidas pierden en todos los casos; el pullback, la compresión y el rango asiático no superan el coste (0,039 ATR).
7. **Control oficial MT5 M15 (ruptura 96):** +656,97 USD, PF 1,13, pero t ≈ 1 y DEV negativo (−0,005 R): no es candidata.
8. **DSR y PBO de la línea H4:** DSR ≈ 0 con N ≥ 54; PBO 0,53.
9. **Dependencia del oro:** una entrada LONG aleatoria a la misma hora ya rinde +0,30 R; la ruptura LONG (+0,44 R) no se distingue (p = 0,16).
10. **Sin consenso ni vintages:** no se pudo calcular ninguna sorpresa macro (clase F).

## Errores técnicos (clase E) y su tratamiento
| Hallazgo | Efecto | Corrección |
|---|---|---|
| `trades.csv` del probador empareja por orden (FIFO) y cruza cierres de posiciones solapadas (43/248 en H4) | atributos por operación incorrectos; totales correctos | V10 usa `ea_trades.csv` (`position_id`), conciliado con el neto oficial; documentado |
| `fred.stlouisfed.org`, `alfred…` y `bls.gov` inaccesibles desde el equipo (timeouts/403) | sin descarga directa | WebFetch con CSV bruto + SHA-256; fechas BLS por enlaces de archivo; sin ALFRED |
| Ventana de volatilidad previa incluía la barra del anuncio (primera ejecución: razón vol 0,8 < 1) | razón post/pre subestimada | corregida (retorno intra-barra, ventana [−60,0)); ahora 2,3–3,7 |
| Hueco de mercado (22–23 UTC) rompía la rejilla de 4 h tras el FOMC (19:00) | FOMC descartado en la primera ejecución | continuidad exigida solo en ±60 min; retorno a 4 h = NaN si cruza el cierre |
| Primera operación sin ATR en Python (historial más corto que el terminal) | R de una operación = NaN | riesgo desde el nivel SL del probador solo para esa operación |
| Etiqueta «contra tendencia» incluía operaciones sin historial (16) | n 76 en lugar de 60 | etiqueta «sin historial» separada |
| Sesgos de resultado: «duración» como variable | parece una señal fuerte (+0,95 R vs −0,29) | señalado como ex post; no se usa |

## Qué no se debe repetir
Familias A–J de scalping en M1/M5; ORB de sesión en M1; rango/fade en M1; cestas sin SL; cobertura del perdedor; filtros por «duración»; TSMOM con las mismas ventanas en H4 sin hipótesis nueva; interpretar el t de subconjuntos de las 248 operaciones como evidencia independiente.

## Limitaciones declaradas
Sin consenso/sorpresas; spread por barra (no capta el ensanchamiento en noticias); sin ticks reales antes de ≈ 2026-05; modelo OHLC 1 min; latencia no evaluada; 34 meses y un solo ciclo del oro (alcista +87,7 %); retornos H4 solapados corregidos con HAC pero con n efectivo bajo (D1 21 días ≈ 38 observaciones independientes).

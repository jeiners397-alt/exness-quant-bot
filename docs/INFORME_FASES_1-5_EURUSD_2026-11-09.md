# REMIX EURUSD — Informe de Fases 1–5 (2026-11-09)

Todo lo de aquí es **exploratorio**: ene-2025→oct-2026 ya fue observado (incluye jul–oct 2026). Ningún parámetro se ha seleccionado con estos datos. Evaluación prospectiva = datos posteriores a 2026-10-31 (aún no usados).
Total de pruebas registradas: 10 variantes de salida (barras) + 10 (ticks, mismas) + 31 ejecuciones S01–S04 → referencia de multiplicidad N≈41 (t máximo esperable bajo azar ≈ 2,73).

## 1. Informe definitivo de S01
- Oficial MT5 (3.000 USD, 0,5 %, estricto, EURUSDm M15, 335 operaciones): +140,50 USD, PF 1,065, expectativa **+0,029 R**, t = 0,52, IC95 (bloques) **[−0,09 ; +0,14] R**, DD de equidad 10,53 %.
- Descomposición: TP+SL = −173,91 USD (P(TP)=37,6 % < 40 % de equilibrio); las salidas horarias (117; verificadas en el código del EA y por hora 17:00:00–06) aportan +314,41 USD y son las operaciones supervivientes.
- Contra control aleatorio (200 sorteos, misma densidad de señales, SL/TP de la propia estrategia): control medio −0,043 R, percentil 95 = +0,060 R; S01 (+0,027 R) queda dentro (**p = 0,15**).
- Antes de costes S01 rinde +0,064 R/op; el spread cuesta 0,037 R/op.
- Datos: ticks reales solo desde 2026-01-01 (2025 generado); spread de ticks = 8 pts en 07–10 h, pero se ensancha en eventos (22 pts a las 12:30:01 del 2026-07-14). Comisión/swap: 0 en el Tester (no demostrado para la cuenta real).
- **Clasificación: SIN VENTAJA DEMOSTRADA — estrategia de referencia (control del laboratorio), no candidata.**

## 2. Variantes de salida con ticks reales (153 ops de 2026; entradas fijas)
V0 en ticks reproduce el oficial: 153/153 motivos, hora de salida ±2 s en 147/153, ΣR 11,42 vs 11,45 oficial, |ΔR| máx 0,016.

| Var. | Exp R | Δ vs V0 | IC95 Δ | t |
|---|---:|---:|---|---:|
| V0 | +0,075 | — | — | — |
| V1a BE +0,5R | −0,011 | −0,086 | [−0,189 ; +0,001] | −1,75 |
| V1b BE +1,0R | +0,083 | +0,008 | [−0,037 ; +0,039] | 0,39 |
| V2a trail ATR×1,5 | +0,056 | −0,018 | [−0,095 ; +0,028] | −0,55 |
| V2b trail ATR×2,5 | +0,073 | −0,002 | [−0,065 ; +0,038] | −0,05 |
| V3 trail estructural | +0,082 | +0,008 | [−0,054 ; +0,052] | 0,26 |
| V4a cierre 13 h | +0,001 | −0,073 | [−0,170 ; −0,004] | −1,47 |
| V4b cierre 15 h | +0,047 | −0,028 | [−0,077 ; +0,018] | −0,95 |
| V4c máx. 4 h | −0,061 | −0,135 | [−0,247 ; −0,067] | −2,30 |
| V4d sin continuación | +0,045 | −0,030 | [−0,121 ; +0,045] | −0,71 |
| V5 parcial 50 % | +0,064 | −0,011 | [−0,047 ; +0,007] | −0,55 |

Ninguna mejora supera el ruido (las dos «positivas» son +0,008 R con IC que contiene cero y cambian de signo por dirección). La latencia de 1 s en la gestión cambia el resultado como mucho 0,003 R; 10 puntos de slippage en stops restan ≈0,02 R a todas. Con ticks reales y a barras (conservador) la conclusión es la misma. **S01 se clasifica como referencia; no se continúa con ajustes.** Archivos: `research/S01_EXIT_VARIANTS_TICKS_*`.

## 3. Paridad Python–MT5 (S01, 3.000 USD, EURUSDm M15, 335 operaciones)
| Elemento | Resultado |
|---|---|
| Señales (fecha/hora de entrada) | 335/335 coinciden, sin extras en ninguno |
| Dirección | 335/335 |
| Precio de entrada | 335/335 idéntico (ask = open + spread de barra) |
| Distancia SL | diferencia mediana 0,0 pts |
| Distancia TP | diferencia mediana 0,5 pts |
| Volumen | 335/335 idéntico (cadena propia de Python y fórmula con el balance de MT5) |
| Motivo de cierre | 335/335 |
| Hora de salida | mediana −2,35 min (Python sale a la apertura de la barra; MT5 en el tick): modelado intrabarra |
| R por operación | |Δ| mediano 0,000; p95 0,012 |
| ΣR / PnL | MT5 9,86 R / +140,50 USD; Python 9,12 R / +129,38 USD |

Diferencias y causas: (a) **1 operación explica casi todo el hueco** — 2026-07-14, TP a 1,14243 pero MT5 rellenó a 1,14411 (+0,92 R) porque el precio saltó 1,14092→1,14411 en 45 ms con spread de 22 pts (evento de noticias 12:30:01): causa = datos/ejecución en salto, no error; (b) los SL en MT5 promedian −1,0045 R vs −1,000 en Python (relleno al tick, ≈0,5 pts); (c) hora de salida: modelado intrabarra; (d) 2025 sin ticks reales en el terminal: ese tramo MT5 usó ticks generados, así que la coincidencia de salidas en 2025 refleja el mismo orden conservador de barras, no verificación con ticks. Con repetición de ticks (2026) la paridad de salida es ±1 s.
**Límites de la afirmación:** verificado solo S01 en EURUSDm. **No** se declara equivalencia total: S02–S04 no se han ejecutado en el Tester (requiere ejecución manual del usuario), el ADX de Python (Wilder) no se ha contrastado con `iADX`, y la comisión de la cuenta no está verificada.
Archivos: `research/parity_python_mt5.py`, `PARITY_S01_PYTHON_MT5.json`, `PARITY_S01_TRADES.csv`.

## 4. S02, S03, S04 (EURUSDm; M15 y H1; 3.000 USD; 0,5 %; estricto)
Reglas verificadas con pruebas (`tests/test_rules_s02_s04.py`, `tests/test_lookahead.py`: la señal de la barra i no cambia al truncar el futuro; 36 pruebas pasan). Parámetros canónicos fijados a priori + vecindad de 4 variantes por estrategia/TF (sensibilidad, no selección).

| Estr. | TF | N | Win% | PF | Exp R neta | Exp R bruta | Coste R/op | IC95 Exp R neta | t | Neto USD | DD % | Trim. + | Vec.>0 | Control p |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|---|---:|
| S01 | M15 | 335 | 46,0 | 1,06 | +0,027 | +0,064 | 0,037 | [−0,09 ; +0,13] | 0,48 | +129 | 10,1 | 6/8 | — | 0,15 |
| S02 | M15 | 1799 | 37,2 | 0,87 | −0,079 | +0,000 | 0,080 | [−0,13 ; −0,02] | −2,77 | −1.473 | 53,3 | 0/8 | 0/4 | 0,17 |
| S02 | H1 | 490 | 37,6 | 0,88 | −0,077 | −0,035 | 0,042 | [−0,17 ; +0,03] | −1,39 | −471 | 17,8 | 2/8 | 0/4 | 0,59 |
| S03 | M15 | 345 | 30,4 | 0,85 | −0,106 | −0,011 | 0,095 | [−0,25 ; +0,02] | −1,40 | −492 | 22,3 | 0/8 | 0/4 | 0,49 |
| S03 | H1 | 101 | 26,7 | 0,71 | −0,205 | −0,151 | 0,054 | [−0,41 ; +0,03] | −1,55 | −283 | 11,8 | 2/8 | 0/4 | 0,85 |
| S04 | M15 | 1177 | 36,2 | 0,84 | −0,105 | −0,013 | 0,092 | [−0,17 ; −0,04] | −2,98 | −1.356 | 46,7 | 0/8 | 0/4 | 0,30 |
| S04 | H1 | 336 | 38,1 | 0,90 | −0,064 | −0,018 | 0,046 | [−0,19 ; +0,08] | −0,95 | −288 | 17,5 | 2/8 | 1/4* | 0,49 |

\* única variante vecina positiva de todo el bloque: S04 H1 `sq_ratio=0,6` (+0,037 R, n=233, t=0,45): ruido, 1 de 31 ejecuciones.
Lectura: **antes de costes S02–S04 rinden ≈ 0 R** (equivalen a entradas aleatorias con SL/TP en múltiplos de ATR); el spread (0,04–0,10 R/op, por SL cortos en M15) los vuelve negativos. Ninguna supera su control aleatorio (p 0,17–0,85; el control medio también es negativo, −0,06 a −0,12 R). Los resultados no dependen de una operación extrema (top-5 ≤ 5,5 % del beneficio bruto, salvo S03 H1 20 %, n=101). Operaciones registradas: `results/phase3_trades_*.csv`; todas las ejecuciones: `research/PHASE3_RUNS.csv`.
Las pérdidas «significativas» de S02/S04 M15 (t≈−2,8/−3,0) no son un hallazgo de ventaja inversa: coinciden con el control aleatorio.

## 5. Decisión de investigación
| Estrategia | Clasificación |
|---|---|
| S01 London Breakout | **Sin ventaja demostrada** (referencia/control). Única con bruto positivo (+0,064 R), no significativo |
| S02 Donchian+ATR | **Sin ventaja demostrada** (bruto ≈ 0, M15 y H1) |
| S03 EMA+ADX pullback | **Sin ventaja demostrada** (pocas operaciones: 345/101) |
| S04 Bollinger squeeze | **Sin ventaja demostrada** |
| Incompatible con los datos | Ninguna de las cuatro. Order flow/CME/gamma siguen fuera (no hay datos) |

Ninguna entra en REMIX EURUSD V1 en este momento. No hay candidata prometedora.
Observación para la siguiente línea de trabajo (no para forzar resultados): el único residuo positivo es la deriva horaria de S01 (+0,19 R en salidas de las 17 h, solo supervivientes) y el spread es el coste dominante en M15 — hipótesis de investigación: estrategias de baja frecuencia / H4–D1 donde el coste por R sea pequeño, y las candidatas P01–P16 de `research/PRIORITY_HYPOTHESES.md` (PDH/PDL, apertura NY, Keltner, momentum diario) con la misma metodología y controles.

## 6. Reproducción
```
python -I -W ignore research\s01_audit.py          # reconstruye 335 ops y R
python -I -W ignore research\s01_mae_mfe.py        # MAE/MFE
python -I -W ignore research\run_exit_variants.py  # variantes en barras
python -I -W ignore research\run_tick_variants.py  # variantes con ticks (necesita terminal MT5 abierto, solo lectura)
python -I -W ignore research\parity_python_mt5.py  # paridad
python -I -W ignore research\run_phase3.py         # S01-S04 + controles (seed 12345)
python -I -W ignore research\phase4_matrix.py      # matriz
python -m pytest -q                                # 36 pruebas
```
Semilla fija 12345. Datos: `data/raw/EURUSDm_{M15,H1}.csv` (SHA-256 en `backup/BACKUP_QUEUE.csv`), caché de ticks `data/raw/ticks_S01/` (no se sube).

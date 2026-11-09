# REMIX EURUSD — Fase D: informe de investigación (2026-11-09)

**Alcance:** solo simulaciones (Python + datos Bid/Ask de barras y ticks del terminal, solo lectura). Sin órdenes, sin `order_send`, EA original intacto, terminal sin cerrar.
**Estatus de los datos:** EXPL = 2025-01→2026-10 (**ya inspeccionado**: exploratorio). RETRO = historia **anterior a 2025**, no inspeccionada hasta esta fase: H1/H4/D1 2018–2024 y M15 nov-2022→2024. No se seleccionó ningún parámetro con RETRO; sirve como réplica retrospectiva, **no** como evaluación prospectiva. La evaluación prospectiva (datos posteriores a oct-2026) queda congelada y sin usar (`research/PROSPECTIVE_FREEZE_2026-11-09.json`, SHA-256 `83a1a3c9c35035b23678b4bab1220c7347240df65b341f2f29dd41045639493b`).

## 1. Resumen ejecutivo
- **Ninguna de las 100 configuraciones probadas alcanza la categoría «Prometedora».** 75 descartadas, 19 «no demostradas», 6 pendientes de datos.
- Multiplicidad: 100 configuraciones en esta fase (200 ejecuciones = EXPL+RETRO) más 41 de la Fase C → ≈141 hipótesis; t máximo esperable solo por azar ≈ **3.15**. El mayor t observado en EXPL (N≥30 operaciones) fue **1.26**: nada se distingue del azar tras corregir por pruebas.
- **Invertir señales no crea ventaja.** Las S02–S04 originales tienen rendimiento *bruto* ≈ 0 (±0,15 R); en M15 el coste (0,10–0,14 R por operación) explica casi toda la pérdida y **también** hunde a las versiones invertidas. Las pocas inversas positivas en EXPL (S03 H1, S04 H1) no se replican en RETRO.
- **Los costes sí son el obstáculo dominante en M15**; en H1/H4 pesan menos (0,02–0,06 R) pero el rendimiento bruto tampoco es positivo de forma fiable.
- **No hay candidatos para validar en MT5 todavía.** Solo 4 «pistas débiles» (positivas en EXPL y RETRO, sin significancia) quedan congeladas para evaluación prospectiva; el EA solo implementa S01–S04, y portar una pista al EA antes de que supere la prospectiva no está justificado.

## 2. Reglas de decisión (pre-registradas antes de ver resultados)
Prometedora: N≥100 en EXPL y RETRO; Exp R>0 en ambos; PF≥1,15 en ambos; Exp R sin las 5 mejores operaciones >0 en ambos; p de control aleatorio ≤0,10 en EXPL; ≥50 % de las variantes del grupo (estrategia, TF) con Exp R>0 en ambos periodos; ≥50 % de trimestres positivos. No demostrada: Exp R>0 en EXPL pero incumple algo. Descartada: Exp R≤0 en EXPL. Pendiente de datos: N<30 en algún periodo. (PF 1,30 es objetivo preferente; ninguna configuración con N≥100 en ambos periodos se acercó.)
Parámetros canónicos fijados a priori; las «variantes» son una rejilla pequeña y predefinida, no un barrido. Capital virtual 3.000 USD, riesgo 0,5 %, política estricta. Controles: 100 sorteos con misma densidad de señales, misma proporción LONG/SHORT, mismos pares SL/TP, mismo riesgo y mismas reglas temporales (no replican salidas por indicador).

## 3. Inversión de S02, S03 y S04 (EXPL: Exp R por variante)
A original · B invertida (SL/TP iguales) · B_swap (SL↔TP) · C solo largos · D solo cortos · E largos invertidos · F cortos invertidos. Cada inversión se reconstruye como operación completa (entrada al ask/bid correcto, SL/TP, tamaño por riesgo, spread, swap); jamás se multiplicó un resultado por −1.

| Estr. / TF | A_orig | B_inv | B_inv_swap | C_long | D_short | E_long_inv | E_long_inv_swap | F_short_inv | F_short_inv_swap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S02 H1 | -0.076 | -0.026 | +0.007 | -0.041 | -0.089 | -0.089 | -0.040 | +0.018 | +0.020 |
| S02 M15 | -0.079 | -0.074 | -0.051 | -0.085 | -0.082 | -0.093 | -0.045 | -0.078 | -0.049 |
| S03 H1 | -0.205 | +0.099 | +0.027 | -0.164 | -0.250 | +0.245 | +0.083 | -0.056 | -0.036 |
| S03 M15 | -0.106 | -0.135 | -0.044 | -0.113 | -0.098 | -0.156 | -0.056 | -0.115 | -0.032 |
| S04 H1 | -0.064 | +0.032 | -0.060 | -0.041 | -0.077 | -0.076 | -0.083 | +0.066 | -0.045 |
| S04 M15 | -0.105 | -0.053 | -0.046 | -0.163 | -0.060 | -0.019 | -0.002 | -0.105 | -0.080 |

Réplica en RETRO (mismas configuraciones, datos anteriores a 2025):

| Estr. / TF | A_orig | B_inv | B_inv_swap | C_long | D_short | E_long_inv | E_long_inv_swap | F_short_inv | F_short_inv_swap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S02 H1 | -0.038 | -0.057 | -0.044 | -0.066 | -0.030 | -0.001 | -0.027 | -0.096 | -0.041 |
| S02 M15 | -0.120 | -0.064 | -0.050 | -0.129 | -0.110 | -0.050 | -0.061 | -0.080 | -0.037 |
| S03 H1 | -0.146 | +0.006 | +0.000 | -0.152 | -0.143 | +0.114 | -0.000 | -0.062 | +0.000 |
| S03 M15 | -0.236 | +0.018 | +0.004 | -0.023 | -0.422 | -0.040 | -0.089 | +0.080 | +0.088 |
| S04 H1 | -0.062 | -0.060 | -0.024 | -0.094 | -0.012 | -0.013 | -0.009 | -0.088 | -0.044 |
| S04 M15 | -0.141 | -0.037 | -0.017 | -0.108 | -0.187 | -0.086 | -0.034 | -0.022 | -0.011 |

Lectura: B_inv en S03 H1 (+0,099 EXPL) → +0,006 en RETRO; S04 H1 (+0,032) → −0,060. Solo S03 H1 «largos invertidos» es positiva en ambos periodos (N=53 y 148; t=1,20 en EXPL; p control 0,14). Que la original pierda no implica que la inversa gane: la inversa paga los mismos costes.

## 4. Nuevas estrategias S05–S12 y tabla completa
S05 Z-score (H1/H4), S06 RSI-2+SMA100, S07 PDH/PDL (ruptura/barrida/retest; niveles solo del día anterior terminado), S08 Keltner, S09 momentum (D1 casi sin operaciones), S10 pullback EMA (H1 con filtro H4 sin lookahead), S11 Bollinger+RSI+ADX, S12 VWAP **proxy** (tick_volume; no es VWAP institucional) + pin bar. S09 D1 queda «pendiente de datos» (3–11 operaciones en EXPL). S12 pierde en ambos periodos (t=−2,9/−3,4 en EXPL); coste ≈0,19 R/op por SL de ~5,5 pips.

### 4.1 Tabla principal — nuevas estrategias (EXPL; réplica RETRO a la derecha)
| Estrategia | TF | Variante | N | WR % | PF | Exp R | DD % | IC95 (bloques) | t | p ctrl | RETRO: N / PF / Exp R | Decisión |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|---|
| S05 | H1 | max_bars: 48, trend_filter: false, z_th: 2.0 | 415 | 40.0 | 1.00 | -0.001 | 13.0 | [-0.13;+0.13] | -0.01 | 0.17 | 1615 / 0.84 / -0.077 | Descartada |
| S05 | H1 | max_bars: 48, trend_filter: true, z_th: 2.0 | 213 | 39.4 | 0.82 | -0.086 | 17.1 | [-0.24;+0.09] | -1.06 | 0.73 | 904 / 0.91 / -0.047 | Descartada |
| S05 | H1 | max_bars: 48, trend_filter: false, z_th: 2.5 | 245 | 37.1 | 0.88 | -0.038 | 13.8 | [-0.21;+0.12] | -0.45 | 0.40 | 979 / 0.87 / -0.067 | Descartada |
| S05 | H1 | max_bars: 48, trend_filter: true, z_th: 2.5 | 126 | 38.1 | 0.87 | -0.059 | 12.8 | [-0.28;+0.19] | -0.53 | 0.53 | 538 / 0.90 / -0.053 | Descartada |
| S05 | H4 | max_bars: 18, trend_filter: false, z_th: 2.0 | 95 | 47.4 | 0.81 | -0.084 | 4.9 | [-0.27;+0.08] | -0.82 | 0.70 | 373 / 1.05 / +0.028 | Descartada |
| S05 | H4 | max_bars: 18, trend_filter: true, z_th: 2.0 | 45 | 60.0 | 1.19 | +0.074 | 2.3 | [-0.20;+0.31] | +0.53 | 0.16 | 175 / 1.22 / +0.101 | No demostrada |
| S05 | H4 | max_bars: 18, trend_filter: false, z_th: 2.5 | 57 | 42.1 | 0.70 | -0.132 | 5.8 | [-0.40;-0.02] | -0.98 | 0.83 | 167 / 1.07 / +0.033 | Descartada |
| S05 | H4 | max_bars: 18, trend_filter: true, z_th: 2.5 | 28 | 57.1 | 1.21 | +0.116 | 2.5 | [-0.32;+0.29] | +0.57 | - | 80 / 0.92 / -0.034 | Pendiente de datos |
| S06 | H1 | rsi_hi: 90, rsi_lo: 10 | 476 | 61.8 | 1.05 | +0.015 | 8.4 | [-0.05;+0.08] | +0.47 | 0.08 | 1832 / 0.97 / -0.010 | No demostrada |
| S06 | H1 | rsi_hi: 95, rsi_lo: 5 | 225 | 62.2 | 0.95 | -0.007 | 5.5 | [-0.09;+0.08] | -0.17 | 0.30 | 938 / 0.95 / -0.015 | Descartada |
| S06 | H4 | rsi_hi: 90, rsi_lo: 10 | 123 | 65.9 | 1.17 | +0.036 | 1.6 | [-0.07;+0.13] | +0.63 | 0.22 | 435 / 0.99 / -0.001 | No demostrada |
| S06 | H4 | rsi_hi: 95, rsi_lo: 5 | 52 | 75.0 | 1.55 | +0.096 | 0.9 | [-0.02;+0.23] | +1.26 | 0.31 | 232 / 1.04 / +0.008 | No demostrada |
| S07 | M15 | mode: breakout, retest_lb: 12 | 452 | 39.4 | 0.89 | -0.063 | 20.8 | [-0.17;+0.05] | -1.16 | 0.47 | 619 / 0.78 / -0.129 | Descartada |
| S07 | M15 | mode: sweep, retest_lb: 12 | 432 | 37.5 | 0.85 | -0.082 | 19.3 | [-0.18;+0.01] | -1.52 | 0.49 | 592 / 0.88 / -0.075 | Descartada |
| S07 | M15 | mode: retest, retest_lb: 12 | 399 | 38.6 | 0.85 | -0.087 | 19.2 | [-0.20;+0.03] | -1.55 | 0.61 | 533 / 0.82 / -0.106 | Descartada |
| S07 | H1 | mode: breakout, retest_lb: 4 | 296 | 42.2 | 0.91 | -0.043 | 9.4 | [-0.16;+0.07] | -0.71 | 0.44 | 1319 / 0.87 / -0.070 | Descartada |
| S07 | H1 | mode: sweep, retest_lb: 4 | 248 | 41.9 | 0.90 | -0.040 | 10.8 | [-0.18;+0.09] | -0.63 | 0.36 | 1223 / 0.89 / -0.047 | Descartada |
| S07 | H1 | mode: retest, retest_lb: 4 | 216 | 38.4 | 0.75 | -0.127 | 16.2 | [-0.27;+0.01] | -1.89 | 0.88 | 1016 / 0.82 / -0.095 | Descartada |
| S08 | H1 | confirm: false, max_bars: 24, regime: false | 628 | 36.9 | 0.92 | -0.045 | 22.5 | [-0.15;+0.06] | -0.89 | 0.33 | 2588 / 0.88 / -0.059 | Descartada |
| S08 | H1 | confirm: false, max_bars: 24, regime: true | 300 | 35.7 | 0.89 | -0.065 | 19.7 | [-0.21;+0.09] | -0.89 | 0.48 | 1202 / 0.89 / -0.067 | Descartada |
| S08 | H1 | confirm: true, max_bars: 24, regime: false | 460 | 49.1 | 0.88 | -0.054 | 17.9 | [-0.14;+0.04] | -1.18 | 0.43 | 1931 / 0.81 / -0.087 | Descartada |
| S08 | H1 | confirm: true, max_bars: 24, regime: true | 166 | 47.6 | 0.80 | -0.099 | 11.0 | [-0.24;+0.07] | -1.32 | 0.59 | 692 / 0.80 / -0.097 | Descartada |
| S08 | H4 | confirm: false, max_bars: 12, regime: false | 141 | 44.0 | 0.92 | -0.047 | 5.3 | [-0.23;+0.13] | -0.51 | 0.44 | 593 / 0.96 / -0.010 | Descartada |
| S08 | H4 | confirm: false, max_bars: 12, regime: true | 60 | 50.0 | 1.36 | +0.122 | 2.3 | [-0.18;+0.42] | +0.84 | 0.11 | 251 / 1.03 / +0.037 | No demostrada |
| S08 | H4 | confirm: true, max_bars: 12, regime: false | 109 | 48.6 | 0.94 | -0.026 | 7.8 | [-0.24;+0.13] | -0.28 | 0.44 | 490 / 0.88 / -0.045 | Descartada |
| S08 | H4 | confirm: true, max_bars: 12, regime: true | 38 | 47.4 | 0.90 | -0.044 | 3.2 | [-0.35;+0.19] | -0.28 | 0.53 | 148 / 1.01 / +0.014 | Descartada |
| S09 | H4 | exit_mode: atr, mom_n: 20 | 79 | 40.5 | 1.30 | +0.193 | 5.1 | [-0.15;+0.56] | +1.16 | 0.05 | 322 / 0.84 / -0.119 | No demostrada |
| S09 | H4 | exit_mode: trend, mom_n: 20 | 97 | 20.6 | 0.92 | -0.001 | 6.2 | [-0.25;+0.16] | -0.01 | 0.41 | 345 / 0.78 / -0.066 | Descartada |
| S09 | H4 | exit_mode: atr, mom_n: 60 | 49 | 30.6 | 0.93 | -0.130 | 4.7 | [-0.48;+0.20] | -0.66 | 0.73 | 227 / 0.83 / -0.130 | Descartada |
| S09 | H4 | exit_mode: trend, mom_n: 60 | 99 | 22.2 | 1.06 | +0.021 | 4.0 | [-0.17;+0.17] | +0.19 | 0.43 | 359 / 0.81 / -0.048 | No demostrada |
| S09 | D1 | exit_mode: atr, mom_n: 20 | 9 | 33.3 | 0.95 | -0.034 | 1.7 | [+nan;+nan] | -0.07 | - | 35 / 1.35 / +0.168 | Pendiente de datos |
| S09 | D1 | exit_mode: trend, mom_n: 20 | 3 | 33.3 | 2.18 | +0.536 | 0.6 | [+nan;+nan] | +0.46 | - | 10 / 0.74 / -0.092 | Pendiente de datos |
| S09 | D1 | exit_mode: atr, mom_n: 60 | 11 | 27.3 | 0.64 | -0.203 | 2.0 | [+nan;+nan] | -0.48 | - | 30 / 1.12 / +0.066 | Pendiente de datos |
| S09 | D1 | exit_mode: trend, mom_n: 60 | 4 | 25.0 | 0.83 | -0.080 | 0.9 | [+nan;+nan] | -0.15 | - | 10 / 0.16 / -0.352 | Pendiente de datos |
| S10 | H1 | confirm: cross, htf: false | 269 | 33.1 | 0.97 | -0.019 | 7.4 | [-0.17;+0.12] | -0.22 | 0.26 | 1119 / 0.87 / -0.088 | Descartada |
| S10 | H1 | confirm: cross, htf: true | 166 | 31.9 | 0.92 | -0.049 | 8.0 | [-0.21;+0.13] | -0.45 | 0.42 | 752 / 0.84 / -0.117 | Descartada |
| S10 | H1 | confirm: structure, htf: false | 369 | 30.1 | 0.82 | -0.118 | 22.6 | [-0.24;+0.01] | -1.63 | 0.76 | 1421 / 0.93 / -0.036 | Descartada |
| S10 | H1 | confirm: structure, htf: true | 218 | 30.3 | 0.83 | -0.113 | 13.5 | [-0.25;+0.03] | -1.20 | 0.70 | 948 / 0.90 / -0.070 | Descartada |
| S10 | H4 | confirm: cross, htf: false | 67 | 20.9 | 0.50 | -0.377 | 13.6 | [-0.70;-0.11] | -2.52 | 0.98 | 236 / 1.06 / +0.043 | Descartada |
| S10 | H4 | confirm: structure, htf: false | 99 | 28.3 | 0.78 | -0.154 | 12.0 | [-0.41;+0.11] | -1.13 | 0.72 | 361 / 0.89 / -0.052 | Descartada |
| S11 | H1 | filt: false, max_bars: 24 | 281 | 44.5 | 0.99 | +0.002 | 6.2 | [-0.13;+0.14] | +0.03 | 0.19 | 1109 / 0.80 / -0.102 | No demostrada |
| S11 | H1 | filt: true, max_bars: 24 | 115 | 42.6 | 1.00 | +0.007 | 6.9 | [-0.16;+0.21] | +0.07 | 0.26 | 434 / 0.76 / -0.132 | No demostrada |
| S11 | H4 | filt: false, max_bars: 12 | 65 | 55.4 | 1.06 | +0.030 | 2.5 | [-0.19;+0.20] | +0.27 | 0.31 | 239 / 0.84 / -0.065 | No demostrada |
| S11 | H4 | filt: true, max_bars: 12 | 23 | 60.9 | 2.02 | +0.245 | 0.7 | [-0.01;+0.60] | +1.46 | - | 92 / 0.85 / -0.065 | Pendiente de datos |
| S12 | M15 | vwap_start: 0 | 536 | 34.3 | 0.78 | -0.148 | 34.4 | [-0.25;-0.05] | -2.92 | 0.20 | 625 / 0.80 / -0.130 | Descartada |
| S12 | M15 | vwap_start: 7 | 906 | 34.9 | 0.78 | -0.135 | 47.2 | [-0.21;-0.06] | -3.43 | 0.09 | 981 / 0.79 / -0.134 | Descartada |

### 4.2 Tabla principal — señales invertidas / subconjuntos de S02–S04 (EXPL; réplica RETRO)
| Estrategia | TF | Variante | N | WR % | PF | Exp R | DD % | IC95 (bloques) | t | p ctrl | RETRO: N / PF / Exp R | Decisión |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|---|
| S02 | M15 | A_orig | 1799 | 37.2 | 0.87 | -0.079 | 53.3 | [-0.13;-0.02] | -2.77 | 0.17 | 1888 / 0.81 / -0.120 | Descartada |
| S02 | M15 | B_inv | 1931 | 37.4 | 0.89 | -0.074 | 53.4 | [-0.13;-0.02] | -2.69 | 0.20 | 2072 / 0.90 / -0.064 | Descartada |
| S02 | M15 | B_inv_swap | 1825 | 57.3 | 0.87 | -0.051 | 38.9 | [-0.09;-0.01] | -2.64 | 0.18 | 1914 / 0.88 / -0.050 | Descartada |
| S02 | M15 | C_long | 1045 | 37.2 | 0.87 | -0.085 | 41.8 | [-0.16;-0.01] | -2.26 | 0.07 | 1155 / 0.81 / -0.129 | Descartada |
| S02 | M15 | D_short | 991 | 36.8 | 0.85 | -0.082 | 39.5 | [-0.15;-0.01] | -2.12 | 0.61 | 1036 / 0.81 / -0.110 | Descartada |
| S02 | M15 | E_long_inv | 1181 | 36.3 | 0.84 | -0.093 | 42.8 | [-0.16;-0.03] | -2.64 | 0.70 | 1353 / 0.92 / -0.050 | Descartada |
| S02 | M15 | E_long_inv_swap | 1057 | 57.3 | 0.88 | -0.045 | 23.0 | [-0.09;+0.00] | -1.77 | 0.34 | 1154 / 0.85 / -0.061 | Descartada |
| S02 | M15 | F_short_inv | 1168 | 37.6 | 0.89 | -0.078 | 47.4 | [-0.14;-0.01] | -2.19 | 0.04 | 1193 / 0.87 / -0.080 | Descartada |
| S02 | M15 | F_short_inv_swap | 1025 | 57.8 | 0.88 | -0.049 | 27.6 | [-0.10;-0.00] | -1.89 | 0.01 | 1057 / 0.90 / -0.037 | Descartada |
| S02 | H1 | A_orig | 490 | 37.6 | 0.88 | -0.076 | 17.8 | [-0.17;+0.03] | -1.39 | 0.54 | 1984 / 0.93 / -0.038 | Descartada |
| S02 | H1 | B_inv | 538 | 39.4 | 0.95 | -0.026 | 20.2 | [-0.13;+0.08] | -0.49 | 0.28 | 2260 / 0.88 / -0.057 | Descartada |
| S02 | H1 | B_inv_swap | 479 | 60.8 | 1.02 | +0.007 | 7.5 | [-0.05;+0.08] | +0.19 | 0.11 | 1988 / 0.89 / -0.044 | No demostrada |
| S02 | H1 | C_long | 256 | 39.5 | 0.93 | -0.041 | 14.6 | [-0.19;+0.12] | -0.53 | 0.15 | 1024 / 0.90 / -0.066 | Descartada |
| S02 | H1 | D_short | 269 | 36.4 | 0.88 | -0.089 | 11.5 | [-0.23;+0.03] | -1.21 | 0.90 | 1080 / 0.95 / -0.030 | Descartada |
| S02 | H1 | E_long_inv | 303 | 36.6 | 0.86 | -0.089 | 18.9 | [-0.22;+0.05] | -1.28 | 0.85 | 1244 / 0.99 / -0.001 | Descartada |
| S02 | H1 | E_long_inv_swap | 250 | 57.6 | 0.90 | -0.041 | 12.2 | [-0.15;+0.07] | -0.78 | 0.81 | 1045 / 0.92 / -0.027 | Descartada |
| S02 | H1 | F_short_inv | 301 | 41.5 | 1.02 | +0.018 | 8.4 | [-0.10;+0.15] | +0.26 | 0.03 | 1267 / 0.81 / -0.096 | No demostrada |
| S02 | H1 | F_short_inv_swap | 270 | 61.9 | 1.03 | +0.019 | 6.3 | [-0.07;+0.11] | +0.39 | 0.02 | 1076 / 0.90 / -0.041 | No demostrada |
| S03 | M15 | A_orig | 345 | 30.4 | 0.85 | -0.106 | 22.3 | [-0.25;+0.02] | -1.40 | 0.44 | 330 / 0.68 / -0.236 | Descartada |
| S03 | M15 | B_inv | 341 | 29.3 | 0.80 | -0.135 | 22.0 | [-0.26;+0.01] | -1.80 | 0.67 | 329 / 1.02 / +0.018 | Descartada |
| S03 | M15 | B_inv_swap | 335 | 64.5 | 0.88 | -0.044 | 7.4 | [-0.11;+0.03] | -1.08 | 0.40 | 328 / 1.00 / +0.004 | Descartada |
| S03 | M15 | C_long | 172 | 30.8 | 0.85 | -0.113 | 13.8 | [-0.32;+0.11] | -1.03 | 0.32 | 152 / 0.96 / -0.023 | Descartada |
| S03 | M15 | D_short | 173 | 30.1 | 0.85 | -0.098 | 16.5 | [-0.32;+0.09] | -0.94 | 0.66 | 179 / 0.47 / -0.422 | Descartada |
| S03 | M15 | E_long_inv | 167 | 28.1 | 0.77 | -0.156 | 13.7 | [-0.32;+0.02] | -1.49 | 0.91 | 155 / 0.93 / -0.040 | Descartada |
| S03 | M15 | E_long_inv_swap | 162 | 63.0 | 0.84 | -0.056 | 5.9 | [-0.16;+0.05] | -0.97 | 0.62 | 153 / 0.77 / -0.089 | Descartada |
| S03 | M15 | F_short_inv | 174 | 30.5 | 0.83 | -0.115 | 12.6 | [-0.30;+0.08] | -1.07 | 0.28 | 175 / 1.11 / +0.081 | Descartada |
| S03 | M15 | F_short_inv_swap | 173 | 65.9 | 0.90 | -0.032 | 4.9 | [-0.14;+0.08] | -0.57 | 0.10 | 176 / 1.31 / +0.088 | Descartada |
| S03 | H1 | A_orig | 101 | 26.7 | 0.71 | -0.205 | 11.8 | [-0.41;+0.03] | -1.55 | 0.85 | 380 / 0.78 / -0.146 | Descartada |
| S03 | H1 | B_inv | 103 | 36.9 | 1.16 | +0.099 | 7.0 | [-0.22;+0.45] | +0.69 | 0.12 | 385 / 1.00 / +0.005 | No demostrada |
| S03 | H1 | B_inv_swap | 102 | 68.6 | 1.09 | +0.027 | 2.5 | [-0.09;+0.16] | +0.39 | 0.16 | 375 / 0.98 / +0.000 | No demostrada |
| S03 | H1 | C_long | 53 | 28.3 | 0.74 | -0.164 | 6.1 | [-0.45;+0.06] | -0.88 | 0.66 | 149 / 0.78 / -0.152 | Descartada |
| S03 | H1 | D_short | 48 | 25.0 | 0.67 | -0.250 | 6.8 | [-0.56;+0.12] | -1.32 | 0.94 | 231 / 0.79 / -0.143 | Descartada |
| S03 | H1 | E_long_inv | 53 | 41.5 | 1.43 | +0.245 | 3.8 | [-0.09;+0.58] | +1.20 | 0.14 | 148 / 1.16 / +0.114 | No demostrada |
| S03 | H1 | E_long_inv_swap | 54 | 72.2 | 1.37 | +0.083 | 1.1 | [-0.03;+0.22] | +0.90 | 0.14 | 147 / 1.02 / -0.000 | No demostrada |
| S03 | H1 | F_short_inv | 50 | 32.0 | 0.90 | -0.056 | 5.3 | [-0.42;+0.31] | -0.28 | 0.31 | 237 / 0.90 / -0.062 | Descartada |
| S03 | H1 | F_short_inv_swap | 48 | 64.6 | 0.91 | -0.036 | 1.9 | [-0.23;+0.15] | -0.35 | 0.37 | 228 / 0.98 / +0.000 | Descartada |
| S04 | M15 | A_orig | 1177 | 36.2 | 0.84 | -0.105 | 46.7 | [-0.17;-0.04] | -2.98 | 0.21 | 1306 / 0.77 / -0.141 | Descartada |
| S04 | M15 | B_inv | 1287 | 38.0 | 0.92 | -0.053 | 31.5 | [-0.12;+0.01] | -1.56 | 0.04 | 1394 / 0.94 / -0.037 | Descartada |
| S04 | M15 | B_inv_swap | 1175 | 57.4 | 0.89 | -0.046 | 24.1 | [-0.09;-0.00] | -1.92 | 0.10 | 1315 / 0.96 / -0.017 | Descartada |
| S04 | M15 | C_long | 649 | 34.2 | 0.77 | -0.163 | 43.9 | [-0.25;-0.07] | -3.46 | 0.67 | 723 / 0.83 / -0.108 | Descartada |
| S04 | M15 | D_short | 606 | 37.6 | 0.89 | -0.060 | 19.5 | [-0.15;+0.04] | -1.22 | 0.20 | 630 / 0.70 / -0.187 | Descartada |
| S04 | M15 | E_long_inv | 705 | 39.3 | 0.96 | -0.019 | 17.3 | [-0.11;+0.08] | -0.42 | 0.06 | 801 / 0.87 / -0.086 | Descartada |
| S04 | M15 | E_long_inv_swap | 648 | 59.9 | 0.99 | -0.002 | 10.3 | [-0.07;+0.06] | -0.06 | 0.04 | 726 / 0.92 / -0.034 | Descartada |
| S04 | M15 | F_short_inv | 701 | 35.9 | 0.84 | -0.105 | 32.7 | [-0.19;-0.03] | -2.32 | 0.09 | 698 / 0.96 / -0.022 | Descartada |
| S04 | M15 | F_short_inv_swap | 618 | 55.5 | 0.82 | -0.080 | 23.8 | [-0.14;-0.02] | -2.39 | 0.19 | 641 / 0.97 / -0.011 | Descartada |
| S04 | H1 | A_orig | 336 | 38.1 | 0.90 | -0.064 | 17.5 | [-0.19;+0.09] | -0.95 | 0.54 | 1492 / 0.89 / -0.062 | Descartada |
| S04 | H1 | B_inv | 339 | 41.6 | 1.05 | +0.032 | 13.7 | [-0.11;+0.15] | +0.47 | 0.07 | 1582 / 0.90 / -0.060 | No demostrada |
| S04 | H1 | B_inv_swap | 335 | 56.7 | 0.87 | -0.060 | 13.4 | [-0.16;+0.02] | -1.32 | 0.71 | 1484 / 0.94 / -0.024 | Descartada |
| S04 | H1 | C_long | 169 | 39.6 | 0.93 | -0.041 | 11.0 | [-0.21;+0.16] | -0.42 | 0.17 | 772 / 0.84 / -0.095 | Descartada |
| S04 | H1 | D_short | 189 | 37.0 | 0.87 | -0.077 | 8.6 | [-0.23;+0.09] | -0.87 | 0.79 | 815 / 0.97 / -0.012 | Descartada |
| S04 | H1 | E_long_inv | 184 | 37.0 | 0.86 | -0.076 | 15.4 | [-0.25;+0.06] | -0.85 | 0.80 | 856 / 0.97 / -0.013 | Descartada |
| S04 | H1 | E_long_inv_swap | 169 | 55.0 | 0.81 | -0.083 | 9.4 | [-0.22;+0.05] | -1.30 | 0.93 | 775 / 0.99 / -0.009 | Descartada |
| S04 | H1 | F_short_inv | 206 | 43.2 | 1.10 | +0.066 | 6.6 | [-0.09;+0.21] | +0.76 | 0.02 | 890 / 0.84 / -0.088 | No demostrada |
| S04 | H1 | F_short_inv_swap | 190 | 57.9 | 0.90 | -0.045 | 6.7 | [-0.16;+0.06] | -0.75 | 0.33 | 819 / 0.88 / -0.044 | Descartada |

## 5. Costes (por qué S02–S04 pierden)
Coste ex-ante = (spread de la barra de señal + 2 pts de slippage estimado) / distancia SL: solo información disponible en la barra de señal (sin spreads futuros). Estrés = spread ×1,5 y 10 pts de slippage por lado.

| Estr. | TF | SL mediano (pips) | Coste est. (R) | % señales >0,05R | % >0,10R | Exp R base | Bruta (antes de costes) | Coste R/op | Exp R estrés | Exp R filtro 0,05R (N) | Exp R filtro 0,10R (N) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| S02 | M15 | 11.8 | 0.108 | 89 | 41 | -0.095 | +0.005 | 0.100 | -0.330 | -0.073 (291) | -0.100 (1298) |
| S02 | H1 | 24.7 | 0.046 | 31 | 2 | -0.065 | -0.022 | 0.043 | -0.168 | -0.094 (381) | -0.072 (485) |
| S03 | M15 | 9.7 | 0.144 | 95 | 55 | -0.158 | -0.040 | 0.118 | -0.404 | -0.054 (22) | -0.134 (184) |
| S03 | H1 | 18.1 | 0.060 | 73 | 4 | -0.205 | -0.151 | 0.054 | -0.277 | -0.012 (30) | -0.210 (98) |
| S04 | M15 | 9.5 | 0.132 | 96 | 59 | -0.142 | -0.018 | 0.124 | -0.403 | -0.263 (75) | -0.084 (621) |
| S04 | H1 | 21.5 | 0.052 | 44 | 2 | -0.058 | -0.009 | 0.049 | -0.174 | -0.061 (226) | -0.061 (335) |

- En M15 el SL mediano es 9,5–11,8 pips; el spread observado (≈8–9 pts) cuesta 0,11–0,14 R por operación y el 89–96 % de las señales supera 0,05 R. En H1 (SL 18–25 pips) el coste es 0,046–0,060 R.
- Antes de costes, S02/S04 rinden ≈0 R y S03 −0,04 a −0,15 R: **sin ventaja bruta que los costes destruyan**; no es «una ventaja que se pierde en fricciones».
- Los filtros 0,05R / 0,10R: reducen coste por operación pero eliminan la mayoría de señales (M15: 22–291 de 394–1.882) y **no producen Exp R positiva** en S02–S04; en nuevas estrategias M15 los resultados con filtro 0,05R tienen N=12–34 (no concluyentes). Los umbrales no se consideran óptimos ni validados.
- Estrés: M15 −0,33 a −0,40 R/op; H1 −0,17 a −0,28.
- Limitaciones: spread de barra (no por tick) en todo EXPL/RETRO; comisión/swap de la cuenta real no verificados; en RETRO se sustituyeron por la mediana 20 barras con spread=0 (datos inválidos) y se excluyeron 6074 barras H1 anteriores a 2018 (cobertura incompleta y spread=0).

## 6. Pistas débiles y comprobación adicional (300 controles; sin variar parámetros)
| Pista | Periodo | N | PF | Exp R | IC95 bloques | t | p control (300) | Exp R estrés |
|---|---|---:|---:|---:|---|---:|---:|---:|
| L1 S03 H1 LONG-invertidas | EXPL | 53 | 1.43 | +0.245 | [-0.09;+0.58] | +1.20 | 0.090 | +0.132 |
| L1 S03 H1 LONG-invertidas | RETRO | 148 | 1.16 | +0.114 | [-0.09;+0.34] | +0.95 | 0.083 | -0.093 |
| L2 S05 H4 z2.0 filtro ADX | EXPL | 45 | 1.19 | +0.074 | [-0.20;+0.32] | +0.53 | 0.206 | +0.002 |
| L2 S05 H4 z2.0 filtro ADX | RETRO | 175 | 1.22 | +0.101 | [-0.05;+0.26] | +1.26 | 0.020 | +0.038 |
| L3 S06 H4 RSI2 5/95 | EXPL | 52 | 1.55 | +0.096 | [-0.03;+0.23] | +1.26 | 0.229 | +0.042 |
| L3 S06 H4 RSI2 5/95 | RETRO | 232 | 1.04 | +0.008 | [-0.07;+0.08] | +0.17 | 0.379 | -0.037 |
| L4 S08 H4 Keltner regimen | EXPL | 60 | 1.36 | +0.122 | [-0.20;+0.40] | +0.84 | 0.110 | +0.027 |
| L4 S08 H4 Keltner regimen | RETRO | 251 | 1.03 | +0.037 | [-0.10;+0.16] | +0.52 | 0.083 | -0.027 |

Exp R por año:

| Pista | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L1 S03 H1 LONG-invertidas | +0.31 | +0.12 | +0.00 | +0.14 | +0.07 | -0.22 | +0.59 | +0.41 | +0.00 |
| L2 S05 H4 z2.0 filtro ADX | +0.64 | -0.18 | -0.16 | +0.15 | +0.15 | -0.05 | +0.16 | +0.04 | +0.11 |
| L3 S06 H4 RSI2 5/95 | -0.07 | -0.19 | +0.06 | +0.05 | -0.02 | +0.17 | -0.01 | +0.06 | +0.15 |
| L4 S08 H4 Keltner regimen | +0.33 | -0.28 | -0.07 | -0.12 | -0.01 | +0.28 | +0.02 | +0.04 | +0.24 |

Ninguna pista tiene IC95 que excluya el cero; con estrés de costes L1, L3 y L4 pasan a negativo en RETRO. L2 (S05 H4 z=2,0 con filtro ADX<25) es la más consistente (RETRO t=1,26, p control 0,02, positiva con estrés) pero son 14–33 operaciones/año; no supera el umbral de multiplicidad. **Clasificación: no demostrada.**

## 7. Robustez, outliers y probabilidades
`research/PHASE_D_ROBUSTNESS.csv` incluye por configuración: Exp R sin la mejor operación y sin las 5 mejores, PF sin las 5 mejores, peso de la mejor operación, ganancia/pérdida media y payoff, pérdidas consecutivas máximas, IC95 por bloques (5) e IC bootstrap iid, mitades temporales, LONG/SHORT, coste y estrés. No se eliminó ninguna operación del resultado oficial; los únicos datos descartados fueron objetivamente inválidos (H1 anterior a 2018, spread=0 reemplazado por la mediana) y están en `PHASE_D_META.json`. Win Rate no se usó para clasificar.

## 8. Indicadores nuevos
Implementados y verificados con pruebas (`tests/test_indicators_d.py`): RSI de Wilder, Z-score, Kaufman ER, Choppiness, pendiente de regresión, percentil de volatilidad, anchura de Bollinger, Hurst R/S, VWAP proxy. Solo RSI, Z-score y Bollinger/Keltner/ADX se usaron en reglas de entrada; KER, Choppiness, Hurst y percentil de volatilidad quedan disponibles para el clasificador de régimen pero **no se usaron** (no se añadieron por cantidad). Hurst R/S es un estimador ruidoso.

## 9. Validación en MT5 y paridad
Ninguna configuración justifica aún portarse al EA. S05–S12 no existen en el EA (solo S01–S04); la paridad Python–MT5 completa sigue limitada a S01 (Fase C). Indicadores nuevos: paridad con las funciones nativas de MT5 (`iRSI`, `iADX`…) **sin verificar**.

## 10. Estrategias
- **Descartadas (Exp R≤0 en EXPL):** S12 (ambos), S07 (las 6 variantes), S10 (todas), S08 H1 (todas) y H4 salvo regimen, la mayoría de S05/S09 y todas las inversiones M15 de S02–S04.
- **Prometedoras:** ninguna.
- **No demostradas / pistas débiles:** L1–L4 (§6) y algunas variantes H1/H4 con Exp R≈0 (S06 H1, S11).
- **Pendientes de datos:** S09 D1 (≤11 operaciones), S05 H4 z=2,5 con filtro, S11 H4 con filtro.

## 11. Costes y riesgos observados
Spread de barras 8–9 pts constante (en ticks 2026: 8 pts, ensanchándose a 22 pts en noticias); SL en M15 de 5–12 pips hace que el spread consuma 0,1–0,2 R; con 3.000 USD y 0,5 % el lote mínimo no limita (riesgo real mediano 0,46–0,48 %). Con 100 USD sigue sin ser viable (Fase 1). Los DD de S02/S04 M15 superan el 45 %.

## 12. Próximos pasos propuestos
1. Mantener congeladas L1–L4; acumular datos posteriores a oct-2026 y evaluar **una sola vez** con N suficiente.
2. Si se quiere más potencia estadística sin forzar: probar la misma metodología en otros símbolos solo con autorización (el usuario pidió exclusividad EURUSD).
3. Estudiar el clasificador de régimen (KER, Choppiness, percentil de volatilidad) con las reglas ya definidas, sin añadirlo a las estrategias hasta superar los controles.
4. No hay candidatos para pruebas en MT5 por ahora.

## 13. Archivos
`research/PHASE_D_ALL_RUNS.csv`, `PHASE_D_INVERSE_STRATEGIES.csv`, `PHASE_D_NEW_STRATEGIES.csv`, `PHASE_D_COST_ANALYSIS.csv`, `PHASE_D_ROBUSTNESS.csv`, `PHASE_D_JOINED.csv`, `PHASE_D_LEAD_CHECK*.csv`, `PHASE_D_META.json`, `PROSPECTIVE_FREEZE_2026-11-09.json`; código `remix_lab/{harness,strategies_d}.py`, `research/{run_phase_d,phase_d_build,phase_d_lead_check,phase_d_report}.py`, `scripts/05_fetch_history_pre2025.py`; pruebas `tests/test_{phase_d,indicators_d}.py` (60 pruebas en total). Reproducción: `python -I -W ignore research\run_phase_d.py` (≈25 min) → `phase_d_build.py` → `phase_d_lead_check.py` → `phase_d_report.py`. Semilla 12345.

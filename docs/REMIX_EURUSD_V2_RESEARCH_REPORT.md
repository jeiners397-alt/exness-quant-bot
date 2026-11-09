# REMIX EURUSD V2 — Informe de investigación y desarrollo (2026-11-09)

**Estado: NO existe ninguna estrategia aprobada para producción.** REMIX_EURUSD_V2.mq5 es un laboratorio experimental con negociación desactivada por defecto. Solo simulación / Strategy Tester. Sin `order_send`. Todo resultado sobre 2025-01→2026-10 es exploratorio (ya inspeccionado); 2018–2024 son réplicas retrospectivas; la evaluación prospectiva (datos posteriores a oct-2026, `PROSPECTIVE_FREEZE_2026-11-09.json`) no se ha tocado.

## 1. Resumen ejecutivo
- **Mejores hipótesis encontradas (ninguna demostrada):** L2 (S05 Z-score reversión H4 con ADX<25) y L1 (S03 largo invertido H1). Agrupando 2018–2026-10 (periodos retrospectivo + exploratorio): L2 221 operaciones, PF 1.22, expectativa +0.099 R, IC95 [-0.04; +0.24], p de control aleatorio 0.010, DD 5.3 %. El intervalo incluye el cero y t < t* de multiplicidad: **no demostrada**.
- **Aunque fuese real, la ventaja es económicamente mínima:** ≈25 operaciones/año × ~0,1 R × 0,5 % ⇒ ≈30 USD/año sobre 3.000 USD (≈1 %/año). No supera a V1 de forma que justifique un robot.
- **Por qué fallan las estrategias tradicionales en EURUSD (hallazgos medidos):** (1) el spread consume 0,11–0,14 R por operación en M15 (SL ≈10 pips) y 0,03–0,06 R en H1/H4; (2) el rendimiento *bruto* de seguimiento de tendencia y rupturas es ≈0 o negativo en 2018–2026; (3) las reversiones tienen probabilidad de acierto cercana al equilibrio sin costes; (4) los efectos horarios existen pero son ≤1,7 pb (≈0,2 pip) frente a un spread de ≈0,8–0,9 pip; (5) las diferencias entre periodos/regímenes son mayores que cualquier ventaja media.
- **Búsqueda de eventos:** 700 celdas (hipótesis × TF × régimen × k) con ordenación intrabarra tratada como cota (conservadora/optimista). 34 de 125 grupos con E>0 en TRAIN; 12 siguen >0 en VALID; 6 en EXPL; 1 cumple la regla básica; 0 prometedoras. La correlación entre la expectativa de TRAIN y la de VALID de lo seleccionado es 0.14: **la selección con datos pasados casi no predice los siguientes** (señal de que lo elegido es ruido). t* por multiplicidad ≈ 3.62; ninguna celda se acerca.

## 2. Auditoría de fases anteriores (Fase 0)
S01: PF 1,065, +0,029 R, t=0,52; S02–S04 negativos tras costes; Fase D: 100 configuraciones, 75 descartadas, 19 no demostradas, 6 pendientes de datos, 0 prometedoras. Las cuatro pistas L1–L4 siguen **congeladas sin modificar** (hash del pre-registro en `research/PROSPECTIVE_FREEZE_2026-11-09.json`). No se repitieron pruebas de fases anteriores; las nuevas son hipótesis independientes registradas por separado.

## 3. Diagnóstico y probabilidades (Fases 1 y 4)
Diseño: evento = señal al cierre de la barra; entrada a la apertura siguiente (ask para largos, bid para cortos); SL = 1,5×ATR14; barreras +0,5/+1/+1,5/+2/+3 R; horizonte 24 barras (H1) / 12 (H4); eventos separados ≥ horizonte/4 barras. Cuando SL y TP caen en la misma barra no se infiere el orden: se informa la cota conservadora (pierde) y la optimista (gana). Periodos: TRAIN 2018–2021 (estimación), VALID 2022–2024 (observada fuera de muestra, retrospectiva), EXPL 2025–2026 (ya inspeccionado).

### 3.1 Hipótesis falsable de ejemplo: reversión tras |z|≥2 (SMA/σ 50)
H1 (todas las condiciones de régimen):

| Periodo | k (R) | N | P(+kR antes de −1R) cons. [IC95 Wilson] | P opt. | P equilibrio sin coste | E cons. [IC95 bloques] | E opt. | coste/op (R) |
|---|---:|---:|---|---:|---:|---|---:|---:|
| TRAIN | 0.5 | 1010 | 0.625 [0.595;0.654] | 0.639 | 0.667 | -0.060 [-0.10;-0.02] | -0.039 | 0.054 |
| TRAIN | 1.0 | 1010 | 0.430 [0.400;0.460] | 0.435 | 0.500 | -0.116 [-0.18;-0.06] | -0.106 | 0.054 |
| TRAIN | 1.5 | 1010 | 0.337 [0.308;0.366] | 0.342 | 0.400 | -0.085 [-0.16;-0.01] | -0.072 | 0.054 |
| TRAIN | 2.0 | 1010 | 0.232 [0.207;0.259] | 0.236 | 0.333 | -0.109 [-0.20;-0.04] | -0.097 | 0.054 |
| TRAIN | 3.0 | 1010 | 0.121 [0.102;0.142] | 0.123 | 0.250 | -0.097 [-0.19;-0.01] | -0.089 | 0.054 |
| VALID | 0.5 | 745 | 0.680 [0.646;0.713] | 0.695 | 0.667 | +0.022 [-0.03;+0.07] | +0.044 | 0.047 |
| VALID | 1.0 | 745 | 0.479 [0.444;0.515] | 0.493 | 0.500 | -0.011 [-0.08;+0.06] | +0.015 | 0.047 |
| VALID | 1.5 | 745 | 0.357 [0.324;0.392] | 0.366 | 0.400 | -0.007 [-0.10;+0.07] | +0.017 | 0.047 |
| VALID | 2.0 | 745 | 0.251 [0.221;0.283] | 0.256 | 0.333 | -0.040 [-0.14;+0.05] | -0.024 | 0.047 |
| VALID | 3.0 | 745 | 0.128 [0.105;0.153] | 0.129 | 0.250 | -0.047 [-0.16;+0.05] | -0.042 | 0.047 |
| EXPL | 0.5 | 456 | 0.642 [0.598;0.685] | 0.675 | 0.667 | -0.034 [-0.10;+0.03] | +0.015 | 0.046 |
| EXPL | 1.0 | 456 | 0.476 [0.430;0.522] | 0.491 | 0.500 | -0.020 [-0.12;+0.07] | +0.011 | 0.046 |
| EXPL | 1.5 | 456 | 0.340 [0.298;0.385] | 0.346 | 0.400 | -0.021 [-0.13;+0.09] | -0.004 | 0.046 |
| EXPL | 2.0 | 456 | 0.228 [0.192;0.269] | 0.233 | 0.333 | -0.059 [-0.19;+0.06] | -0.046 | 0.046 |
| EXPL | 3.0 | 456 | 0.116 [0.090;0.149] | 0.116 | 0.250 | -0.053 [-0.18;+0.09] | -0.053 | 0.046 |

H4:

| Periodo | k (R) | N | P(+kR antes de −1R) cons. [IC95 Wilson] | P opt. | P equilibrio sin coste | E cons. [IC95 bloques] | E opt. | coste/op (R) |
|---|---:|---:|---|---:|---:|---|---:|---:|
| TRAIN | 0.5 | 353 | 0.654 [0.603;0.702] | 0.663 | 0.667 | -0.002 [-0.09;+0.08] | +0.010 | 0.025 |
| TRAIN | 1.0 | 353 | 0.428 [0.377;0.480] | 0.428 | 0.500 | -0.024 [-0.14;+0.10] | -0.024 | 0.025 |
| TRAIN | 1.5 | 353 | 0.289 [0.244;0.338] | 0.289 | 0.400 | -0.003 [-0.15;+0.14] | -0.003 | 0.025 |
| TRAIN | 2.0 | 353 | 0.178 [0.142;0.222] | 0.178 | 0.333 | +0.014 [-0.17;+0.18] | +0.014 | 0.025 |
| TRAIN | 3.0 | 353 | 0.062 [0.042;0.093] | 0.062 | 0.250 | +0.026 [-0.15;+0.22] | +0.026 | 0.025 |
| VALID | 0.5 | 284 | 0.658 [0.602;0.711] | 0.672 | 0.667 | +0.012 [-0.08;+0.10] | +0.033 | 0.025 |
| VALID | 1.0 | 284 | 0.489 [0.432;0.547] | 0.493 | 0.500 | +0.092 [-0.04;+0.21] | +0.099 | 0.025 |
| VALID | 1.5 | 284 | 0.313 [0.262;0.369] | 0.313 | 0.400 | +0.102 [-0.04;+0.24] | +0.102 | 0.025 |
| VALID | 2.0 | 284 | 0.190 [0.149;0.240] | 0.190 | 0.333 | +0.113 [-0.03;+0.26] | +0.113 | 0.025 |
| VALID | 3.0 | 284 | 0.088 [0.060;0.127] | 0.088 | 0.250 | +0.159 [-0.00;+0.34] | +0.159 | 0.025 |
| EXPL | 0.5 | 172 | 0.651 [0.577;0.718] | 0.674 | 0.667 | +0.008 [-0.10;+0.11] | +0.043 | 0.022 |
| EXPL | 1.0 | 172 | 0.424 [0.353;0.499] | 0.442 | 0.500 | +0.005 [-0.15;+0.16] | +0.040 | 0.022 |
| EXPL | 1.5 | 172 | 0.267 [0.207;0.338] | 0.279 | 0.400 | +0.002 [-0.17;+0.17] | +0.031 | 0.022 |
| EXPL | 2.0 | 172 | 0.151 [0.105;0.212] | 0.163 | 0.333 | -0.038 [-0.19;+0.14] | -0.003 | 0.022 |
| EXPL | 3.0 | 172 | 0.052 [0.028;0.096] | 0.052 | 0.250 | -0.008 [-0.18;+0.18] | -0.008 | 0.022 |

Lectura: a +1 R la probabilidad observada (≈43–49 %) queda por debajo o en el equilibrio sin costes (50 %) y el coste medio (0,02–0,05 R) la pone por debajo; la expectativa cambia de signo entre periodos. H4 fue positiva en VALID y ≈0 en EXPL: no hay persistencia. Intervalos de confianza: Wilson para probabilidades, bootstrap por bloques para la expectativa.

### 3.2 Expectativa conservadora media por familia (todas las variantes, k=1 R, régimen ALL)
| Familia | TF | TRAIN 2018-21 | VALID 2022-24 | EXPL 2025-26 |
|---|---|---:|---:|---:|
| A1 | H1 | -0.103 | -0.045 | +0.002 |
| A1 | H4 | -0.149 | +0.052 | -0.012 |
| A2 | H1 | -0.022 | -0.022 | -0.054 |
| A2 | H4 | -0.065 | -0.041 | +0.011 |
| A3 | H1 | -0.048 | -0.075 | -0.051 |
| A3 | H4 | -0.035 | +0.003 | +0.034 |
| A4 | H1 | -0.103 | -0.059 | +0.091 |
| A4 | H4 | -0.112 | -0.016 | +0.048 |
| B1 | H1 | -0.048 | -0.113 | -0.114 |
| B1 | H4 | -0.091 | -0.072 | -0.063 |
| B2 | H1 | -0.029 | -0.072 | -0.105 |
| B2 | H4 | -0.058 | -0.089 | -0.069 |
| B3 | H1 | -0.091 | -0.032 | +0.000 |
| B3 | H4 | -0.146 | -0.051 |  |
| B4 | H1 | -0.004 | -0.082 | -0.121 |
| B4 | H4 | +0.040 | -0.076 | -0.070 |
| C1 | H1 | -0.074 | +0.025 | -0.021 |
| C1 | H4 | -0.128 | +0.011 | -0.088 |
| C2 | H1 | -0.058 | -0.127 | -0.088 |
| C3 | H1 | -0.086 | -0.048 | -0.100 |
| E1 | H1 | -0.075 | -0.044 | -0.162 |
| E1 | H4 | -0.078 | -0.035 | -0.102 |
| E2 | H1 | -0.072 | -0.086 | +0.012 |
| E2 | H4 | -0.018 | -0.051 | +0.021 |

A reversión estadística · B continuación · C estructura · E comportamiento tras expansión. Sin familia con expectativa positiva y estable.

### 3.3 Sesiones y hora del día
`research/PHASE_E_HOURLY.csv`. Horas con efecto estadísticamente fuerte y de signo estable (11 h y 15 h negativas en los tres periodos; 20 h negativa solo en TRAIN/VALID; 22 h positiva), pero |media| ≤1,7 pb ≈ 0,2 pip por barra H1, al menos ~5 veces menor que el spread, y 20–22 h coincide con el rollover (liquidez mínima): no explotable. Es coherente con Breedon & Ranaldo (el efecto se consume en el spread).

## 4. Selección pre-registrada y robustez
Regla fijada antes de ver VALID/EXPL: por (hipótesis, TF, régimen) se elige el k con mayor expectativa conservadora en TRAIN (N≥100) y se evalúa en VALID y EXPL. Resultado: 34 de 125 grupos con E>0 en TRAIN; 12 siguen >0 en VALID; 6 en EXPL; 1 cumple la regla básica; 0 prometedoras.
La única celda que pasa la regla básica (reversión z≥2 en H4 con KER alta, k=3) tiene P(éxito) de ~6–9 % (perfil de lotería), t_VALID=2,09 < t*=3.62, y sus vecinas (z=1,5/2,5/3,0, otros k) cambian de signo entre periodos: no es una región estable. Estadística completa: `PHASE_E_SELECTION.csv`.

## 5. Optimización controlada (Fase 5): región de parámetros de S05 H4 (18 configuraciones)
Motor completo (3.000 USD, 0,5 %, estricto, spread, swap). Rejilla pequeña predefinida: ADX<25 sí/no × SL {1,5; 2; 3} ATR × duración {12; 18; 30} barras.

| ADX<25 | SL (ATR) | Máx. barras | Exp R TRAIN (N) | Exp R VALID (N) | Exp R EXPL (N) |
|---|---:|---:|---|---|---|
| no | 1.5 | 12 | +0.012 (245) | +0.088 (196) | -0.063 (119) |
| no | 1.5 | 18 | +0.028 (244) | +0.035 (191) | -0.089 (117) |
| no | 1.5 | 30 | +0.026 (240) | +0.063 (190) | -0.011 (116) |
| no | 2.0 | 12 | -0.021 (208) | +0.075 (174) | -0.040 (100) |
| no | 2.0 | 18 | +0.016 (206) | +0.042 (168) | -0.050 (98) |
| no | 2.0 | 30 | -0.018 (203) | +0.091 (168) | +0.023 (98) |
| no | 3.0 | 12 | +0.035 (175) | +0.101 (147) | +0.008 (86) |
| no | 3.0 | 18 | +0.031 (172) | +0.053 (135) | -0.009 (83) |
| no | 3.0 | 30 | +0.003 (166) | +0.069 (133) | +0.024 (81) |
| sí | 1.5 | 12 | +0.116 (100) | +0.190 (106) | +0.064 (54) |
| sí | 1.5 | 18 | +0.145 (99) | +0.093 (102) | +0.041 (54) |
| sí | 1.5 | 30 | +0.149 (99) | +0.163 (102) | +0.151 (54) |
| sí | 2.0 | 12 | +0.037 (90) | +0.166 (95) | +0.104 (47) |
| sí | 2.0 | 18 | +0.110 (87) | +0.090 (89) | +0.091 (47) |
| sí | 2.0 | 30 | +0.090 (86) | +0.143 (89) | +0.201 (47) |
| sí | 3.0 | 12 | +0.056 (87) | +0.192 (90) | -0.016 (43) |
| sí | 3.0 | 18 | +0.099 (81) | +0.139 (85) | -0.041 (43) |
| sí | 3.0 | 30 | +0.058 (80) | +0.122 (84) | +0.019 (43) |

Configuraciones con Exp R>0 en los tres periodos: **9/18** (con filtro ADX: 7/9; sin filtro: 2/9). Con el filtro, la región es estable en signo (Exp R ≈ +0,04…+0,20 en 2018–2026), pero con N≈85–105 por periodo cada celda es estadísticamente débil, y no es evidencia independiente: estos periodos ya se habían visto al definir L2. Sin filtro el edge desaparece (≈0). Se registraron las 18 configuraciones como intentos (sesgo de selección).

## 6. Costes (Fase D, ampliada)
Ver `docs/REMIX_EURUSD_PHASE_D_REPORT.md` §5 y `PHASE_D_COST_ANALYSIS.csv`: coste ex-ante = (spread de la barra de señal + 2 pts)/SL (sin spreads futuros); los filtros 0,05 R / 0,10 R reducen coste pero no crean ventaja bruta; estrés (spread×1,5 + 10 pts/lado) deja M15 en −0,33…−0,40 R/op.

## 7. Comparación V1 vs módulos V2 (3.000 USD, 0,5 %, estricto, EURUSDm)
V1 = S01 canónico (Python verificado contra MT5: 335/335 señales, entradas y lotes). Módulos V2 = pistas congeladas implementadas en el EA. EXPL = 2025-01→2026-10; POOL = 2018→2026-10. Diferencias de datos/ejecución: barras M15/H1/H4 con spread de barra (Python) frente a ticks reales sólo desde 2026 en MT5; H4 en Python usa las barras nativas de MT5 (verificadas); la comisión de la cuenta real no está verificada (0 supuesto).

| Módulo | Periodo | N | WR % | PF | Exp R | IC95 bloques | t | Neto USD | Rent. % | DD % | Recovery | Payoff | Coste R/op | Exp R estrés | N/año | USD/año | p control |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V1_S01_M15 | EXPL | 335 | 46.0 | 1.06 | +0.027 | [-0.09;+0.13] | +0.48 | +129 | +4.3 | 10.1 | 0.40 | 1.25 | 0.037 | -0.083 | 184.1 | +71 | 0.134 |
| M05_S05_L2_H4 | EXPL | 48 | 62.5 | 1.41 | +0.146 | [-0.15;+0.41] | +1.07 | +84 | +2.8 | 2.3 | 1.21 | 0.86 | 0.028 | +0.097 | 27.1 | +47 | 0.070 |
| M05_S05_L2_H4 | POOL | 221 | 50.7 | 1.22 | +0.099 | [-0.04;+0.24] | +1.42 | +258 | +8.6 | 5.3 | 1.54 | 1.21 | 0.032 | +0.035 | 25.3 | +30 | 0.010 |
| M06_S06_L3_H4 | EXPL | 52 | 73.1 | 1.26 | +0.055 | [-0.07;+0.19] | +0.65 | +37 | +1.2 | 1.5 | 0.83 | 0.46 | 0.021 | +0.014 | 30.4 | +21 | 0.308 |
| M06_S06_L3_H4 | POOL | 285 | 65.6 | 1.11 | +0.024 | [-0.05;+0.09] | +0.61 | +102 | +3.4 | 3.8 | 0.90 | 0.57 | 0.026 | -0.023 | 32.6 | +12 | 0.234 |
| M08_S08_L4_H4 | EXPL | 60 | 45.0 | 1.10 | +0.021 | [-0.28;+0.25] | +0.14 | +41 | +1.4 | 2.7 | 0.49 | 1.27 | 0.029 | -0.031 | 33.9 | +23 | 0.318 |
| M08_S08_L4_H4 | POOL | 314 | 45.2 | 1.09 | +0.052 | [-0.07;+0.17] | +0.80 | +180 | +6.0 | 10.5 | 0.54 | 1.33 | 0.037 | -0.018 | 36.0 | +21 | 0.030 |
| M11_L1_S03inv_H1 | EXPL | 53 | 41.5 | 1.43 | +0.245 | [-0.15;+0.58] | +1.20 | +192 | +6.4 | 3.8 | 1.56 | 2.00 | 0.044 | +0.132 | 32.5 | +118 | 0.050 |
| M11_L1_S03inv_H1 | POOL | 201 | 38.3 | 1.22 | +0.148 | [-0.03;+0.34] | +1.44 | +404 | +13.4 | 5.2 | 2.43 | 2.00 | 0.058 | -0.033 | 23.3 | +47 | 0.035 |

**Conclusión de la comparación:** ninguna mejora de V2 sobre V1 es estadísticamente demostrable. En EXPL, L1 y L2 tienen mejor expectativa y menor drawdown que S01 pero con 48–53 operaciones; sus IC95 incluyen el cero. Una mejora histórica no es evidencia prospectiva. Las mejoras absolutas (decenas de USD al año) son inferiores a la incertidumbre de ejecución.

## 8. Fuentes externas (Fase 3)
`research/EXTERNAL_SOURCES.csv`: momentum FX con costes (Menkhoff et al.; BIS WP 366), patrones horarios EUR/USD (Breedon & Ranaldo), reversión intradía EURUSD (Wiśniewska). Sólo se leyeron resúmenes del buscador, no los textos completos; ninguna cifra de rentabilidad externa se importó. No se evaluaron estrategias de YouTube/GitHub (sin datos reproducibles ni costes) ni LONA (no conectado).

## 9. REMIX_EURUSD_V2.mq5
- Compilado con MetaEditor: **0 errores, 0 avisos**. `.ex5` generado. SHA-256 del fuente en `docs/V2_BUILD_INFO.json`.
- Módulos (uno a la vez; todos desactivados por defecto: `Module=NONE`, `EnableTrading=false`): S01 (referencia M15), S05/L2 (H4), S06/L3 (H4), S08/L4 (H4), L1 (H1). Exige el marco temporal de diseño (`RequireTimeframe`).
- Riesgo configurable (0,5 % por defecto, máx. 2 %), política estricta de lote mínimo, SL obligatorio (sin SL no se abre), TP configurable (retorno a la media o múltiplo de ATR), salida temporal, break-even y trailing ATR opcionales, control de spread (fracción del SL y puntos absolutos), control de deslizamiento (desviación en la orden + registro/cierre opcional), Magic Number, manejo de errores de orden, CSV de operaciones y de señales (carpeta Common\Files), criterio `OnTester` penalizado (beneficio/DD × muestra).
- Seguridad: sólo con `MQL_TESTER` y cuenta no real; las llamadas de trading están sólo en `OpenTrade`, `ClosePosition`, `ModifySL` tras `TradingAllowed()` (verificado por `tests/test_ea_v2_static.py`).
- **No se ejecutó ningún backtest oficial de V2 en MT5:** un terminal aislado necesitaría iniciar sesión en el servidor de Exness (credenciales que no se usan ni se piden) y el terminal principal no se cierra. Los resultados «esperados» de Python por módulo están en `results/v2_expected/` para compararlos con el CSV del Tester. Instrucciones: `docs/V2_TESTER_INSTRUCTIONS.md`.

## 10. Estrategias descartadas / no demostradas
Ver `REMIX_V2_STRATEGY_MATRIX.csv` (225 filas). Descartadas: S02–S04 (y sus inversas en M15), S07, S10, S12, S08 H1, S09, la mayoría de S05/S06/S11 y todas las celdas de eventos con expectativa ≤0 en TRAIN o VALID. No demostradas (pistas): L1–L4 y la celda de reversión z H4. Aprobadas para producción: **ninguna**.

## 11. Limitaciones
Spread de barra (no por tick); ticks reales sólo desde 2026-01; comisión/swap de la cuenta real sin verificar; paridad de indicadores nuevos con `iRSI`/`iADX` sin verificar; EA V2 sin backtest oficial en MT5; H1 anterior a 2018 descartado por datos inválidos; una sola serie (EURUSDm), por lo que la potencia estadística es limitada.

## 12. Siguientes pasos
1. Ejecutar V2 en su Strategy Tester (L2, L1) y comparar con `results/v2_expected/` (paridad de señales y de resultados).
2. Mantener congeladas L1–L4 y evaluar una sola vez con datos posteriores a oct-2026 (≈14–51 operaciones/año ⇒ años para N≥100).
3. Si se desea más potencia estadística: replicar la metodología en otros pares solo con su autorización.

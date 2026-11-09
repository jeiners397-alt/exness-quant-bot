# REMIX EURUSD V3 — informe cuantitativo (2026-11-09)

**Solo investigación y simulación. Ninguna estrategia está aprobada para producción.** Capital virtual 3.000 USD, riesgo 0,5 %, política estricta, compuertas de spread del EA (0,15×SL y 30 pts), filtro de coste ex-ante 0,10 R. 2025-01→2026-10 está **ya inspeccionado** (exploratorio); 2018–2024 son réplicas retrospectivas. El periodo prospectivo congelado no se ha usado.

## 1. Auditoría del resultado oficial de V2.1
- **Paridad:** 27/27 operaciones coinciden entre el Tester y Python (dirección, lotes, precio de entrada, motivo y barra de salida); neto 27.32 vs 27.3 USD, swaps -6.26 vs -6.27. Esto confirma las correcciones de la fase anterior (`docs/PARITY_V2_L2_REPORT.md`).
- **Indicadores vela a vela (2.693 barras, `scripts/compare_bar_diag.py`):** ATR, SMA (manual e `iMA`), σ y z-score coinciden a ≤5·10⁻⁷; **+DI/−DI/ADX del `iADX` nativo coinciden con la fórmula EMA(2/(n+1)) (mediana 2,6·10⁻⁷; Wilder difiere hasta 32 pts)**; 29 de 2.693 barras (1,1 %) tienen diferencia de ADX >0,01 en un episodio aislado (24–26-oct-2025) sin efecto en ninguna señal.
- **Concentración:** la mejor operación (2025-01-02 16:00:00, +24.72 USD) es el **90.5 %** del neto; sin ella el neto es **+2.60 USD**, sin las cinco mejores **-73.40 USD**; 2025: 14 operaciones, +26,01 USD; 2026: 13 operaciones, +1,31 USD. **L2 queda como no demostrada y dependiente de un outlier.**

## 2. Qué se probó (todas las configuraciones se registran)
Rejilla **predefinida**, sin barrido: A (False Breakout) 16 configuraciones, B (Volatility Momentum) 20, D (Regímenes) 14 celdas de condición × 2 TF + 8 backtests. Cada configuración se ejecutó **una vez** sobre todo el periodo; periodos, walk-forward y controles salen de esas operaciones. Controles aleatorios: 100 sorteos con la misma densidad de señales, proporción LONG/SHORT, pares SL/TP y horas. Multiplicidad: 72 configuraciones/celdas en esta fase (t máximo esperable por azar ≈ 2.92); acumulando fases anteriores (~913) ≈ 3.69. **El mayor t de la fase es 1.27.**
Periodos H1: TRAIN 2018–21 | VALID 2022–24 | EXPL 2025–26. M15 (datos desde nov-2022): TRAIN nov-22–2023 | VALID 2024 | EXPL 2025–26. Walk-forward: pliegues anuales expansivos; cada pliegue elige la configuración con mejor R medio **anterior** (N≥30) y se evalúa en el año siguiente.

## 3. Tabla comparativa de las cuatro estrategias
| Familia | TF | Configs | Operaciones (rango) | Exp R mediana [peor; mejor] | PF mediano | Configs Exp R>0 | Positivas en los 3 periodos | t máx. | Configs p control≤0,05 | DD mediano % | Walk-forward OOS (N / Exp R / PF) |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| A | H1 | 8 | 536–2545 | -0.017 [-0.055; +0.010] | 0.96 | 1 | 0 | +0.33 | 1 | 20.4 | 1019 / -0.043 / 0.91 |
| A | M15 | 8 | 311–1135 | -0.061 [-0.129; -0.001] | 0.89 | 0 | 0 | -0.01 | 0 | 18.4 | 261 / +0.003 / 1.00 |
| B | H1 | 10 | 728–3265 | -0.042 [-0.068; -0.013] | 0.91 | 0 | 0 | -0.47 | 1 | 33.1 | 845 / -0.034 / 0.92 |
| B | M15 | 10 | 103–1736 | -0.056 [-0.139; +0.026] | 0.90 | 3 | 0 | +0.24 | 1 | 27.4 | 67 / -0.057 / 0.91 |

| Estrategia | Estado | Motivo |
|---|---|---|
| **A False Breakout Reversal** | **Sin ventaja demostrada** | 1 de 16 configuraciones con Exp R>0 (mejor: +0.010 R, t=+0.33); walk-forward OOS H1 -0.043 R (N=1019), M15 +0.003 R |
| **B Volatility Momentum** | **Sin ventaja demostrada (descartada)** | 3 de 20 con Exp R>0 y ninguna significativa; una gran vela no genera continuación rentable tras costes; OOS H1 -0.034 R, M15 -0.057 R |
| **C Macro News** | **Pendiente de datos** | No existe calendario histórico con marcas temporales verificables y valores de primera publicación en este entorno (el CSV de noticias de Exness extraído estaba vacío; la API Python de MT5 no expone el calendario económico). Se dejó el validador `remix_lab/news.py` y el esquema exigido; el EA rechaza este módulo |
| **D Regime Conditional Reversal** | **Requiere investigación (pista débil), no demostrada** | La condición KER bajo + Choppiness alto en H4 es la única positiva en los tres periodos (ver §5) pero IC95 incluye 0, N=148 en 8,8 años (≈17/año), y su versión de eventos no se replica con otro diseño de salida |

## 4. Familias A y B — las 36 configuraciones
| Fam. | TF | Configuración | N | WR % | PF | Exp R | IC95 (bloques) | t | DD % | Trim.+ | TRAIN | VALID | EXPL | sin top-5 | p ctrl |
|---|---|---|---:|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---:|---:|
| A | H1 | confirm: 1, levels: PD, sl_mode: struct | 1271 | 43.4 | 1.02 | +0.010 | [-0.05;+0.07] | +0.33 | 18.8 | 19/36 | -0.054 | +0.104 | -0.014 | +0.004 | 0.02 |
| A | H1 | confirm: 1, levels: PD, sl_mode: atr | 1572 | 41.7 | 0.91 | -0.042 | [-0.10;+0.01] | -1.60 | 34.3 | 14/36 | -0.035 | -0.029 | -0.083 | -0.046 | 0.27 |
| A | H1 | confirm: 2, levels: PD, sl_mode: struct | 536 | 42.5 | 0.97 | -0.013 | [-0.09;+0.06] | -0.33 | 10.3 | 17/36 | -0.028 | +0.020 | -0.037 | -0.027 | 0.31 |
| A | H1 | confirm: 2, levels: PD, sl_mode: atr | 646 | 41.8 | 0.94 | -0.021 | [-0.10;+0.06] | -0.53 | 11.9 | 22/36 | -0.030 | +0.045 | -0.134 | -0.033 | 0.18 |
| A | H1 | confirm: 1, levels: ASIA, sl_mode: struct | 1990 | 40.9 | 0.91 | -0.049 | [-0.10;-0.00] | -2.07 | 51.2 | 13/36 | +0.005 | -0.106 | -0.064 | -0.053 | 0.36 |
| A | H1 | confirm: 1, levels: ASIA, sl_mode: atr | 2545 | 41.1 | 0.90 | -0.055 | [-0.10;-0.01] | -2.60 | 59.4 | 13/36 | -0.022 | -0.125 | -0.006 | -0.058 | 0.37 |
| A | H1 | confirm: 2, levels: ASIA, sl_mode: struct | 863 | 44.5 | 0.97 | -0.011 | [-0.08;+0.05] | -0.34 | 20.2 | 19/36 | -0.007 | -0.020 | -0.005 | -0.019 | 0.15 |
| A | H1 | confirm: 2, levels: ASIA, sl_mode: atr | 1069 | 43.7 | 0.99 | -0.002 | [-0.07;+0.06] | -0.07 | 20.6 | 21/36 | -0.027 | +0.046 | -0.024 | -0.009 | 0.08 |
| A | M15 | confirm: 1, levels: PD, sl_mode: struct | 430 | 40.7 | 0.93 | -0.039 | [-0.14;+0.07] | -0.72 | 13.9 | 9/17 | -0.029 | +0.139 | -0.119 | -0.057 | 0.33 |
| A | M15 | confirm: 1, levels: PD, sl_mode: atr | 670 | 39.1 | 0.87 | -0.071 | [-0.15;+0.02] | -1.66 | 28.0 | 6/17 | -0.074 | -0.037 | -0.079 | -0.083 | 0.67 |
| A | M15 | confirm: 2, levels: PD, sl_mode: struct | 327 | 38.5 | 0.82 | -0.100 | [-0.22;+0.01] | -1.69 | 18.8 | 7/17 | -0.044 | +0.049 | -0.195 | -0.125 | 0.72 |
| A | M15 | confirm: 2, levels: PD, sl_mode: atr | 311 | 37.3 | 0.77 | -0.129 | [-0.24;-0.02] | -2.12 | 19.3 | 4/17 | -0.186 | +0.227 | -0.164 | -0.156 | 0.88 |
| A | M15 | confirm: 1, levels: ASIA, sl_mode: struct | 693 | 41.0 | 0.94 | -0.030 | [-0.11;+0.06] | -0.67 | 13.3 | 8/17 | -0.051 | -0.005 | -0.015 | -0.041 | 0.17 |
| A | M15 | confirm: 1, levels: ASIA, sl_mode: atr | 1135 | 37.9 | 0.82 | -0.096 | [-0.16;-0.03] | -2.84 | 41.7 | 3/17 | -0.140 | -0.018 | -0.074 | -0.103 | 0.83 |
| A | M15 | confirm: 2, levels: ASIA, sl_mode: struct | 547 | 41.3 | 0.99 | -0.001 | [-0.09;+0.10] | -0.01 | 13.7 | 10/17 | -0.083 | +0.231 | -0.013 | -0.015 | 0.09 |
| A | M15 | confirm: 2, levels: ASIA, sl_mode: atr | 561 | 39.0 | 0.90 | -0.050 | [-0.14;+0.05] | -1.05 | 17.9 | 11/17 | -0.130 | +0.180 | -0.034 | -0.064 | 0.44 |
| B | H1 | k: 1.5, ker_on: true, mode: impulse, sl_mode: atr | 1834 | 42.1 | 0.91 | -0.044 | [-0.09;+0.00] | -1.78 | 38.8 | 11/36 | -0.038 | -0.034 | -0.074 | -0.048 | 0.37 |
| B | H1 | k: 1.5, ker_on: true, mode: impulse, sl_mode: struct | 1628 | 43.4 | 0.93 | -0.029 | [-0.08;+0.01] | -1.17 | 29.4 | 14/36 | -0.021 | -0.023 | -0.058 | -0.034 | 0.20 |
| B | H1 | k: 1.5, ker_on: false, mode: impulse, sl_mode: atr | 3265 | 42.0 | 0.91 | -0.043 | [-0.08;-0.01] | -2.33 | 52.6 | 15/36 | -0.049 | -0.032 | -0.053 | -0.046 | 0.23 |
| B | H1 | k: 1.5, ker_on: false, mode: impulse, sl_mode: struct | 2846 | 42.9 | 0.91 | -0.042 | [-0.08;-0.01] | -2.21 | 45.7 | 13/36 | -0.039 | -0.037 | -0.054 | -0.044 | 0.37 |
| B | H1 | k: 2.0, ker_on: true, mode: impulse, sl_mode: atr | 1245 | 41.3 | 0.89 | -0.058 | [-0.12;-0.00] | -1.92 | 34.4 | 13/36 | -0.039 | -0.055 | -0.106 | -0.064 | 0.54 |
| B | H1 | k: 2.0, ker_on: true, mode: impulse, sl_mode: struct | 1073 | 44.4 | 0.96 | -0.014 | [-0.07;+0.04] | -0.47 | 17.2 | 17/36 | +0.024 | -0.027 | -0.079 | -0.021 | 0.17 |
| B | H1 | k: 2.0, ker_on: false, mode: impulse, sl_mode: atr | 2094 | 41.9 | 0.93 | -0.036 | [-0.08;+0.01] | -1.53 | 35.6 | 15/36 | -0.047 | -0.022 | -0.040 | -0.040 | 0.35 |
| B | H1 | k: 2.0, ker_on: false, mode: impulse, sl_mode: struct | 1819 | 44.4 | 0.96 | -0.013 | [-0.06;+0.03] | -0.57 | 21.3 | 15/36 | -0.008 | -0.012 | -0.029 | -0.017 | 0.05 |
| B | H1 | ker_on: true, mode: squeeze, sl_mode: atr | 728 | 41.8 | 0.89 | -0.056 | [-0.13;+0.02] | -1.40 | 23.1 | 13/36 | -0.115 | -0.026 | +0.009 | -0.067 | 0.53 |
| B | H1 | ker_on: false, mode: squeeze, sl_mode: atr | 959 | 41.4 | 0.86 | -0.068 | [-0.13;+0.00] | -1.98 | 31.9 | 15/36 | -0.108 | -0.056 | -0.004 | -0.077 | 0.64 |
| B | M15 | k: 1.5, ker_on: true, mode: impulse, sl_mode: atr | 1014 | 37.6 | 0.85 | -0.084 | [-0.15;-0.01] | -2.33 | 39.6 | 3/17 | -0.088 | -0.132 | -0.066 | -0.092 | 0.75 |
| B | M15 | k: 1.5, ker_on: true, mode: impulse, sl_mode: struct | 1040 | 39.4 | 0.89 | -0.060 | [-0.13;+0.01] | -1.71 | 29.4 | 6/17 | -0.098 | -0.055 | -0.031 | -0.068 | 0.51 |
| B | M15 | k: 1.5, ker_on: false, mode: impulse, sl_mode: atr | 1703 | 38.5 | 0.88 | -0.065 | [-0.12;-0.01] | -2.31 | 45.8 | 5/17 | -0.063 | -0.103 | -0.054 | -0.069 | 0.52 |
| B | M15 | k: 1.5, ker_on: false, mode: impulse, sl_mode: struct | 1736 | 39.7 | 0.91 | -0.047 | [-0.10;+0.01] | -1.71 | 36.6 | 6/17 | -0.059 | -0.011 | -0.049 | -0.051 | 0.33 |
| B | M15 | k: 2.0, ker_on: true, mode: impulse, sl_mode: atr | 529 | 34.6 | 0.78 | -0.139 | [-0.24;-0.04] | -2.78 | 33.7 | 2/17 | -0.083 | -0.256 | -0.153 | -0.155 | 0.93 |
| B | M15 | k: 2.0, ker_on: true, mode: impulse, sl_mode: struct | 606 | 38.4 | 0.85 | -0.083 | [-0.17;+0.00] | -1.82 | 25.3 | 4/17 | -0.042 | -0.137 | -0.095 | -0.096 | 0.74 |
| B | M15 | k: 2.0, ker_on: false, mode: impulse, sl_mode: atr | 857 | 38.5 | 0.91 | -0.052 | [-0.13;+0.03] | -1.31 | 23.2 | 6/17 | -0.032 | -0.078 | -0.067 | -0.061 | 0.35 |
| B | M15 | k: 2.0, ker_on: false, mode: impulse, sl_mode: struct | 1012 | 41.9 | 1.01 | +0.009 | [-0.07;+0.07] | +0.24 | 13.2 | 6/17 | +0.042 | -0.019 | -0.012 | +0.001 | 0.04 |
| B | M15 | ker_on: true, mode: squeeze, sl_mode: atr | 103 | 40.8 | 1.04 | +0.026 | [-0.21;+0.25] | +0.22 | 5.0 | 8/14 | +0.181 | +0.353 | -0.105 | -0.049 | 0.21 |
| B | M15 | ker_on: false, mode: squeeze, sl_mode: atr | 151 | 41.1 | 1.01 | +0.007 | [-0.19;+0.20] | +0.07 | 6.5 | 7/14 | +0.065 | +0.444 | -0.079 | -0.044 | 0.23 |

Lectura: la mediana de Exp R de A es -0.039 R y la de B -0.049 R; con 100–3.300 operaciones por configuración el IC de la expectativa es de ±0,05–0,10 R, de modo que lo positivo es indistinguible de cero y casi siempre cambia de signo entre periodos. Las configuraciones con p de control ≤0,05 (3 de 36) son las esperables por azar entre 36 pruebas. Frecuencia: A/H1 genera 536–2.545 operaciones en 8,8 años (≈120–580 por 2 años; las configuraciones de ≤1.300 operaciones caen en el rango exploratorio de 100–300 por 2 años) pero sin ventaja.

**Gestión de posiciones (SL estructural/ATR, TP, trailing, BE, tiempo):** el SL estructural vs ATR se comparó dentro de la rejilla (columna `sl`); las demás variantes (trailing, break-even, salida por estructura) **no se ejecutaron** porque la orden pide probarlas «únicamente para hipótesis que justifiquen la prueba» y ninguna A/B/D presenta ventaja que gestionar (la Fase C ya mostró que BE/trailing no rescatan una expectativa nula).

## 5. Estrategia D — condiciones de régimen (reversión tras |z|≥2)
Pregunta falsable: ¿mejora alguna condición observable (KER10, Choppiness14, ADX14 (fórmula MT5), percentil de volatilidad) la probabilidad de reversión? Umbrales = terciles de los eventos TRAIN; SL 1,5 ATR; cota conservadora.

| TF | Condición (umbrales = terciles de los eventos TRAIN) | P(+1R antes de −1R) TRAIN / VALID / EXPL | N TRAIN / VALID / EXPL | Exp R cons. TRAIN | VALID | EXPL |
|---|---|---|---|---:|---:|---:|
| H1 | ALL | 0.430 / 0.479 / 0.476 | 1010 / 745 / 456 | -0.116 | -0.011 | -0.020 |
| H1 | RANGE(ker<p33 & chop>p67) | 0.407 / 0.528 / 0.510 | 216 / 163 / 100 | -0.174 | +0.089 | +0.032 |
| H1 | adx_LOW | 0.398 / 0.445 / 0.493 | 337 / 245 / 154 | -0.192 | -0.060 | +0.027 |
| H1 | chop_HIGH | 0.427 / 0.515 / 0.503 | 337 / 262 / 171 | -0.130 | +0.056 | +0.024 |
| H1 | ker_LOW | 0.398 / 0.510 / 0.500 | 337 / 251 / 138 | -0.180 | +0.065 | +0.018 |
| H1 | volpct_LOW | 0.416 / 0.474 / 0.463 | 327 / 215 / 162 | -0.159 | -0.051 | -0.074 |
| H4 | ALL | 0.428 / 0.489 / 0.424 | 353 / 284 / 172 | -0.024 | +0.092 | +0.005 |
| H4 | RANGE(ker<p33 & chop>p67) | 0.420 / 0.419 / 0.359 | 69 / 62 / 39 | -0.079 | -0.027 | -0.141 |
| H4 | adx_LOW | 0.390 / 0.489 / 0.439 | 118 / 133 / 66 | -0.066 | +0.112 | +0.032 |
| H4 | chop_HIGH | 0.483 / 0.469 / 0.361 | 118 / 96 / 61 | +0.071 | +0.061 | -0.128 |
| H4 | ker_LOW | 0.466 / 0.429 / 0.422 | 118 / 91 / 71 | +0.035 | +0.027 | -0.005 |
| H4 | volpct_LOW | 0.514 / 0.494 / 0.464 | 107 / 91 / 56 | +0.105 | +0.010 | +0.072 |

Walk-forward por celda (elige la mejor celda con datos anteriores y la aplica el año siguiente): H1: N=565, Exp R ponderada -0.117 (todas las condiciones del mismo periodo: -0.046); H4: N=208, Exp R ponderada -0.057 (todas las condiciones del mismo periodo: +0.008). **Elegir condición con datos pasados no mejora la expectativa fuera de muestra.**

Backtests completos (S05: z=2, SL 2 ATR, TP = retorno a la media, `max_bars` 48/18; filtros pre-registrados):

| TF | Filtro | N | WR % | PF | Exp R | IC95 | t | DD % | Neto USD | sin top-5 | TRAIN | VALID | EXPL | p ctrl |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H1 | D0 sin filtro | 2038 | 37.0 | 0.86 | -0.061 | [-0.12;-0.01] | -2.14 | 51.1 | -1426 | -0.071 | -0.131 | -0.008 | +0.006 | 0.71 |
| H1 | D1 ADX_MT5<25 (=L2) | 628 | 40.4 | 0.86 | -0.070 | [-0.16;+0.02] | -1.48 | 24.0 | -610 | -0.094 | -0.063 | -0.062 | -0.105 | 0.65 |
| H1 | D2 KER<p33(TRAIN) | 901 | 41.2 | 0.89 | -0.050 | [-0.13;+0.03] | -1.28 | 25.0 | -617 | -0.066 | -0.118 | -0.024 | +0.069 | 0.46 |
| H1 | D3 RANGE ker<p33 & chop>p67 (TRAIN) | 532 | 42.7 | 0.87 | -0.069 | [-0.16;+0.02] | -1.43 | 19.2 | -466 | -0.093 | -0.086 | -0.114 | +0.036 | 0.57 |
| H4 | D0 sin filtro | 469 | 44.6 | 1.03 | +0.012 | [-0.08;+0.12] | +0.24 | 7.7 | +75 | -0.018 | +0.015 | +0.040 | -0.043 | 0.22 |
| H4 | D1 ADX_MT5<25 (=L2) | 133 | 47.4 | 1.17 | +0.076 | [-0.09;+0.27] | +0.84 | 6.0 | +123 | -0.001 | +0.007 | +0.095 | +0.154 | 0.06 |
| H4 | D2 KER<p33(TRAIN) | 247 | 46.2 | 1.10 | +0.040 | [-0.10;+0.18] | +0.59 | 5.9 | +147 | -0.007 | +0.078 | -0.002 | +0.030 | 0.06 |
| H4 | D3 RANGE ker<p33 & chop>p67 (TRAIN) | 148 | 50.7 | 1.28 | +0.112 | [-0.07;+0.27] | +1.27 | 3.0 | +227 | +0.042 | +0.170 | +0.103 | +0.027 | 0.02 |

H4 «RANGE» (D3): 148 operaciones, PF 1.28, +0.112 R, IC95 [-0.0674, 0.2729], t=1.27, p de control 0.02, DD 3.0 %, sin las cinco mejores +0.042 R; positiva en los tres periodos (TRAIN en parte in-sample porque define los umbrales). Pero en el diseño de eventos (SL 1,5 ATR, barrera +1R) el mismo régimen H4 es negativo en VALID y EXPL: **la «ventaja» depende de la estructura de salida**, señal de fragilidad. Sigue como hipótesis a validar con datos nuevos, no como estrategia.

## 6. Descartadas / que merecen continuar
- **Descartadas:** B en todas sus configuraciones; A/M15; A/H1 con SL ATR y niveles asiáticos con confirmación de 1 barra; D en H1 (negativa con cualquier filtro).
- **Merecen continuar (solo como hipótesis, sin afirmar ventaja):** D3 H4 (régimen de baja eficiencia + alta choppiness), A/H1 PDH/PDL con SL estructural y confirmación en 1 barra (la mejor de A: +0,010 R, p de control 0,02, pero TRAIN −0,054 y EXPL −0,014 → inestable) y la ya congelada L1–L4. Ninguna cumple el criterio de «prometedora».
- **Pendiente de datos:** C (calendario macro verificable con primera publicación).

## 7. REMIX_EURUSD_V3.mq5
Compilado con MetaEditor: **0 errores, 0 avisos** (SHA-256 fuente `0d16cdb6ee992a57503f9f713c3e17be6694f4a075da978427eb68b084d31fa8`). Módulos A, B, D activables individualmente (`Module`), C bloqueado (INIT_FAILED con mensaje); **todos desactivados por defecto** (`Module=NONE`, `EnableTrading=false`). Solo Tester, SL obligatorio, lote estricto, control de spread/coste, BE y trailing opcionales, CSV de operaciones y de señales (se reinician en cada corrida; en V2.1 se acumulaban). V1 (`1c327de0…`), V2 (`9908279f…`) y V2.1 (`9a5be44f…`) **intactos** (verificado por hash en `tests/test_v3.py`).
Archivos `.set`: `mql5/sets/V3_A_H1_PD_struct.set`, `V3_B_H1_impulse_k2_struct.set`, `V3_D_H4_regime.set`. Operaciones esperadas de Python en 2025-01→2026-10 (no son resultados de MT5): A/H1 236 operaciones, -35.69 USD, PF 0.976; B/H1 317, -108.15 USD, PF 0.943; D/H4 40, +4.24 USD, PF 1.019. La paridad MT5 de estos módulos **no está verificada** (el EA V3 no se ha ejecutado en el Tester).

## 8. Limitaciones y pasos
Spread de barra (el primer tick de reapertura de fin de semana tiene spread mayor); ticks reales solo desde 2026; comisión de la cuenta real sin verificar; periodo EXPL contaminado; sin datos macro. Siguiente: (1) ejecutar los `.set` V3 en su Tester y comparar con `results/v3_expected/`; (2) mantener congeladas L1–L4; (3) conseguir un calendario macro verificable para C; (4) no seguir optimizando A/B.

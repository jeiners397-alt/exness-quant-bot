# V10 — Investigación económica (momentum, macro, regímenes, volatilidad, M15)

Todas las hipótesis y su fundamento se escribieron en el código antes de ejecutar (`v10_momentum.py`, `v10_macro.py`, `v10_m15.py`). Presupuesto cerrado: **86 pruebas** (momentum 38, económicas 12, volatilidad 5, M15 22, macro 3, controles H4 6). Acumulado V7+V8+V9+V10 = **3.805** pruebas → t* = √(2 ln N) = **4,06**. Tramos fijos: DEV 2024 · SEL 2025 · VAL 2026-01→10 · reserva ≥ 2026-11-01 sin tocar.

## A. Literatura consultada y cómo se usó (no se asumió transferibilidad)
- **Moskowitz, Ooi, Pedersen (2012), *Time series momentum*, JFE 104(2), DOI 10.1016/j.jfineco.2011.11.003.** Documentan que el signo del retorno de los últimos 1–12 meses predice el retorno siguiente en futuros de 58 contratos, con reversión parcial a más de un año, y lo atribuyen a reacción lenta a la información y a flujos de cobertura/especulación. *Uso:* el estadístico es el suyo (pendiente de retorno futuro escalado por volatilidad sobre el signo del retorno pasado). *Límite:* sus datos son mensuales con futuros; aquí son CFD intradía con spread de 0,16 USD y solo 34 meses.
- **Macro y metales (*Impact of macroeconomic news on metal futures*, J. Banking & Finance, ScienceDirect S0378426611001968).** **No se pudo leer el artículo desde este equipo**, por lo que no se citan sus resultados ni se asumen. Se usó únicamente la pregunta que plantea (¿cambia la volatilidad/dirección del metal alrededor de anuncios macro?), medida con datos propios sin suponer dirección.
- **Bailey & López de Prado (2014)** *The Deflated Sharpe Ratio* (DOI 10.3905/jpm.2014.40.5.094) y **Bailey, Borwein, López de Prado, Zhu (2015)** *The Probability of Backtest Overfitting* (SSRN 2326253): implementados en `v10_h4_audit.py` (DSR) y `v10_final.py` (PBO por CSCV).
- **FRED/ALFRED:** ver §D.

## B. Momentum, reversión y volatilidad (Lote B) — `V10_MOMENTUM_RESEARCH.csv`
**25 pruebas TSMOM** (pendiente de y = retorno futuro a *h* barras / (σ₆₀·√h) sobre x = signo del retorno de *L* barras; Newey-West de rezago *h*): D1 L∈{5,21,63}×h∈{1,5,21}; H4 L∈{6,30,126}×h∈{6,30}; H1 L∈{4,24,120}×h∈{4,24}; M15 L∈{16,96}×h∈{16,96}.
- **Ninguna alcanza t\*.** 24 de 25 tienen |t| < 2. Todas las pendientes son positivas (0,01–0,21 σ por señal) pero pequeñas e inestables por tramo (p. ej. D1 L=21 h=21: +0,21 pero DEV +0,01, SEL +0,09; H4 L=126 h=30: DEV −0,19, VAL +0,15).
- La única con |t|≥2 (**M15 L=16 h=96: pendiente 0,029 σ, t 2,10**, signo coherente en DEV/SEL/VAL) es lo que se espera por azar en 25 pruebas (≈1,2) y su efecto (0,03 σ) es del orden del coste por viaje (0,007 σ por h=96, más la rotación): **clase C, no B** tras aplicar la regla t\*.
- **Reversión tras extremos (|z|>2):** H4 (n=75) y D1 (n=23) → F por tamaño; H1 (n=250) −0,005 (t −0,06); M15 (n=738) +0,033 (t 0,65). Sin evidencia.
- **Momentum condicionado** por volatilidad (percentil previo) y por eficiencia (ER30), 6 celdas H4 L=30 h=6: todas |t|<1,6; ninguna diferencia útil entre terciles.
- **Continuación tras rupturas y consolidaciones (H4, ventana 20):** con consolidación previa (rango de 10 velas en el cuartil inferior): n=114, **+0,49 R (t 2,70)**, VAL +1,47 R; sin consolidación n=129, +0,22 R (t 1,38). **Diferencia con/sin consolidación: t 1,09 → no distinguible.** Clase C (subconjunto de la muestra ya explorada).
- **Información incremental respecto de la H4 congelada:** las rupturas H4 ya capturan casi todo el signo de la ventana de 20 velas; el TSMOM puro (F: signo de 20 velas, siempre una posición) rinde +2.538 USD con PF 1,30 pero DD 26 % y 87 % de exposición (`V10_XAU_H4_BENCHMARKS.csv`). Ninguna señal nueva añade evidencia independiente.

## C. Volatilidad (`V10_VOLATILITY_REGIMES.csv`)
- Agrupamiento: autocorrelación de |r| H4 = 0,25 (lag 1) decayendo despacio (lags 2–30 en el CSV): la volatilidad es persistente, es el único hecho robusto de esta sección.
- Expectativa de la ruptura H4 por tercil (n≈81 cada uno): **sube con la volatilidad relativa** (rv20/rv120: bajo +0,13 R, medio +0,36, alto **+0,59 R (t 2,71)**; P(TP) 27 %→34 %→40 %) y **baja con la compresión previa** (compresión baja +0,56 vs alta +0,08; contrario a la hipótesis de «compresión→expansión» del §B, que usaba la definición de cuartil) y con el tamaño de la vela de ruptura (+0,52 → +0,12). Son 15 celdas descriptivas sobre las mismas 243 señales: no se convierten en filtros.

## D. Datos macro y regímenes económicos
**Fuentes y procedencia** (`V10_MACRO_DATA_PROVENANCE.csv`):
- Series de mercado de FRED (DFII10 tasa real 10 a, DGS10, T10YIE inflación implícita, DTWEXBGS dólar amplio, VIXCLS), bajadas con WebFetch porque `fred.stlouisfed.org` no responde desde el equipo local; CSV bruto con SHA-256 en `data/raw/v10/`. No son series revisadas; se usan con **retardo de 2 días de calendario** (publicación D+1 tarde).
- Fechas de NFP y CPI (33 + 33, 08:30 ET): enlaces de archivo de BLS vía WebFetch (el acceso directo da 403); FOMC (23 reuniones, 14:00 ET): HTML de federalreserve.gov guardado. Control de plausibilidad: ningún evento cae en fin de semana, y **el pico de rango de 5 min cae exactamente en la ranura del anuncio tanto en horario de verano (12:30/18:00 UTC) como de invierno (13:30/19:00 UTC)** (`V10_MACRO_TIMESTAMP_CHECK.csv`).
- **No se obtuvieron ALFRED/vintages ni consensos**: no hay fuente verificable accesible. Por tanto **no se calculan sorpresas** (clase F) y no se usan valores revisados de NFP/CPI.

**Ventanas de anuncios (M5)** — `V10_MACRO_EVENTS.csv` (86 eventos), 4 controles por evento (mismo reloj ±1 y ±2 semanas, sin otro anuncio):
| | n | rango 30 min (mediana) | control | razón | vol 60 min post/pre | P(continuación 15→60 min) |
|---|---|---|---|---|---|---|
| NFP | 31 | 28,3 USD | 8,3 | ×2,8 (t log 12,8) | 3,7 | **26 %** (reversión 74 %) |
| CPI | 32 | 22,1 USD | 9,9 | ×2,2 (t 7,2) | 2,3 | 50 % |
| FOMC | 23 | 18,5 USD | 6,3 | ×3,0 (t 7,9) | 3,0 | 61 % |
- La volatilidad se multiplica por 2–4: es un hecho, no una ventaja. La dirección no se predice con la información disponible. NFP revierte 23 de 31 veces entre los 15 y 60 min (p bilateral ≈ 0,01 sin ajustar; con las 3 familias y la multiplicidad acumulada no es concluyente y n<100).
- Estrategias sobre anuncios (entrada T+15 min, salida T+60 min, en ATR M5): continuación −0,24 (t −0,37); reversión +0,08 (t 0,12), n=86 → **F/D**. El spread por barra no refleja el ensanchamiento real durante el anuncio (el dato por barra es una muestra puntual), por lo que el coste en ventanas de noticias está subestimado.

**Regímenes económicos** (`V10_ECONOMIC_REGIMES.csv`, 6 variables):
- Oro D1, retorno 5 d futuro ~ variable (z expansivo, HAC): **ninguna significativa** (|t| ≤ 1,44) y con signo inestable por tramo (p. ej. tasa real 20 d: DEV −0,07, SEL +0,05, VAL −0,02).
- Expectativa de las 248 operaciones de la ruptura por tercil de cada variable (18 comparaciones retrospectivas): destaca **VIX subiendo en los últimos 20 días (+0,88 R, t 4,02; n 83)** frente a +0,25 y −0,25 R en los otros terciles (no monótono); también rendimiento nominal 10 a subiendo (+0,51, t 2,42), real subiendo (+0,45, t 2,14), nivel alto de VIX (+0,55, t 2,53). Con 18 comparaciones sobre las mismas 248 operaciones, y no monotonía, **se registran como hipótesis de nueva generación (C), no como filtros**.

## E. XAUUSD M15 (Lote D) — `V10_XAU_M15_EVENTS.csv`
- Coste/ATR: **M15 0,039** (Asia 0,043 · Londres 0,040 · NY 0,032 · cierre 0,056) frente a M1 0,166, M5 0,070, H4 0,009. ATR M15 mediano 4,84 USD; spread mediano 0,16 USD.
- 5 familias × {primaria, invertida} × RR {1,5; 3} = 20 pruebas + 2 de noticias. Reglas de clase y control (dirección barajada, 300 reps) prefijados.
- **Ninguna candidata.** 13 D, 3 C, 6 F. Lo más relevante: *todas* las invertidas son negativas (−0,05…−0,14 R) y las primarias de ruptura de 96 velas se acercan a 0 bruto (+0,04…+0,13 R) con neto +0,00…+0,08 R. Mejores: ruptura de 96 velas TP 3R: bruta +0,097, neta +0,054 (t 1,01, DEV −0,05, SEL +0,11, VAL +0,10); alineada con la tendencia H4 TP 3R: bruta +0,127, neta +0,084 (t 1,29; DEV −0,07, SEL +0,13, VAL +0,20; p(control)=0,043). Pullback, compresión y rango asiático: ≤ 0 neto.
- **Control oficial MT5** de la ruptura de 96 velas TP 3R: 1.077 op. (1,5/día), **+656,97 USD, PF 1,13, DD de equidad 9,65 %**; paridad con Python 97,1 % de señales, 100 % de dirección, 98,2 % de salidas, expectativa +0,054 (Py) vs +0,062 (MT5). Por tramo: DEV −0,005 R (PF 0,94), SEL +0,05 (1,06), VAL +0,12 (1,23). IC95 por bloques [−0,04; +0,16] R. **No es candidata: t≈1.**

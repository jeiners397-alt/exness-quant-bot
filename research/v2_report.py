"""Genera docs/REMIX_EURUSD_V2_RESEARCH_REPORT.md, docs/V2_TESTER_INSTRUCTIONS.md y research/REMIX_V2_STRATEGY_MATRIX.csv desde los CSV de resultados."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ev = pd.read_csv(ROOT / "research/PHASE_E_EVENT_STUDY.csv")
sel = pd.read_csv(ROOT / "research/PHASE_E_SELECTION.csv")
meta = json.loads((ROOT / "research/PHASE_E_META.json").read_text())
pr = pd.read_csv(ROOT / "research/PHASE_E_PARAM_REGION.csv")
cmp_ = pd.read_csv(ROOT / "research/V2_VS_V1_COMPARISON.csv")
jd = pd.read_csv(ROOT / "research/PHASE_D_JOINED.csv")
ncell = meta["n_cells"]; tstar = float(np.sqrt(2 * np.log(ncell)))

# ---- matriz unificada
rows = []
for r in jd.itertuples():
    rows.append(dict(origen="Fase D", familia=r.strategy, tf=r.tf, variante=str(r.variant), n_exploratorio=r.n, pf=r.pf, exp_R=r.exp_R, t=r.t, n_retro=r.n_R, exp_R_retro=r.exp_R_R, decision=r.decision))
for r in sel.itertuples():
    dec = "No demostrada" if r.pass_basic else ("Descartada" if (r.E_TRAIN <= 0 or r.E_VALID <= 0) else "No demostrada")
    rows.append(dict(origen="Fase E (eventos)", familia=r.hyp, tf=r.tf, variante=f"{r.regime} k={r.k}", n_exploratorio=getattr(r, "n_EXPL", np.nan), pf=np.nan, exp_R=getattr(r, "E_EXPL", np.nan), t=getattr(r, "t_EXPL", np.nan),
                    n_retro=getattr(r, "n_VALID", np.nan), exp_R_retro=getattr(r, "E_VALID", np.nan), decision=dec))
M = pd.DataFrame(rows)
M.to_csv(ROOT / "research/REMIX_V2_STRATEGY_MATRIX.csv", index=False)

fam = ev[(ev.regime == "ALL") & (ev.k == 1.0)].assign(fam=lambda d: d.hyp.str[:2]).groupby(["fam", "tf", "period"]).E_cons.mean().unstack()[["TRAIN", "VALID", "EXPL"]].round(3)
fam_md = ["| Familia | TF | TRAIN 2018-21 | VALID 2022-24 | EXPL 2025-26 |", "|---|---|---:|---:|---:|"] + [f"| {a} | {b} | {r.TRAIN:+.3f} | {r.VALID:+.3f} | {'' if pd.isna(r.EXPL) else f'{r.EXPL:+.3f}'} |" for (a, b), r in fam.iterrows()]
ex = ev[(ev.hyp == "A1_zrev_2.0") & (ev.regime == "ALL")]


def prob_tab(tf):
    s = ex[ex.tf == tf]
    out = ["| Periodo | k (R) | N | P(+kR antes de −1R) cons. [IC95 Wilson] | P opt. | P equilibrio sin coste | E cons. [IC95 bloques] | E opt. | coste/op (R) |", "|---|---:|---:|---|---:|---:|---|---:|---:|"]
    for r in s.itertuples():
        out.append(f"| {r.period} | {r.k} | {r.n} | {r.p_win_cons:.3f} [{r.p_ci_lo:.3f};{r.p_ci_hi:.3f}] | {r.p_win_opt:.3f} | {r.p_breakeven_nocost:.3f} | {r.E_cons:+.3f} [{r.E_cons_ci_lo:+.2f};{r.E_cons_ci_hi:+.2f}] | {r.E_opt:+.3f} | {r.cost_R:.3f} |")
    return "\n".join(out)


chance = f"{int((sel.E_TRAIN > 0).sum())} de {len(sel)} grupos con E>0 en TRAIN; {int(((sel.E_TRAIN > 0) & (sel.E_VALID > 0)).sum())} siguen >0 en VALID; {int(((sel.E_TRAIN > 0) & (sel.E_VALID > 0) & (sel.E_EXPL > 0)).sum())} en EXPL; {int(sel.pass_basic.sum())} cumple la regla básica; {int(sel.promising.sum())} prometedoras"
corr = f"{sel[['E_TRAIN', 'E_VALID']].corr().iloc[0, 1]:.2f}"
pv = pr.pivot_table(index=["adx_filter", "sl_atr", "max_bars"], columns="period", values="exp_R")[["TRAIN", "VALID", "EXPL"]]
pn = pr.pivot_table(index=["adx_filter", "sl_atr", "max_bars"], columns="period", values="n")[["TRAIN", "VALID", "EXPL"]]
pv_md = ["| ADX<25 | SL (ATR) | Máx. barras | Exp R TRAIN (N) | Exp R VALID (N) | Exp R EXPL (N) |", "|---|---:|---:|---|---|---|"] + [
    f"| {'sí' if a else 'no'} | {s} | {m} | {r.TRAIN:+.3f} ({int(pn.loc[(a, s, m), 'TRAIN'])}) | {r.VALID:+.3f} ({int(pn.loc[(a, s, m), 'VALID'])}) | {r.EXPL:+.3f} ({int(pn.loc[(a, s, m), 'EXPL'])}) |" for (a, s, m), r in pv.iterrows()]
allpos = int((pv > 0).all(axis=1).sum()); onpos = int((pv.loc[True] > 0).all(axis=1).sum()); offpos = int((pv.loc[False] > 0).all(axis=1).sum())
cmp_md = ["| Módulo | Periodo | N | WR % | PF | Exp R | IC95 bloques | t | Neto USD | Rent. % | DD % | Recovery | Payoff | Coste R/op | Exp R estrés | N/año | USD/año | p control |", "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
for r in cmp_.itertuples():
    ci = str(r.ci_block).strip("[]").split(",")
    cmp_md.append(f"| {r.module} | {r.period} | {r.n} | {r.wr} | {r.pf:.2f} | {r.exp_R:+.3f} | [{float(ci[0]):+.2f};{float(ci[1]):+.2f}] | {r.t:+.2f} | {r.net_usd:+.0f} | {r.ret_pct:+.1f} | {r.maxdd_pct:.1f} | {r.recovery:.2f} | {r.payoff:.2f} | {r.cost_R:.3f} | {r.expR_stress:+.3f} | {r.trades_per_year} | {r.usd_per_year:+.0f} | {r.ctrl_p:.3f} |")

doc = f"""# REMIX EURUSD V2 — Informe de investigación y desarrollo (2026-11-09)

**Estado: NO existe ninguna estrategia aprobada para producción.** REMIX_EURUSD_V2.mq5 es un laboratorio experimental con negociación desactivada por defecto. Solo simulación / Strategy Tester. Sin `order_send`. Todo resultado sobre 2025-01→2026-10 es exploratorio (ya inspeccionado); 2018–2024 son réplicas retrospectivas; la evaluación prospectiva (datos posteriores a oct-2026, `PROSPECTIVE_FREEZE_2026-11-09.json`) no se ha tocado.

## 1. Resumen ejecutivo
- **Mejores hipótesis encontradas (ninguna demostrada):** L2 (S05 Z-score reversión H4 con ADX<25) y L1 (S03 largo invertido H1). Agrupando 2018–2026-10 (periodos retrospectivo + exploratorio): L2 {cmp_[(cmp_.module=='M05_S05_L2_H4')&(cmp_.period=='POOL')].iloc[0].n} operaciones, PF {cmp_[(cmp_.module=='M05_S05_L2_H4')&(cmp_.period=='POOL')].iloc[0].pf:.2f}, expectativa {cmp_[(cmp_.module=='M05_S05_L2_H4')&(cmp_.period=='POOL')].iloc[0].exp_R:+.3f} R, IC95 [{float(str(cmp_[(cmp_.module=='M05_S05_L2_H4')&(cmp_.period=='POOL')].iloc[0].ci_block).strip('[]').split(',')[0]):+.2f}; {float(str(cmp_[(cmp_.module=='M05_S05_L2_H4')&(cmp_.period=='POOL')].iloc[0].ci_block).strip('[]').split(',')[1]):+.2f}], p de control aleatorio {cmp_[(cmp_.module=='M05_S05_L2_H4')&(cmp_.period=='POOL')].iloc[0].ctrl_p:.3f}, DD {cmp_[(cmp_.module=='M05_S05_L2_H4')&(cmp_.period=='POOL')].iloc[0].maxdd_pct:.1f} %. El intervalo incluye el cero y t < t* de multiplicidad: **no demostrada**.
- **Aunque fuese real, la ventaja es económicamente mínima:** ≈25 operaciones/año × ~0,1 R × 0,5 % ⇒ ≈{cmp_[(cmp_.module=='M05_S05_L2_H4')&(cmp_.period=='POOL')].iloc[0].usd_per_year:.0f} USD/año sobre 3.000 USD (≈1 %/año). No supera a V1 de forma que justifique un robot.
- **Por qué fallan las estrategias tradicionales en EURUSD (hallazgos medidos):** (1) el spread consume 0,11–0,14 R por operación en M15 (SL ≈10 pips) y 0,03–0,06 R en H1/H4; (2) el rendimiento *bruto* de seguimiento de tendencia y rupturas es ≈0 o negativo en 2018–2026; (3) las reversiones tienen probabilidad de acierto cercana al equilibrio sin costes; (4) los efectos horarios existen pero son ≤1,7 pb (≈0,2 pip) frente a un spread de ≈0,8–0,9 pip; (5) las diferencias entre periodos/regímenes son mayores que cualquier ventaja media.
- **Búsqueda de eventos:** {ncell} celdas (hipótesis × TF × régimen × k) con ordenación intrabarra tratada como cota (conservadora/optimista). {chance}. La correlación entre la expectativa de TRAIN y la de VALID de lo seleccionado es {corr}: **la selección con datos pasados casi no predice los siguientes** (señal de que lo elegido es ruido). t* por multiplicidad ≈ {tstar:.2f}; ninguna celda se acerca.

## 2. Auditoría de fases anteriores (Fase 0)
S01: PF 1,065, +0,029 R, t=0,52; S02–S04 negativos tras costes; Fase D: 100 configuraciones, 75 descartadas, 19 no demostradas, 6 pendientes de datos, 0 prometedoras. Las cuatro pistas L1–L4 siguen **congeladas sin modificar** (hash del pre-registro en `research/PROSPECTIVE_FREEZE_2026-11-09.json`). No se repitieron pruebas de fases anteriores; las nuevas son hipótesis independientes registradas por separado.

## 3. Diagnóstico y probabilidades (Fases 1 y 4)
Diseño: evento = señal al cierre de la barra; entrada a la apertura siguiente (ask para largos, bid para cortos); SL = 1,5×ATR14; barreras +0,5/+1/+1,5/+2/+3 R; horizonte 24 barras (H1) / 12 (H4); eventos separados ≥ horizonte/4 barras. Cuando SL y TP caen en la misma barra no se infiere el orden: se informa la cota conservadora (pierde) y la optimista (gana). Periodos: TRAIN 2018–2021 (estimación), VALID 2022–2024 (observada fuera de muestra, retrospectiva), EXPL 2025–2026 (ya inspeccionado).

### 3.1 Hipótesis falsable de ejemplo: reversión tras |z|≥2 (SMA/σ 50)
H1 (todas las condiciones de régimen):

{prob_tab('H1')}

H4:

{prob_tab('H4')}

Lectura: a +1 R la probabilidad observada (≈43–49 %) queda por debajo o en el equilibrio sin costes (50 %) y el coste medio (0,02–0,05 R) la pone por debajo; la expectativa cambia de signo entre periodos. H4 fue positiva en VALID y ≈0 en EXPL: no hay persistencia. Intervalos de confianza: Wilson para probabilidades, bootstrap por bloques para la expectativa.

### 3.2 Expectativa conservadora media por familia (todas las variantes, k=1 R, régimen ALL)
{chr(10).join(fam_md)}

A reversión estadística · B continuación · C estructura · E comportamiento tras expansión. Sin familia con expectativa positiva y estable.

### 3.3 Sesiones y hora del día
`research/PHASE_E_HOURLY.csv`. Horas con efecto estadísticamente fuerte y de signo estable (11 h y 15 h negativas en los tres periodos; 20 h negativa solo en TRAIN/VALID; 22 h positiva), pero |media| ≤1,7 pb ≈ 0,2 pip por barra H1, al menos ~5 veces menor que el spread, y 20–22 h coincide con el rollover (liquidez mínima): no explotable. Es coherente con Breedon & Ranaldo (el efecto se consume en el spread).

## 4. Selección pre-registrada y robustez
Regla fijada antes de ver VALID/EXPL: por (hipótesis, TF, régimen) se elige el k con mayor expectativa conservadora en TRAIN (N≥100) y se evalúa en VALID y EXPL. Resultado: {chance}.
La única celda que pasa la regla básica (reversión z≥2 en H4 con KER alta, k=3) tiene P(éxito) de ~6–9 % (perfil de lotería), t_VALID=2,09 < t*={tstar:.2f}, y sus vecinas (z=1,5/2,5/3,0, otros k) cambian de signo entre periodos: no es una región estable. Estadística completa: `PHASE_E_SELECTION.csv`.

## 5. Optimización controlada (Fase 5): región de parámetros de S05 H4 (18 configuraciones)
Motor completo (3.000 USD, 0,5 %, estricto, spread, swap). Rejilla pequeña predefinida: ADX<25 sí/no × SL {{1,5; 2; 3}} ATR × duración {{12; 18; 30}} barras.

{chr(10).join(pv_md)}

Configuraciones con Exp R>0 en los tres periodos: **{allpos}/18** (con filtro ADX: {onpos}/9; sin filtro: {offpos}/9). Con el filtro, la región es estable en signo (Exp R ≈ +0,04…+0,20 en 2018–2026), pero con N≈85–105 por periodo cada celda es estadísticamente débil, y no es evidencia independiente: estos periodos ya se habían visto al definir L2. Sin filtro el edge desaparece (≈0). Se registraron las 18 configuraciones como intentos (sesgo de selección).

## 6. Costes (Fase D, ampliada)
Ver `docs/REMIX_EURUSD_PHASE_D_REPORT.md` §5 y `PHASE_D_COST_ANALYSIS.csv`: coste ex-ante = (spread de la barra de señal + 2 pts)/SL (sin spreads futuros); los filtros 0,05 R / 0,10 R reducen coste pero no crean ventaja bruta; estrés (spread×1,5 + 10 pts/lado) deja M15 en −0,33…−0,40 R/op.

## 7. Comparación V1 vs módulos V2 (3.000 USD, 0,5 %, estricto, EURUSDm)
V1 = S01 canónico (Python verificado contra MT5: 335/335 señales, entradas y lotes). Módulos V2 = pistas congeladas implementadas en el EA. EXPL = 2025-01→2026-10; POOL = 2018→2026-10. Diferencias de datos/ejecución: barras M15/H1/H4 con spread de barra (Python) frente a ticks reales sólo desde 2026 en MT5; H4 en Python usa las barras nativas de MT5 (verificadas); la comisión de la cuenta real no está verificada (0 supuesto).

{chr(10).join(cmp_md)}

**Conclusión de la comparación:** ninguna mejora de V2 sobre V1 es estadísticamente demostrable. En EXPL, L1 y L2 tienen mejor expectativa y menor drawdown que S01 pero con 48–53 operaciones; sus IC95 incluyen el cero. Una mejora histórica no es evidencia prospectiva. Las mejoras absolutas (decenas de USD al año) son inferiores a la incertidumbre de ejecución.

## 8. Fuentes externas (Fase 3)
`research/EXTERNAL_SOURCES.csv`: momentum FX con costes (Menkhoff et al.; BIS WP 366), patrones horarios EUR/USD (Breedon & Ranaldo), reversión intradía EURUSD (Wiśniewska). Sólo se leyeron resúmenes del buscador, no los textos completos; ninguna cifra de rentabilidad externa se importó. No se evaluaron estrategias de YouTube/GitHub (sin datos reproducibles ni costes) ni LONA (no conectado).

## 9. REMIX_EURUSD_V2.mq5
- Compilado con MetaEditor: **0 errores, 0 avisos**. `.ex5` generado. SHA-256 del fuente en `docs/V2_BUILD_INFO.json`.
- Módulos (uno a la vez; todos desactivados por defecto: `Module=NONE`, `EnableTrading=false`): S01 (referencia M15), S05/L2 (H4), S06/L3 (H4), S08/L4 (H4), L1 (H1). Exige el marco temporal de diseño (`RequireTimeframe`).
- Riesgo configurable (0,5 % por defecto, máx. 2 %), política estricta de lote mínimo, SL obligatorio (sin SL no se abre), TP configurable (retorno a la media o múltiplo de ATR), salida temporal, break-even y trailing ATR opcionales, control de spread (fracción del SL y puntos absolutos), control de deslizamiento (desviación en la orden + registro/cierre opcional), Magic Number, manejo de errores de orden, CSV de operaciones y de señales (carpeta Common\\Files), criterio `OnTester` penalizado (beneficio/DD × muestra).
- Seguridad: sólo con `MQL_TESTER` y cuenta no real; las llamadas de trading están sólo en `OpenTrade`, `ClosePosition`, `ModifySL` tras `TradingAllowed()` (verificado por `tests/test_ea_v2_static.py`).
- **No se ejecutó ningún backtest oficial de V2 en MT5:** un terminal aislado necesitaría iniciar sesión en el servidor de Exness (credenciales que no se usan ni se piden) y el terminal principal no se cierra. Los resultados «esperados» de Python por módulo están en `results/v2_expected/` para compararlos con el CSV del Tester. Instrucciones: `docs/V2_TESTER_INSTRUCTIONS.md`.

## 10. Estrategias descartadas / no demostradas
Ver `REMIX_V2_STRATEGY_MATRIX.csv` ({len(M)} filas). Descartadas: S02–S04 (y sus inversas en M15), S07, S10, S12, S08 H1, S09, la mayoría de S05/S06/S11 y todas las celdas de eventos con expectativa ≤0 en TRAIN o VALID. No demostradas (pistas): L1–L4 y la celda de reversión z H4. Aprobadas para producción: **ninguna**.

## 11. Limitaciones
Spread de barra (no por tick); ticks reales sólo desde 2026-01; comisión/swap de la cuenta real sin verificar; paridad de indicadores nuevos con `iRSI`/`iADX` sin verificar; EA V2 sin backtest oficial en MT5; H1 anterior a 2018 descartado por datos inválidos; una sola serie (EURUSDm), por lo que la potencia estadística es limitada.

## 12. Siguientes pasos
1. Ejecutar V2 en su Strategy Tester (L2, L1) y comparar con `results/v2_expected/` (paridad de señales y de resultados).
2. Mantener congeladas L1–L4 y evaluar una sola vez con datos posteriores a oct-2026 (≈14–51 operaciones/año ⇒ años para N≥100).
3. Si se desea más potencia estadística: replicar la metodología en otros pares solo con su autorización.
"""
(ROOT / "docs" / "REMIX_EURUSD_V2_RESEARCH_REPORT.md").write_text(doc, encoding="utf-8")

tester = """# Instrucciones para ejecutar REMIX_EURUSD_V2 en su Strategy Tester

El EA solo funciona en el Strategy Tester y **no opera por defecto**. Cada prueba carga un archivo `.set` de `mql5/sets/` que activa **un** módulo.

1. Copie `mql5/REMIX_EURUSD_V2.mq5` a `MQL5\\Experts\\REMIX\\` (ya está desplegado y compilado ahí si usó `scripts/06_compile_ea_v2.py`) y compílelo con MetaEditor (F7) si lo ha modificado.
2. MT5 → Ver → Probador de estrategias (Ctrl+R). Experto: `REMIX\\REMIX_EURUSD_V2`.
3. Símbolo `EURUSDm`. Marco temporal según el módulo: S01 → M15; S05/S06/S08 → H4; L1 → H1 (el EA se niega a arrancar con otro marco).
4. Periodo: 2025.01.01 – 2026.10.31 (comparable con Python). Segunda corrida opcional con ticks reales: 2026.01.02 – 2026.10.31 con «Cada tick basado en ticks reales». (El terminal solo conserva ticks reales desde 2026-01.)
5. Depósito 3000 USD, apalancamiento 1:500, optimización desactivada, forward desactivado.
6. En la pestaña Entradas → Cargar → elija el `.set`: `V2_S01_reference_M15.set`, `V2_S05_L2_H4.set`, `V2_S06_L3_H4.set`, `V2_S08_L4_H4.set` o `V2_L1_S03inv_H1.set`.
7. Inicie. Guarde el informe HTML/XLSX. El EA escribe `REMIX_V2_deals_*.csv` y `REMIX_V2_signals_*.csv` en `Common\\Files`.
8. Compare con `results/v2_expected/<módulo>_EXPL_expected_trades.csv` (operaciones esperadas de Python con 3000 USD): número de operaciones, hora de entrada, dirección, lotes y motivo de salida. Diferencias esperables: ticks generados en 2025, salida a mercado por tiempo/regla en el primer tick de la barra, y `iADX`/`iRSI` frente a las versiones de Python (paridad no verificada).
9. No active el EA en un gráfico normal: no abrirá nada (INIT_FAILED fuera del Tester).

Expectativa honesta: ningún módulo tiene ventaja demostrada; un resultado positivo aislado en el Tester no es evidencia prospectiva.
"""
(ROOT / "docs" / "V2_TESTER_INSTRUCTIONS.md").write_text(tester, encoding="utf-8")
import hashlib
sha = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
(ROOT / "docs" / "V2_BUILD_INFO.json").write_text(json.dumps({"ea": "mql5/REMIX_EURUSD_V2.mq5", "sha256_source": sha("mql5/REMIX_EURUSD_V2.mq5"), "compile": {"errors": 0, "warnings": 0},
                                                              "v1_ea_untouched_sha256": sha("mql5/REMIX_STRATEGY_RESEARCH_LAB_V1.mq5"), "date": "2026-11-09"}, indent=1), encoding="utf-8")
print("ok", len(doc))


"""Genera docs/REMIX_EURUSD_PHASE_D_REPORT.md (tablas automaticas desde PHASE_D_JOINED.csv) y research/PROSPECTIVE_FREEZE_2026-11-09.json"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
j = pd.read_csv(ROOT / "research/PHASE_D_JOINED.csv")
C = pd.read_csv(ROOT / "research/PHASE_D_COST_ANALYSIS.csv")
L = pd.read_csv(ROOT / "research/PHASE_D_LEAD_CHECK.csv")
Y = pd.read_csv(ROOT / "research/PHASE_D_LEAD_CHECK_BY_YEAR.csv")
meta = json.loads((ROOT / "research/PHASE_D_META.json").read_text())
N = len(j); tstar = float(np.sqrt(2 * np.log(N))); Ntot = N + 41; tstar_tot = float(np.sqrt(2 * np.log(Ntot)))

# ---------- congelacion prospectiva (pre-registro)
freeze = {
    "fecha_congelacion": "2026-11-09", "evaluacion_desde": "2026-11-01 (datos posteriores a oct-2026; no han intervenido en ninguna seleccion)",
    "regla": "UNA sola evaluacion por configuracion cuando haya N minimo; prohibido reoptimizar con esos datos; los parametros no pueden cambiar tras este archivo.",
    "criterio_exito_prospectivo": {"n_min": 100, "exp_R_neta_mayor_0": True, "pf_min": 1.15, "ic95_bloques_inferior_mayor_0": True, "coste_stress_exp_R_mayor_0": True},
    "nota_tamano": "Las pistas H4 generan ~14-51 operaciones/ano: alcanzar n=100 exigiria 3-5 anos de datos nuevos con un solo simbolo; evaluar antes solo como informativo.",
    "configuraciones": {
        "L1": {"tf": "H1", "base": "S03 canonico (EMA20/50/200, ADX14>25, SL1.5ATR, TP3ATR)", "transform": "long_inv", "geometry": "mirror"},
        "L2": {"tf": "H4", "strategy": "S05", "params": {"sma_n": 50, "z_th": 2.0, "trend_filter": True, "adx_max": 25.0, "atr_n": 14, "sl_atr": 2.0, "max_bars": 18}},
        "L3": {"tf": "H4", "strategy": "S06", "params": {"rsi_lo": 5, "rsi_hi": 95, "sma_n": 100, "sl_atr": 2.0, "tp_atr": 5.0, "max_bars": 20}},
        "L4": {"tf": "H4", "strategy": "S08", "params": {"ema_n": 20, "k": 2.0, "sl_atr": 1.5, "confirm": False, "regime": True, "adx_max": 25.0, "max_bars": 12}},
    },
}
fp = ROOT / "research/PROSPECTIVE_FREEZE_2026-11-09.json"
fp.write_text(json.dumps(freeze, indent=1, ensure_ascii=False), encoding="utf-8")
fz_hash = hashlib.sha256(fp.read_bytes()).hexdigest()


def fmt_ci(s):
    try:
        a, b = [float(x) for x in str(s).strip("[]").split(",")]
        return f"[{a:+.2f};{b:+.2f}]"
    except Exception:
        return "n/d"


def vtxt(v):
    return str(v).replace('"', "").replace("{", "").replace("}", "")[:46]


def table(df):
    out = ["| Estrategia | TF | Variante | N | WR % | PF | Exp R | DD % | IC95 (bloques) | t | p ctrl | RETRO: N / PF / Exp R | Decisión |", "|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---|---|"]
    for r in df.itertuples():
        pf = "-" if pd.isna(r.pf) else f"{r.pf:.2f}"
        cp = "-" if pd.isna(r.ctrl_p) else f"{r.ctrl_p:.2f}"
        retro = "-" if pd.isna(r.n_R) else f"{int(r.n_R)} / {r.pf_R:.2f} / {r.exp_R_R:+.3f}"
        out.append(f"| {r.strategy} | {r.tf} | {vtxt(r.variant)} | {int(r.n)} | {r.wr:.1f} | {pf} | {r.exp_R:+.3f} | {r.maxdd_pct:.1f} | {fmt_ci(r.ci_block)} | {r.t:+.2f} | {cp} | {retro} | {r.decision} |")
    return "\n".join(out)


inv, new = j[j.part == "INV"], j[j.part == "NEW"]
ip = inv.pivot_table(index=["strategy", "tf"], columns="variant", values="exp_R").round(3)
ipr = inv.pivot_table(index=["strategy", "tf"], columns="variant", values="exp_R_R").round(3)
order = ["A_orig", "B_inv", "B_inv_swap", "C_long", "D_short", "E_long_inv", "E_long_inv_swap", "F_short_inv", "F_short_inv_swap"]


def pv(p):
    p = p[order]
    rows = ["| Estr. / TF | " + " | ".join(order) + " |", "|---|" + "---:|" * len(order)]
    for (s, t), r in p.iterrows():
        rows.append(f"| {s} {t} | " + " | ".join(f"{v:+.3f}" for v in r.values) + " |")
    return "\n".join(rows)


co = C[(C.origin == "ORIG") & (C.period == "EXPL")]
cost_tab = ["| Estr. | TF | SL mediano (pips) | Coste est. (R) | % señales >0,05R | % >0,10R | Exp R base | Bruta (antes de costes) | Coste R/op | Exp R estrés | Exp R filtro 0,05R (N) | Exp R filtro 0,10R (N) |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
for r in co.itertuples():
    cost_tab.append(f"| {r.strategy} | {r.tf} | {r.sl_pips_median:.1f} | {r.est_cost_R_mean:.3f} | {r.share_gt_0p05*100:.0f} | {r.share_gt_0p10*100:.0f} | {r.expR_base:+.3f} | {r.gross_R:+.3f} | {r.cost_R:.3f} | {r.expR_stress:+.3f} | {r.expR_f05:+.3f} ({int(r.n_f05)}) | {r.expR_f10:+.3f} ({int(r.n_f10)}) |")
lead_tab = ["| Pista | Periodo | N | PF | Exp R | IC95 bloques | t | p control (300) | Exp R estrés |", "|---|---|---:|---:|---:|---|---:|---:|---:|"]
for r in L.itertuples():
    lead_tab.append(f"| {r.lead} | {r.period} | {int(r.n)} | {r.pf:.2f} | {r.exp_R:+.3f} | {fmt_ci(r.ci_block)} | {r.t:+.2f} | {r.ctrl_p:.3f} | {r.expR_stress:+.3f} |")
yy = Y.pivot_table(index="lead", columns="year", values="exp_R").round(2)
year_tab = ["| Pista | " + " | ".join(str(c) for c in yy.columns) + " |", "|---|" + "---:|" * len(yy.columns)] + [f"| {i} | " + " | ".join("" if pd.isna(v) else f"{v:+.2f}" for v in r.values) + " |" for i, r in yy.iterrows()]
dec = j.groupby(["part", "decision"]).size().unstack(fill_value=0)
best_t = j[j.n >= 30].t.max()

doc = f"""# REMIX EURUSD — Fase D: informe de investigación (2026-11-09)

**Alcance:** solo simulaciones (Python + datos Bid/Ask de barras y ticks del terminal, solo lectura). Sin órdenes, sin `order_send`, EA original intacto, terminal sin cerrar.
**Estatus de los datos:** EXPL = 2025-01→2026-10 (**ya inspeccionado**: exploratorio). RETRO = historia **anterior a 2025**, no inspeccionada hasta esta fase: H1/H4/D1 2018–2024 y M15 nov-2022→2024. No se seleccionó ningún parámetro con RETRO; sirve como réplica retrospectiva, **no** como evaluación prospectiva. La evaluación prospectiva (datos posteriores a oct-2026) queda congelada y sin usar (`research/PROSPECTIVE_FREEZE_2026-11-09.json`, SHA-256 `{fz_hash}`).

## 1. Resumen ejecutivo
- **Ninguna de las {N} configuraciones probadas alcanza la categoría «Prometedora».** {int(dec.loc['INV'].get('Descartada',0)+dec.loc['NEW'].get('Descartada',0))} descartadas, {int(dec.loc['INV'].get('No demostrada',0)+dec.loc['NEW'].get('No demostrada',0))} «no demostradas», {int(dec.loc['NEW'].get('Pendiente de datos',0))} pendientes de datos.
- Multiplicidad: {N} configuraciones en esta fase ({meta['n_runs']} ejecuciones = EXPL+RETRO) más 41 de la Fase C → ≈{Ntot} hipótesis; t máximo esperable solo por azar ≈ **{tstar_tot:.2f}**. El mayor t observado en EXPL (N≥30 operaciones) fue **{best_t:.2f}**: nada se distingue del azar tras corregir por pruebas.
- **Invertir señales no crea ventaja.** Las S02–S04 originales tienen rendimiento *bruto* ≈ 0 (±0,15 R); en M15 el coste (0,10–0,14 R por operación) explica casi toda la pérdida y **también** hunde a las versiones invertidas. Las pocas inversas positivas en EXPL (S03 H1, S04 H1) no se replican en RETRO.
- **Los costes sí son el obstáculo dominante en M15**; en H1/H4 pesan menos (0,02–0,06 R) pero el rendimiento bruto tampoco es positivo de forma fiable.
- **No hay candidatos para validar en MT5 todavía.** Solo 4 «pistas débiles» (positivas en EXPL y RETRO, sin significancia) quedan congeladas para evaluación prospectiva; el EA solo implementa S01–S04, y portar una pista al EA antes de que supere la prospectiva no está justificado.

## 2. Reglas de decisión (pre-registradas antes de ver resultados)
Prometedora: N≥100 en EXPL y RETRO; Exp R>0 en ambos; PF≥1,15 en ambos; Exp R sin las 5 mejores operaciones >0 en ambos; p de control aleatorio ≤0,10 en EXPL; ≥50 % de las variantes del grupo (estrategia, TF) con Exp R>0 en ambos periodos; ≥50 % de trimestres positivos. No demostrada: Exp R>0 en EXPL pero incumple algo. Descartada: Exp R≤0 en EXPL. Pendiente de datos: N<30 en algún periodo. (PF 1,30 es objetivo preferente; ninguna configuración con N≥100 en ambos periodos se acercó.)
Parámetros canónicos fijados a priori; las «variantes» son una rejilla pequeña y predefinida, no un barrido. Capital virtual 3.000 USD, riesgo 0,5 %, política estricta. Controles: {meta['controls_per_run']} sorteos con misma densidad de señales, misma proporción LONG/SHORT, mismos pares SL/TP, mismo riesgo y mismas reglas temporales (no replican salidas por indicador).

## 3. Inversión de S02, S03 y S04 (EXPL: Exp R por variante)
A original · B invertida (SL/TP iguales) · B_swap (SL↔TP) · C solo largos · D solo cortos · E largos invertidos · F cortos invertidos. Cada inversión se reconstruye como operación completa (entrada al ask/bid correcto, SL/TP, tamaño por riesgo, spread, swap); jamás se multiplicó un resultado por −1.

{pv(ip)}

Réplica en RETRO (mismas configuraciones, datos anteriores a 2025):

{pv(ipr)}

Lectura: B_inv en S03 H1 (+0,099 EXPL) → +0,006 en RETRO; S04 H1 (+0,032) → −0,060. Solo S03 H1 «largos invertidos» es positiva en ambos periodos (N=53 y 148; t=1,20 en EXPL; p control 0,14). Que la original pierda no implica que la inversa gane: la inversa paga los mismos costes.

## 4. Nuevas estrategias S05–S12 y tabla completa
S05 Z-score (H1/H4), S06 RSI-2+SMA100, S07 PDH/PDL (ruptura/barrida/retest; niveles solo del día anterior terminado), S08 Keltner, S09 momentum (D1 casi sin operaciones), S10 pullback EMA (H1 con filtro H4 sin lookahead), S11 Bollinger+RSI+ADX, S12 VWAP **proxy** (tick_volume; no es VWAP institucional) + pin bar. S09 D1 queda «pendiente de datos» (3–11 operaciones en EXPL). S12 pierde en ambos periodos (t=−2,9/−3,4 en EXPL); coste ≈0,19 R/op por SL de ~5,5 pips.

### 4.1 Tabla principal — nuevas estrategias (EXPL; réplica RETRO a la derecha)
{table(new)}

### 4.2 Tabla principal — señales invertidas / subconjuntos de S02–S04 (EXPL; réplica RETRO)
{table(inv)}

## 5. Costes (por qué S02–S04 pierden)
Coste ex-ante = (spread de la barra de señal + 2 pts de slippage estimado) / distancia SL: solo información disponible en la barra de señal (sin spreads futuros). Estrés = spread ×1,5 y 10 pts de slippage por lado.

{chr(10).join(cost_tab)}

- En M15 el SL mediano es 9,5–11,8 pips; el spread observado (≈8–9 pts) cuesta 0,11–0,14 R por operación y el 89–96 % de las señales supera 0,05 R. En H1 (SL 18–25 pips) el coste es 0,046–0,060 R.
- Antes de costes, S02/S04 rinden ≈0 R y S03 −0,04 a −0,15 R: **sin ventaja bruta que los costes destruyan**; no es «una ventaja que se pierde en fricciones».
- Los filtros 0,05R / 0,10R: reducen coste por operación pero eliminan la mayoría de señales (M15: 22–291 de 394–1.882) y **no producen Exp R positiva** en S02–S04; en nuevas estrategias M15 los resultados con filtro 0,05R tienen N=12–34 (no concluyentes). Los umbrales no se consideran óptimos ni validados.
- Estrés: M15 −0,33 a −0,40 R/op; H1 −0,17 a −0,28.
- Limitaciones: spread de barra (no por tick) en todo EXPL/RETRO; comisión/swap de la cuenta real no verificados; en RETRO se sustituyeron por la mediana {meta['data_notes']['M15_pre2025']['spread_zero_replaced_by_median'] + meta['data_notes']['H1_2018_2024']['spread_zero_replaced_by_median']} barras con spread=0 (datos inválidos) y se excluyeron {meta['data_notes']['H1_excluded_before_2018']['bars']} barras H1 anteriores a 2018 (cobertura incompleta y spread=0).

## 6. Pistas débiles y comprobación adicional (300 controles; sin variar parámetros)
{chr(10).join(lead_tab)}

Exp R por año:

{chr(10).join(year_tab)}

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
`research/PHASE_D_ALL_RUNS.csv`, `PHASE_D_INVERSE_STRATEGIES.csv`, `PHASE_D_NEW_STRATEGIES.csv`, `PHASE_D_COST_ANALYSIS.csv`, `PHASE_D_ROBUSTNESS.csv`, `PHASE_D_JOINED.csv`, `PHASE_D_LEAD_CHECK*.csv`, `PHASE_D_META.json`, `PROSPECTIVE_FREEZE_2026-11-09.json`; código `remix_lab/{{harness,strategies_d}}.py`, `research/{{run_phase_d,phase_d_build,phase_d_lead_check,phase_d_report}}.py`, `scripts/05_fetch_history_pre2025.py`; pruebas `tests/test_{{phase_d,indicators_d}}.py` (60 pruebas en total). Reproducción: `python -I -W ignore research\\run_phase_d.py` (≈25 min) → `phase_d_build.py` → `phase_d_lead_check.py` → `phase_d_report.py`. Semilla 12345.
"""
(ROOT / "docs" / "REMIX_EURUSD_PHASE_D_REPORT.md").write_text(doc, encoding="utf-8")
print("ok", len(doc), "chars; freeze sha", fz_hash)

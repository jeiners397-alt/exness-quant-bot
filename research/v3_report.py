"""Genera docs/REMIX_EURUSD_V3_REPORT.md, research/V3_FAMILY_COMPARISON.csv y docs/V3_TESTER_INSTRUCTIONS.md desde los resultados."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = pd.read_csv(ROOT / "research/V3_ALL_RUNS.csv")
WF = pd.read_csv(ROOT / "research/V3_WALKFORWARD_SUMMARY.csv")
WFY = pd.read_csv(ROOT / "research/V3_WALKFORWARD.csv")
DE = pd.read_csv(ROOT / "research/V3_D_EVENTS.csv")
DW = pd.read_csv(ROOT / "research/V3_D_WALKFORWARD.csv")
DB = pd.read_csv(ROOT / "research/V3_D_BACKTESTS.csv")
par = json.loads((ROOT / "research/PARITY_V2_1_OFFICIAL.json").read_text())
exp = json.loads((ROOT / "results/v3_expected/V3_expected_summary.json").read_text())
full = R[R.period == "FULL"].copy()
per = R.pivot_table(index="cid", columns="period", values="exp_R")[["TRAIN", "VALID", "EXPL"]]
full = full.merge(per, left_on="cid", right_index=True, suffixes=("", "_p"))
full["all3_pos"] = (full.TRAIN > 0) & (full.VALID > 0) & (full.EXPL > 0)
rows = []
for (fam, tf), g in full.groupby(["family", "tf"]):
    w = WF[(WF.family == fam) & (WF.tf == tf)]
    rows.append(dict(family=fam, tf=tf, configs=len(g), trades_min=int(g.n.min()), trades_max=int(g.n.max()), expR_median=round(g.exp_R.median(), 4), expR_best=round(g.exp_R.max(), 4), expR_worst=round(g.exp_R.min(), 4),
                     pf_median=round(g.pf.median(), 3), n_expR_pos=int((g.exp_R > 0).sum()), n_pos_all3_periods=int(g.all3_pos.sum()), t_max=round(g.t.max(), 2), ctrl_p_le_0p05=int((g.ctrl_p <= 0.05).sum()),
                     maxdd_median=round(g.maxdd_pct.median(), 1), wf_oos_n=int(w.n_oos.iloc[0]) if len(w) else None, wf_oos_expR=float(w.expR_oos.iloc[0]) if len(w) else None, wf_oos_pf=float(w.pf.iloc[0]) if len(w) else None))
F = pd.DataFrame(rows); F.to_csv(ROOT / "research/V3_FAMILY_COMPARISON.csv", index=False)


def md_family():
    out = ["| Familia | TF | Configs | Operaciones (rango) | Exp R mediana [peor; mejor] | PF mediano | Configs Exp R>0 | Positivas en los 3 periodos | t máx. | Configs p control≤0,05 | DD mediano % | Walk-forward OOS (N / Exp R / PF) |", "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in F.itertuples():
        wf = f"{r.wf_oos_n} / {r.wf_oos_expR:+.3f} / {r.wf_oos_pf:.2f}" if r.wf_oos_n else "-"
        out.append(f"| {r.family} | {r.tf} | {r.configs} | {r.trades_min}–{r.trades_max} | {r.expR_median:+.3f} [{r.expR_worst:+.3f}; {r.expR_best:+.3f}] | {r.pf_median:.2f} | {r.n_expR_pos} | {r.n_pos_all3_periods} | {r.t_max:+.2f} | {r.ctrl_p_le_0p05} | {r.maxdd_median} | {wf} |")
    return "\n".join(out)


def md_configs():
    out = ["| Fam. | TF | Configuración | N | WR % | PF | Exp R | IC95 (bloques) | t | DD % | Trim.+ | TRAIN | VALID | EXPL | sin top-5 | p ctrl |", "|---|---|---|---:|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---:|---:|"]
    for r in full.sort_values(["family", "tf"]).itertuples():
        p = r.params.replace('"', "").replace("{", "").replace("}", "")
        ci = str(r.ci_block).strip("[]").split(",")
        out.append(f"| {r.family} | {r.tf} | {p} | {r.n} | {r.wr} | {r.pf:.2f} | {r.exp_R:+.3f} | [{float(ci[0]):+.2f};{float(ci[1]):+.2f}] | {r.t:+.2f} | {r.maxdd_pct:.1f} | {r.q_pos}/{r.q_total} | {r.TRAIN:+.3f} | {r.VALID:+.3f} | {r.EXPL:+.3f} | {r.exp_R_ex5:+.3f} | {r.ctrl_p:.2f} |")
    return "\n".join(out)


dp = DE[DE.cell.isin(["ALL", "RANGE(ker<p33 & chop>p67)", "ker_LOW", "chop_HIGH", "adx_LOW", "volpct_LOW"])].pivot_table(index=["tf", "cell"], columns="period", values="E_cons")[["TRAIN", "VALID", "EXPL"]].round(3)
dn = DE[DE.cell.isin(dp.index.get_level_values(1))].pivot_table(index=["tf", "cell"], columns="period", values="n")[["TRAIN", "VALID", "EXPL"]]
dpw = DE[DE.cell.isin(dp.index.get_level_values(1))].pivot_table(index=["tf", "cell"], columns="period", values="p_win")[["TRAIN", "VALID", "EXPL"]]
d_md = ["| TF | Condición (umbrales = terciles de los eventos TRAIN) | P(+1R antes de −1R) TRAIN / VALID / EXPL | N TRAIN / VALID / EXPL | Exp R cons. TRAIN | VALID | EXPL |", "|---|---|---|---|---:|---:|---:|"]
for (tf, c), r in dp.iterrows():
    d_md.append(f"| {tf} | {c} | {dpw.loc[(tf, c), 'TRAIN']:.3f} / {dpw.loc[(tf, c), 'VALID']:.3f} / {dpw.loc[(tf, c), 'EXPL']:.3f} | {int(dn.loc[(tf, c), 'TRAIN'])} / {int(dn.loc[(tf, c), 'VALID'])} / {int(dn.loc[(tf, c), 'EXPL'])} | {r.TRAIN:+.3f} | {r.VALID:+.3f} | {r.EXPL:+.3f} |")
dbf = DB[DB.period == "FULL"]
dper = DB.pivot_table(index=["tf", "filtro"], columns="period", values="exp_R")[["TRAIN", "VALID", "EXPL"]]
db_md = ["| TF | Filtro | N | WR % | PF | Exp R | IC95 | t | DD % | Neto USD | sin top-5 | TRAIN | VALID | EXPL | p ctrl |", "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
for r in dbf.itertuples():
    ci = str(r.ci_block).strip("[]").split(",")
    pr = dper.loc[(r.tf, r.filtro)]
    db_md.append(f"| {r.tf} | {r.filtro} | {r.n} | {r.wr} | {r.pf:.2f} | {r.exp_R:+.3f} | [{float(ci[0]):+.2f};{float(ci[1]):+.2f}] | {r.t:+.2f} | {r.maxdd_pct:.1f} | {r.net_usd:+.0f} | {r.exp_R_ex5:+.3f} | {pr.TRAIN:+.3f} | {pr.VALID:+.3f} | {pr.EXPL:+.3f} | {r.ctrl_p:.2f} |")
dwf = DW.copy()
oos_h4 = dwf[dwf.tf == "H4"]; oos_h1 = dwf[dwf.tf == "H1"]
wf_txt = lambda g: f"N={int(g.n_test.sum())}, Exp R ponderada {np.average(g.E_test.fillna(0), weights=g.n_test):+.3f} (todas las condiciones del mismo periodo: {np.average(g.E_all, weights=g.n_all):+.3f})"
tmax_phase = float(max(full.t.max(), DB[DB.period == 'FULL'].t.max()))
n_phase = len(full) + int(DE[['tf', 'cell']].drop_duplicates().shape[0]) + len(dbf)
tstar_phase = float(np.sqrt(2 * np.log(n_phase))); tstar_all = float(np.sqrt(2 * np.log(n_phase + 41 + 100 + 700)))
a_best = full[full.family == "A"].sort_values("exp_R", ascending=False).iloc[0]
d3 = dbf[(dbf.tf == "H4") & dbf.filtro.str.startswith("D3")].iloc[0]
sha = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

doc = f"""# REMIX EURUSD V3 — informe cuantitativo (2026-11-09)

**Solo investigación y simulación. Ninguna estrategia está aprobada para producción.** Capital virtual 3.000 USD, riesgo 0,5 %, política estricta, compuertas de spread del EA (0,15×SL y 30 pts), filtro de coste ex-ante 0,10 R. 2025-01→2026-10 está **ya inspeccionado** (exploratorio); 2018–2024 son réplicas retrospectivas. El periodo prospectivo congelado no se ha usado.

## 1. Auditoría del resultado oficial de V2.1
- **Paridad:** 27/27 operaciones coinciden entre el Tester y Python (dirección, lotes, precio de entrada, motivo y barra de salida); neto {par['net_mt5']} vs {par['net_py']} USD, swaps {par['swap_mt5']} vs {par['swap_py']}. Esto confirma las correcciones de la fase anterior (`docs/PARITY_V2_L2_REPORT.md`).
- **Indicadores vela a vela (2.693 barras, `scripts/compare_bar_diag.py`):** ATR, SMA (manual e `iMA`), σ y z-score coinciden a ≤5·10⁻⁷; **+DI/−DI/ADX del `iADX` nativo coinciden con la fórmula EMA(2/(n+1)) (mediana 2,6·10⁻⁷; Wilder difiere hasta 32 pts)**; 29 de 2.693 barras (1,1 %) tienen diferencia de ADX >0,01 en un episodio aislado (24–26-oct-2025) sin efecto en ninguna señal.
- **Concentración:** la mejor operación ({par['best_trade']['entry']}, +{par['best_trade']['net']} USD) es el **{par['best_trade_share_of_net_pct']} %** del neto; sin ella el neto es **{par['net_without_best']:+.2f} USD**, sin las cinco mejores **{par['net_without_best5']:+.2f} USD**; 2025: 14 operaciones, +26,01 USD; 2026: 13 operaciones, +1,31 USD. **L2 queda como no demostrada y dependiente de un outlier.**

## 2. Qué se probó (todas las configuraciones se registran)
Rejilla **predefinida**, sin barrido: A (False Breakout) 16 configuraciones, B (Volatility Momentum) 20, D (Regímenes) 14 celdas de condición × 2 TF + 8 backtests. Cada configuración se ejecutó **una vez** sobre todo el periodo; periodos, walk-forward y controles salen de esas operaciones. Controles aleatorios: 100 sorteos con la misma densidad de señales, proporción LONG/SHORT, pares SL/TP y horas. Multiplicidad: {n_phase} configuraciones/celdas en esta fase (t máximo esperable por azar ≈ {tstar_phase:.2f}); acumulando fases anteriores (~{n_phase + 841}) ≈ {tstar_all:.2f}. **El mayor t de la fase es {tmax_phase:.2f}.**
Periodos H1: TRAIN 2018–21 | VALID 2022–24 | EXPL 2025–26. M15 (datos desde nov-2022): TRAIN nov-22–2023 | VALID 2024 | EXPL 2025–26. Walk-forward: pliegues anuales expansivos; cada pliegue elige la configuración con mejor R medio **anterior** (N≥30) y se evalúa en el año siguiente.

## 3. Tabla comparativa de las cuatro estrategias
{md_family()}

| Estrategia | Estado | Motivo |
|---|---|---|
| **A False Breakout Reversal** | **Sin ventaja demostrada** | {int(F[F.family=='A'].n_expR_pos.sum())} de {int(F[F.family=='A'].configs.sum())} configuraciones con Exp R>0 (mejor: {a_best.exp_R:+.3f} R, t={a_best.t:+.2f}); walk-forward OOS H1 {WF[(WF.family=='A')&(WF.tf=='H1')].expR_oos.iloc[0]:+.3f} R (N={int(WF[(WF.family=='A')&(WF.tf=='H1')].n_oos.iloc[0])}), M15 {WF[(WF.family=='A')&(WF.tf=='M15')].expR_oos.iloc[0]:+.3f} R |
| **B Volatility Momentum** | **Sin ventaja demostrada (descartada)** | {int(F[F.family=='B'].n_expR_pos.sum())} de {int(F[F.family=='B'].configs.sum())} con Exp R>0 y ninguna significativa; una gran vela no genera continuación rentable tras costes; OOS H1 {WF[(WF.family=='B')&(WF.tf=='H1')].expR_oos.iloc[0]:+.3f} R, M15 {WF[(WF.family=='B')&(WF.tf=='M15')].expR_oos.iloc[0]:+.3f} R |
| **C Macro News** | **Pendiente de datos** | No existe calendario histórico con marcas temporales verificables y valores de primera publicación en este entorno (el CSV de noticias de Exness extraído estaba vacío; la API Python de MT5 no expone el calendario económico). Se dejó el validador `remix_lab/news.py` y el esquema exigido; el EA rechaza este módulo |
| **D Regime Conditional Reversal** | **Requiere investigación (pista débil), no demostrada** | La condición KER bajo + Choppiness alto en H4 es la única positiva en los tres periodos (ver §5) pero IC95 incluye 0, N=148 en 8,8 años (≈17/año), y su versión de eventos no se replica con otro diseño de salida |

## 4. Familias A y B — las 36 configuraciones
{md_configs()}

Lectura: la mediana de Exp R de A es {F[F.family=='A'].expR_median.median():+.3f} R y la de B {F[F.family=='B'].expR_median.median():+.3f} R; con 100–3.300 operaciones por configuración el IC de la expectativa es de ±0,05–0,10 R, de modo que lo positivo es indistinguible de cero y casi siempre cambia de signo entre periodos. Las configuraciones con p de control ≤0,05 ({int(full.ctrl_p.le(0.05).sum())} de {len(full)}) son las esperables por azar entre {len(full)} pruebas. Frecuencia: A/H1 genera 536–2.545 operaciones en 8,8 años (≈120–580 por 2 años; las configuraciones de ≤1.300 operaciones caen en el rango exploratorio de 100–300 por 2 años) pero sin ventaja.

**Gestión de posiciones (SL estructural/ATR, TP, trailing, BE, tiempo):** el SL estructural vs ATR se comparó dentro de la rejilla (columna `sl`); las demás variantes (trailing, break-even, salida por estructura) **no se ejecutaron** porque la orden pide probarlas «únicamente para hipótesis que justifiquen la prueba» y ninguna A/B/D presenta ventaja que gestionar (la Fase C ya mostró que BE/trailing no rescatan una expectativa nula).

## 5. Estrategia D — condiciones de régimen (reversión tras |z|≥2)
Pregunta falsable: ¿mejora alguna condición observable (KER10, Choppiness14, ADX14 (fórmula MT5), percentil de volatilidad) la probabilidad de reversión? Umbrales = terciles de los eventos TRAIN; SL 1,5 ATR; cota conservadora.

{chr(10).join(d_md)}

Walk-forward por celda (elige la mejor celda con datos anteriores y la aplica el año siguiente): H1: {wf_txt(oos_h1)}; H4: {wf_txt(oos_h4)}. **Elegir condición con datos pasados no mejora la expectativa fuera de muestra.**

Backtests completos (S05: z=2, SL 2 ATR, TP = retorno a la media, `max_bars` 48/18; filtros pre-registrados):

{chr(10).join(db_md)}

H4 «RANGE» (D3): {int(d3.n)} operaciones, PF {d3.pf:.2f}, {d3.exp_R:+.3f} R, IC95 {d3.ci_block}, t={d3.t:.2f}, p de control {d3.ctrl_p:.2f}, DD {d3.maxdd_pct:.1f} %, sin las cinco mejores {d3.exp_R_ex5:+.3f} R; positiva en los tres periodos (TRAIN en parte in-sample porque define los umbrales). Pero en el diseño de eventos (SL 1,5 ATR, barrera +1R) el mismo régimen H4 es negativo en VALID y EXPL: **la «ventaja» depende de la estructura de salida**, señal de fragilidad. Sigue como hipótesis a validar con datos nuevos, no como estrategia.

## 6. Descartadas / que merecen continuar
- **Descartadas:** B en todas sus configuraciones; A/M15; A/H1 con SL ATR y niveles asiáticos con confirmación de 1 barra; D en H1 (negativa con cualquier filtro).
- **Merecen continuar (solo como hipótesis, sin afirmar ventaja):** D3 H4 (régimen de baja eficiencia + alta choppiness), A/H1 PDH/PDL con SL estructural y confirmación en 1 barra (la mejor de A: +0,010 R, p de control 0,02, pero TRAIN −0,054 y EXPL −0,014 → inestable) y la ya congelada L1–L4. Ninguna cumple el criterio de «prometedora».
- **Pendiente de datos:** C (calendario macro verificable con primera publicación).

## 7. REMIX_EURUSD_V3.mq5
Compilado con MetaEditor: **0 errores, 0 avisos** (SHA-256 fuente `{sha('mql5/REMIX_EURUSD_V3.mq5')}`). Módulos A, B, D activables individualmente (`Module`), C bloqueado (INIT_FAILED con mensaje); **todos desactivados por defecto** (`Module=NONE`, `EnableTrading=false`). Solo Tester, SL obligatorio, lote estricto, control de spread/coste, BE y trailing opcionales, CSV de operaciones y de señales (se reinician en cada corrida; en V2.1 se acumulaban). V1 (`1c327de0…`), V2 (`9908279f…`) y V2.1 (`9a5be44f…`) **intactos** (verificado por hash en `tests/test_v3.py`).
Archivos `.set`: `mql5/sets/V3_A_H1_PD_struct.set`, `V3_B_H1_impulse_k2_struct.set`, `V3_D_H4_regime.set`. Operaciones esperadas de Python en 2025-01→2026-10 (no son resultados de MT5): A/H1 {exp['A_H1_PD_struct']['n']} operaciones, {exp['A_H1_PD_struct']['net_usd']:+.2f} USD, PF {exp['A_H1_PD_struct']['pf']}; B/H1 {exp['B_H1_impulse_k2_struct']['n']}, {exp['B_H1_impulse_k2_struct']['net_usd']:+.2f} USD, PF {exp['B_H1_impulse_k2_struct']['pf']}; D/H4 {exp['D_H4_regime']['n']}, {exp['D_H4_regime']['net_usd']:+.2f} USD, PF {exp['D_H4_regime']['pf']}. La paridad MT5 de estos módulos **no está verificada** (el EA V3 no se ha ejecutado en el Tester).

## 8. Limitaciones y pasos
Spread de barra (el primer tick de reapertura de fin de semana tiene spread mayor); ticks reales solo desde 2026; comisión de la cuenta real sin verificar; periodo EXPL contaminado; sin datos macro. Siguiente: (1) ejecutar los `.set` V3 en su Tester y comparar con `results/v3_expected/`; (2) mantener congeladas L1–L4; (3) conseguir un calendario macro verificable para C; (4) no seguir optimizando A/B.
"""
(ROOT / "docs" / "REMIX_EURUSD_V3_REPORT.md").write_text(doc, encoding="utf-8")
(ROOT / "docs" / "V3_TESTER_INSTRUCTIONS.md").write_text("""# Prueba de REMIX_EURUSD_V3 en su Strategy Tester

1. `mql5/REMIX_EURUSD_V3.mq5` está desplegado y compilado en `MQL5\\Experts\\REMIX\\` (0 errores/0 avisos).
2. Probador (Ctrl+R) → Experto `REMIX\\REMIX_EURUSD_V3`; símbolo `EURUSDm`; periodo 2025.01.01 – 2026.11.01; depósito 3000 USD; 1:500; optimización y forward desactivados; «Cada tick» (ticks reales opcionales).
3. Entradas → Cargar uno de `mql5/sets/`: `V3_A_H1_PD_struct.set` (marco **H1**), `V3_B_H1_impulse_k2_struct.set` (**H1**), `V3_D_H4_regime.set` (**H4**). El EA se niega a arrancar con otro marco. El módulo C no opera (pendiente de datos).
4. Salidas en `Common\\Files`: `REMIX_V3_deals_M0X_EURUSDm_PERIOD_*.csv` y `REMIX_V3_signals_*.csv`.
5. Compare con `results/v3_expected/V3_<modulo>_expected_trades.csv` (Python). La paridad de V3 aún no está verificada: las diferencias iniciales son información, no un fallo.
6. Ningún módulo tiene ventaja demostrada; un resultado positivo aislado no es evidencia.
""", encoding="utf-8")
print(F.to_string(index=False)); print("ok", len(doc))


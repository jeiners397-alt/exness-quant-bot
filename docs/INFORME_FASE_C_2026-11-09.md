# Informe Fase C (parcial) — 2026-11-09

Estado: **iniciada; completadas la auditoría de S01, MAE/MFE, calidad de datos y primera comparación de salidas.** Detalle y cifras: `research/S01_EXIT_DIAGNOSTICS.md`.

| Entregable | Estado | Archivos |
|---|---|---|
| A. Auditoría S01 | Hecho | `research/s01_audit.py`, `S01_TRADES_RECONSTRUCTED.csv`, `S01_AUDIT_STATS.json` |
| B. MAE/MFE | Hecho (153 con ticks reales; 182 con cota por barras) | `S01_MAE_MFE_ANALYSIS.csv`, `s01_mae_mfe.py` |
| C. Variantes de salida (V0–V5) | Hecho a resolución M15 conservadora; **falta repetir con ticks (2026)** | `remix_lab/exit_variants.py`, `S01_EXIT_VARIANTS_*.csv/json` |
| D. S02–S04 | Pendiente (ya implementadas en Python y en el EA; sin evaluar con la metodología nueva) | — |
| E. Regímenes | Pendiente | — |
| F. Paridad Python–MT5 | Parcial: salidas V0 reproducen 335/335 motivos; **falta paridad de señales** (entradas/hora/precio Python vs Tester) | `S01_EXIT_VARIANTS_PARITY.json` |
| G. Estadísticas | S01: exp. +0,029 R, t=0,52, IC95 [−0,09 ; +0,14] | `S01_AUDIT_STATS.json` |
| H. Registro | 10 comparaciones de variantes contra V0 (+ V0). Sin selección de parámetros | `S01_EXIT_VARIANTS_RESULTS.csv` |
| I. Respaldos | Pendiente (Drive para escritorio) | `backup/BACKUP_QUEUE.csv` |

## Hechos clave
1. Los 117 cierres sin etiqueta son horarios (17:00:00–17:00:06; código del EA verificado).
2. TP+SL pierde porque P(TP)=37,6 % < 40 % (equilibrio con RR 1,5). El resultado final lo sostienen las salidas horarias (+0,19 R medio), que son las operaciones supervivientes.
3. No hay ventaja demostrada: IC95 de la expectativa incluye 0.
4. El terminal solo tiene ticks reales desde 2026-01-01; 2025 se simuló con ticks generados. Spread de ticks reales = 8 puntos constante.
5. Ninguna variante de salida (BE, trailing ATR/estructural, horarias, parcial) mejora a V0 significativamente a resolución M15.
6. El histórico completo (incl. jul–oct 2026) ya no es un holdout virgen. Nuevo holdout = datos posteriores a 2026-10-31 (prospectivo).

## Próximos pasos propuestos
1. Repetir V1–V5 con ticks reales en las 153 operaciones de 2026.
2. Paridad de señales Python↔Tester (S01, mismo capital 3.000 USD).
3. S02–S04 y controles aleatorios con la misma metodología (R, IC por bloques, nº de pruebas).
4. Clasificador de régimen causal y comparación A/B/C/D.
5. Recolección prospectiva: dejar acumular datos nuevos desde 2026-11-01 para la Fase E.

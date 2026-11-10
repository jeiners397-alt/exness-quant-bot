# V7 — Informe de validación (lote 1)

## Regla de selección (fijada antes de ver resultados)
Candidato: expectativa neta IS > 0 con t ≥ 2 y n_IS ≥ 100. Confirmación OOS: expectativa > 0, t ≥ 1,65, n ≥ 50. Clase B solo si además pasa la corrección por múltiples pruebas en IS (t ≥ √(2 ln N)), sobrevive a costes ×1,5 y el IC95 OOS excluye 0. Clase A: **no asignable** — no existen datos independientes (todo 2024-01 → 2026-10 se usó en V4/V5/V7). IS = hasta 2025-06-30, OOS = desde 2025-07-01.

## Resultados
| Lote | N pruebas | t\* | Candidatos IS | Confirmados OOS | Pasan multiplicidad | Clases |
|---|---|---|---|---|---|---|
| M15 | 1.200 | 3,77 | 0 | 0 | 0 | D 1.116, C 84 |
| H1 | 1.000 | 3,72 | 2 | 1 | 0 | D 702, C 208, F 90 |
| Combinado | 2.200 | 3,92 | 2 | 1 | 0 | ninguna A/B |

Los dos candidatos H1 son la misma regla (XAUUSDm, ruptura de 96 velas con cierre fuera, operada en continuación; TP 1,5R y 3R): t_IS 2,18/2,04, t_OOS 1,46/1,66, n 161/159. Con 1.000 pruebas se esperan ≈ 25 con p<0,025 unilateral por azar; sin corrección, esta no es distinguible del azar. Estado: **clase C — hipótesis para validación prospectiva**.

## Controles aplicados
Sin look-ahead (entrada en la apertura siguiente; pivotes confirmados con retardo); control aleatorio por hora y tercil de ER (100 sorteos); separación temporal IS/OOS; sensibilidad de coste ×1,5/×2/×3 (lineal, exacta porque el SL de medición es 1 ATR); registro completo de las 2.200 pruebas (`V7_EXPERIMENT_REGISTER*.csv`); eventos con enfriamiento de 12 velas para reducir solapamiento (el solapamiento residual infla t ligeramente).

## No aplicado todavía
Walk-forward con reoptimización, bootstrap por bloques y Monte Carlo (no hay estrategia que remuestrear), validación en MT5 con ticks reales, test de esfuerzo. **Reserva prospectiva**: datos desde 2026-11-01 sin usar (≈ 8 días hoy, insuficientes: la regla XAU H1 produce ≈ 0,3 operaciones por día calendario, o sea ~2–3 operaciones). Se necesitan ≈ 6–12 meses de datos nuevos (≥ 100 operaciones) para una validación con potencia razonable.

# Verificación del escáner oficial de MT5 (Optimization=3)

Fuente: https://www.metatrader5.com/en/terminal/help/start_advanced/start — `Optimization`: 0 desactivada, 1 completa, 2 genética, **3 "All Symbols Selected in Market Watch"**.

## Qué se implementó (`automation/mt5_market_scanner.py`)
1. Deja en Market Watch solo los símbolos pedidos (`symbol_select`) y verifica la lista con `symbols_get()`.
2. Escribe el `.ini` oficial (`[Tester]` con `Optimization=3`, Expert, Period, fechas, depósito, modelo; `[TesterInputs]`) + `.set`.
3. Lanza la instancia aislada, vigila el fin, cuenta símbolos procesados y archivos `.opt`.

## Prueba real (F2 M15, 2026-01-02→2026-03-01, 4 símbolos pedidos)
| Verificación | Resultado |
|---|---|
| El INI con `Optimization=3` es aceptado | **SÍ**: el Tester arrancó en modo optimización y creó `Tester\cache\REMIX_V5_GENERIC.all_symbols.M15.20260102.20260301.12.<hash>.opt` |
| Símbolos del Market Watch = los pedidos | **NO**: pedí 4, quedaron **83** (`exact_match=false`). La API deselecciona de forma asíncrona y MT5 mantiene seleccionados ~80 símbolos de conversión de divisas (`USD*`) necesarios para calcular margen/beneficio. Con reintentos el resultado fue el mismo |
| Símbolos procesados | el escáner recorrió el Market Watch completo (≥40 símbolos procesados en el log antes de cortarlo, p. ej. `USDKWDm`, `XNIUSDm`, `XPBUSDm`) descargando historial de cada uno: lento (≈15 s por símbolo) e incontrolable |
| Métricas recuperables | solo el `.opt` binario de la caché (formato no documentado); **no se generan informes HTML ni CSV por símbolo**; el log no imprime PF/neto por pasada |

## Decisión
El escáner oficial **no cumple** el requisito de "producir resultados equivalentes y auditables" (no aísla los símbolos ni exporta métricas). Se usa el **método alternativo exigido**: una ejecución oficial por símbolo con el ejecutor V4 (`automation/multi_market_batch_runner.py`), que produce informe HTML, `trades.csv`, `stats.json` y `.ini/.set` por prueba y registra símbolo y timeframe leídos del log del EA (verificación de que el cambio de mercado y de timeframe es real: 79/79 filas coinciden).

Evidencia: `results/v5_scanner/SCAN_PROBE_F2_M15_*` (`.ini`, lista de Market Watch, log del Tester).

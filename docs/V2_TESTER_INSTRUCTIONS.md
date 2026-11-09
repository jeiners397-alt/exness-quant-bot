# Instrucciones para ejecutar REMIX_EURUSD_V2 en su Strategy Tester

El EA solo funciona en el Strategy Tester y **no opera por defecto**. Cada prueba carga un archivo `.set` de `mql5/sets/` que activa **un** módulo.

1. Copie `mql5/REMIX_EURUSD_V2.mq5` a `MQL5\Experts\REMIX\` (ya está desplegado y compilado ahí si usó `scripts/06_compile_ea_v2.py`) y compílelo con MetaEditor (F7) si lo ha modificado.
2. MT5 → Ver → Probador de estrategias (Ctrl+R). Experto: `REMIX\REMIX_EURUSD_V2`.
3. Símbolo `EURUSDm`. Marco temporal según el módulo: S01 → M15; S05/S06/S08 → H4; L1 → H1 (el EA se niega a arrancar con otro marco).
4. Periodo: 2025.01.01 – 2026.10.31 (comparable con Python). Segunda corrida opcional con ticks reales: 2026.01.02 – 2026.10.31 con «Cada tick basado en ticks reales». (El terminal solo conserva ticks reales desde 2026-01.)
5. Depósito 3000 USD, apalancamiento 1:500, optimización desactivada, forward desactivado.
6. En la pestaña Entradas → Cargar → elija el `.set`: `V2_S01_reference_M15.set`, `V2_S05_L2_H4.set`, `V2_S06_L3_H4.set`, `V2_S08_L4_H4.set` o `V2_L1_S03inv_H1.set`.
7. Inicie. Guarde el informe HTML/XLSX. El EA escribe `REMIX_V2_deals_*.csv` y `REMIX_V2_signals_*.csv` en `Common\Files`.
8. Compare con `results/v2_expected/<módulo>_EXPL_expected_trades.csv` (operaciones esperadas de Python con 3000 USD): número de operaciones, hora de entrada, dirección, lotes y motivo de salida. Diferencias esperables: ticks generados en 2025, salida a mercado por tiempo/regla en el primer tick de la barra, y `iADX`/`iRSI` frente a las versiones de Python (paridad no verificada).
9. No active el EA en un gráfico normal: no abrirá nada (INIT_FAILED fuera del Tester).

Expectativa honesta: ningún módulo tiene ventaja demostrada; un resultado positivo aislado en el Tester no es evidencia prospectiva.

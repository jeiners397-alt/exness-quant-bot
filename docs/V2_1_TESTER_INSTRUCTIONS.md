# Prueba oficial de REMIX_EURUSD_V2_1 en su Strategy Tester

1. `mql5/REMIX_EURUSD_V2_1.mq5` ya está desplegado y compilado en `MQL5\Experts\REMIX\` (0 errores, 0 avisos). Si lo recompila: MetaEditor → F7.
2. Probador de estrategias (Ctrl+R) → Experto `REMIX\REMIX_EURUSD_V2_1`.
3. Símbolo `EURUSDm`, marco **H4**, periodo **2025.01.01 – 2026.11.01**, modelo «Cada tick» (puede usar «Cada tick basado en ticks reales»; en 2025 el terminal generará ticks), depósito **3000 USD**, apalancamiento 1:500, optimización y forward **desactivados**.
4. Pestaña Entradas → Cargar → `mql5/sets/V2_1_S05_L2_H4.set` (Module=5, z=2,0, SMA 50, ADX<25, SL 2 ATR, máx. 18 barras, riesgo 0,5 %, política estricta, trailing y break-even desactivados, `ExportBarDiag=true`, `RetryFailedClose=false`).
5. Inicie. Guarde el informe (xlsx/html).
6. Archivos que el EA escribe en `Common\Files`:
   - `REMIX_V21_deals_M05_EURUSDm_PERIOD_H4.csv` (operaciones),
   - `REMIX_V21_signals_M05_EURUSDm_PERIOD_H4.csv` (decisiones y motivos de rechazo),
   - `REMIX_V21_bars_M05_EURUSDm_PERIOD_H4.csv` (por barra: ATR, SMA manual e iMA, σ, z, ADX, +DI, −DI, señal, motivo).
7. Compare:
   - `python scripts/compare_bar_diag.py "<ruta>\REMIX_V21_bars_M05_EURUSDm_PERIOD_H4.csv"` → diferencias vela a vela de ATR, SMA, z y ADX (e indica si el `iADX` nativo coincide con la fórmula EMA o con Wilder).
   - Operaciones: `results/v2_1_expected/V2_1_S05_L2_H4_expected_trades.csv` (Python esperaba 27 operaciones, +27,30 USD, PF 1,18 con el modelo de sesión).
8. No lo active en un gráfico normal: se niega a arrancar fuera del Tester.

Notas: el resultado de V2.1 no es evidencia de ventaja; L2 sigue sin ventaja demostrada. Si el diario del Tester muestra `[Market closed]` en cierres de domingo, es el comportamiento ya medido; póngale `RetryFailedClose=true` para que reintente (cambia la paridad con Python).

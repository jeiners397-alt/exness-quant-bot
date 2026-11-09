# Prueba de REMIX_EURUSD_V3 en su Strategy Tester

1. `mql5/REMIX_EURUSD_V3.mq5` está desplegado y compilado en `MQL5\Experts\REMIX\` (0 errores/0 avisos).
2. Probador (Ctrl+R) → Experto `REMIX\REMIX_EURUSD_V3`; símbolo `EURUSDm`; periodo 2025.01.01 – 2026.11.01; depósito 3000 USD; 1:500; optimización y forward desactivados; «Cada tick» (ticks reales opcionales).
3. Entradas → Cargar uno de `mql5/sets/`: `V3_A_H1_PD_struct.set` (marco **H1**), `V3_B_H1_impulse_k2_struct.set` (**H1**), `V3_D_H4_regime.set` (**H4**). El EA se niega a arrancar con otro marco. El módulo C no opera (pendiente de datos).
4. Salidas en `Common\Files`: `REMIX_V3_deals_M0X_EURUSDm_PERIOD_*.csv` y `REMIX_V3_signals_*.csv`.
5. Compare con `results/v3_expected/V3_<modulo>_expected_trades.csv` (Python). La paridad de V3 aún no está verificada: las diferencias iniciales son información, no un fallo.
6. Ningún módulo tiene ventaja demostrada; un resultado positivo aislado no es evidencia.

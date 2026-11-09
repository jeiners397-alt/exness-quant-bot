# T001 — S01 London Breakout · EURUSDm · M15 · 2025.01.01–2025.03.31 · ticks reales · política estricta

**Estado: NO EJECUTADO (bloqueado por entorno). Resultado: ninguno. No se inventa ni se extrapola.**

- Fecha: 2026-11-09 (UTC). INI generado por `scripts/04_run_tester.py` (`T001_S01_EURUSDm_M15_strict.ini`, UTF-16, `ShutdownTerminal=0`, `Visual=0`, `Optimization=0`, `ForwardMode=0`, depósito 100 USD).
- Entradas EA: `Strategy_ID=1`, `RiskPercent=0.5`, `SizingPolicy=0 (STRICT)`. Hash SHA-256 del EA en `meta.json`.
- Qué pasó: `terminal64.exe /config:<ini>` lanzado con el terminal principal abierto (PID 34572). No apareció informe en 420 s ni entradas del Tester en `Logs/`. El terminal en ejecución no atiende la configuración de una segunda instancia.
- El terminal principal **no se cerró ni se modificó** (mismo PID y hora de inicio tras la prueba).
- Datos esperables (Python, mismo periodo, sin ejecutar el Tester): 49 señales, 49 rechazadas por lote mínimo ⇒ **0 operaciones esperadas** en esta configuración. Esta cifra es una predicción del motor Python, no un resultado de MT5.
- Desbloqueo (requiere decisión del usuario): (1) cerrar el terminal manualmente y ejecutar `04_run_tester.py` con `--shutdown` desactivado; (2) ejecutar el INI a mano en la interfaz del Tester; (3) copia portable aislada del terminal sin perfiles ni gráficos.

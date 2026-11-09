# Verificación de la automatización de MT5 (V4)

| Componente | Estado | Evidencia |
|---|---|---|
| Instancia aislada (copia portable `C:\REMIX_MT5_LAB\terminal`, 1,7 GB, historial copiado) | FUNCIONA | arranca con `/portable`, log propio |
| Compilación automática (`automation/compile_ea.py`) | FUNCIONA | V3 compilado en la instancia aislada: 0 errores, 0 avisos, EX5 fresco, sha256 fuente/EX5 en `logs/compile_registry.csv` |
| Generación de `.set` e `.ini` | FUNCIONA | `results/v4_runs/RUN_*/*.set`, `*.ini`; el terminal confirma `launched with ...ini` |
| Lanzamiento del Tester | **BLOQUEADO** | log del terminal aislado: `tester not started because the account is not specified` |
| Informe oficial / parser | Parser verificado con informe sintético (tests); **sin informe oficial V4 todavía** | `tests/test_automation_v4.py` |
| Terminal principal intacto | VERIFICADO | PID 34572 vivo antes y después de cada intento (`meta.json`) |
| Clasificación de fallos | FUNCIONA | el intento sin cuenta quedó como `SIN_INFORME`, sin inventar métricas |

**Incidente de seguridad (corregido)**: el primer arranque aislado inició sesión en la demo ACCOUNTID, que tiene 4 posiciones abiertas y trading habilitado. No se envió ninguna orden (sin gráficos ni EAs, sin `order_send`), el proceso aislado se detuvo y `automation/isolate_lab_terminal.py` borra cuenta, credenciales y gráficos de la copia. El probador necesita una cuenta: se acordó con el usuario que **él inicia sesión una vez** en la instancia aislada con una demo NUEVA sin posiciones. Hasta entonces no existe informe oficial V4.

Otros hallazgos: `/config` con rutas con espacios no carga → los `.ini` se copian a `C:\REMIX_MT5_LAB\ini\`; el servidor MCP del terminal aislado no puede enlazar el puerto 22346 (ocupado por el principal; irrelevante para el probador).


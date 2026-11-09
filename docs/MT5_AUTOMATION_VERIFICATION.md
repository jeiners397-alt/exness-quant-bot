# Verificación de la automatización de MT5 (V4) — actualizado tras el ciclo completo

Cuenta del probador: demo Exness Standard NUEVA (hedging, 3.000 USD, 0 posiciones), iniciada por el usuario en la instancia aislada `C:\REMIX_MT5_LAB\terminal`. Terminal principal (PID 34572) vivo antes y después de cada ejecución (`meta.json`: `main_terminal_alive_before/after = true`). Antes de lanzar se cerró SOLO el proceso de la instancia aislada.

| Componente | Estado | Evidencia |
|---|---|---|
| Instancia aislada con cuenta nueva sin posiciones | VERIFICADO | log: `terminal synchronized ... 0 positions, 0 orders`, hedging |
| Compilación automática (`compile_ea.py`) | VERIFICADO | V3 y V4: 0 errores, 0 avisos, EX5 reciente, hashes en `logs/compile_registry.csv` |
| `.set` + `.ini` automáticos | VERIFICADO | `results/v4_runs/RUN_*/` |
| Lanzamiento del Tester sin intervención | VERIFICADO | 4 ejecuciones (`status=OK`), 15–60 s cada una |
| Informe oficial HTML | VERIFICADO | `report.htm` por ejecución (informe del probador, build 6249, español) |
| Parser | VERIFICADO | suma de operaciones = Beneficio Neto del informe (−55,71 exacto); nº de operaciones = "Total de operaciones ejecutadas" (test `test_parsed_official_reports_are_internally_consistent`) |
| Python vs MT5 (V3 módulo A, H1, 2025-01→2026-10) | PARIDAD PARCIAL | ver abajo |
| Terminal principal intacto | VERIFICADO | ver arriba |
| `order_send` | no usado | tests estáticos en `automation/` y en los EAs |

## Primer backtest oficial (RUN_20261109_EURUSDm_H1_V3_A_PD_STRUCT_001)
V3 módulo A (False Breakout, PDH/PDL, SL estructural), EURUSDm H1, 2025.01.01–2026.11.01, 3.000 USD, 1:500, modelo OHLC 1 min, calidad de historial 100 % (2.631.637 ticks, 11.400 barras).

| Métrica oficial | Valor |
|---|---|
| Beneficio neto | −55,71 USD |
| Beneficio / pérdida bruta | 1.428,64 / −1.484,35 |
| Factor de beneficio | 0,96 |
| Beneficio esperado | −0,24 USD |
| Operaciones | 237 (95 rentables = 40,08 %) |
| DD máximo equidad | 271,83 USD (8,92 %); balance 255,38 (8,40 %) |
| Sharpe / Recuperación | −0,66 / −0,20 |
| Mayor ganancia / pérdida | 22,30 / −14,95 |
| Máx. pérdidas consecutivas | 11 (−109,73) |
| Trimestres positivos | 4 de 8 |
| Sin la mejor / sin las 5 mejores | −78,01 / −165,13 |

**Conclusión: sin ventaja** (coherente con la expectativa de Python, PF 0,976).

**Paridad con Python** (`python_vs_mt5.json`): 236 de las 236 entradas esperadas aparecen en MT5 con el mismo instante y dirección y precio de entrada idéntico (diferencia máx. 2·10⁻¹⁶); MT5 tiene 1 operación extra; 229 de 236 con el mismo lote (los otros 7 difieren porque el lote depende del balance acumulado); la hora de salida coincide solo en 82 (Python sale en la barra, MT5 en el tick). Neto MT5 −55,71 vs Python −35,69 (−6,90 en las operaciones emparejadas, el resto por la operación extra y los lotes). Es concordancia de señales, no igualdad de P&L.

Observaciones: los CSV del EA se escriben en `Common\Files` compartido (`%APPDATA%\MetaQuotes\Terminal\Common\Files`), común a todos los terminales; el servidor MCP del terminal aislado no enlaza el puerto 22346 (ocupado; irrelevante).

**Incidente anterior (corregido)**: en el primer intento la instancia inició sesión en la demo con 4 posiciones abiertas; no se envió ninguna orden. `isolate_lab_terminal.py` deja la copia sin credenciales/gráficos; ahora usa una cuenta nueva y vacía definida por el usuario.


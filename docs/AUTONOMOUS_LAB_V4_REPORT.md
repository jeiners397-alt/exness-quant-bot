# REMIX Autonomous Quant Lab V4 — informe (2026-11-09, ciclo completo ejecutado)

## Criterios de finalización (orden §20)
| Criterio | Estado | Evidencia |
|---|---|---|
| A Python ejecuta una prueba oficial de MT5 sin intervención | **CUMPLIDO** (4 ejecuciones) | `results/v4_runs/RUN_*/meta.json` (`status=OK`), `docs/MT5_AUTOMATION_VERIFICATION.md` |
| B Informe oficial verificable y analizado | **CUMPLIDO** | `report.htm` + `stats.json` + `trades.csv`; suma de operaciones = Beneficio Neto |
| C Margen 5 % por símbolo | **CUMPLIDO dentro del Tester** (EURUSDm, XAUUSDm, US30m: 0 admisiones sobre el presupuesto) | `docs/MULTI_POSITION_TEST_REPORT.md`, `research/V4_DIAG_*` |
| D Lotaje 0,01 preferido + especificaciones reales | **CUMPLIDO** (0,01–0,84 lotes; US30m mínimo real 0,05; 0 fuera de paso) | idem |
| E Múltiples posiciones y presupuestos | **CUMPLIDO en hedging dentro del Tester** (hasta 10 posiciones + 13 pendientes); netting solo simulado | idem + `tests/test_margin_v4.py` |
| F Respaldo con IDs reales en Drive | ver `backup/DRIVE_BACKUP_STATUS.md` (solo cuenta lo registrado con ID) | |
| G Código verificable en GitHub | rama `feature/remix-autonomous-quant-lab-v4` | |

**Lo que NO está demostrado**: ninguna estrategia tiene ventaja. El primer backtest oficial (V3-A, EURUSDm H1, 2025-01→2026-10, 3.000 USD) dio **−55,71 USD, PF 0,96, 237 operaciones, DD 8,92 %**. Las tres ejecuciones del módulo diagnóstico V4 son pruebas del controlador de margen, no estrategias (P&L sin significado).

## Estadísticas oficiales (informes del Strategy Tester)
Ver `research/MULTI_MARKET_RESULTS.csv`, `ROBUSTNESS_RESULTS.csv`, `STRATEGY_RANKING.csv`.

| Run | Neto | PF | Operaciones | DD equidad |
|---|---|---|---|---|
| V3-A EURUSDm H1 (estrategia) | −55,71 | 0,96 | 237 | 8,92 % |
| V4 diag EURUSDm M15 (jun–ago 2025) | −324,71 | 0,96 | 1.238 | 25,75 % |
| V4 diag XAUUSDm M15 | −820,38 | 0,92 | 1.689 | 42,33 % |
| V4 diag US30m M15 | −172,74 | 0,97 | 1.014 | 30,65 % |

## Hallazgos y limitaciones
- La demo antigua tenía 4 posiciones abiertas y no se usó; el probador usa la demo nueva vacía. Primer intento (antes del cambio) conectó brevemente a la cuenta antigua sin enviar órdenes (ver verificación).
- Demo con apalancamiento ilimitado → `order_calc_margin`=0 desde Python; en el Tester (1:500) `OrderCalcMargin` funciona y es lo que usa el EA. Con 1:500 el límite de riesgo (0,5 %) restringe el tamaño antes que el 5 % de margen, que sí limita el número de posiciones simultáneas.
- Paridad Python–MT5 (V3-A): 236/236 entradas coinciden (mismo instante, dirección, precio), 1 operación extra en MT5, 229/236 lotes iguales; P&L no idéntico (−55,71 vs −35,69).
- Modelo de simulación: OHLC 1 minuto, no ticks reales. Costes del spread de barra.
- Periodos 2025-01→2026-10 ya explorados: no son validación independiente.
- Investigación multiactivo (H101–H103) registrada pero NO ejecutada: queda bajo el límite de lotes y a la espera de su aprobación.

## Pendiente
Automatizar la carga a Drive desde Python (el conector solo se usa desde la sesión de Claude; para ejecución sin supervisión se requiere Drive para escritorio o API de Google); ejecutar H101–H103 con control aleatorio; validar netting en el Tester con una cuenta netting.

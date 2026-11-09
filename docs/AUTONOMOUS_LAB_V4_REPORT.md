# REMIX Autonomous Quant Lab V4 — informe de estado (2026-11-09)

## Criterios de finalización (orden §20)
| Criterio | Estado | Nota |
|---|---|---|
| A Automatización verificada (Python ejecuta prueba oficial MT5) | **NO CUMPLIDO** | compilación y generación de .set/.ini sí; el Tester aislado exige una cuenta (`account is not specified`) — requiere que el usuario inicie sesión en una demo vacía en la instancia aislada |
| B Informe oficial verificado | **NO CUMPLIDO** | parser probado solo con informe sintético |
| C Margen 5 % verificado | CUMPLIDO en Python con especificaciones y cálculos reales del broker (12 símbolos, ≤5,00 %); **no** verificado dentro de un EA en el Tester (el EA V4 con control de margen aún no existe) | `research/MARGIN_ALLOCATION_RESULTS.csv` |
| D Lotaje 0,01 preferido y especificaciones reales | CUMPLIDO (Python) | mínimos reales 0,01/0,05/0,10 respetados; `DYNAMIC_LOT_RESULTS.csv` |
| E Múltiples posiciones | CUMPLIDO (Python, simulado) | 7–14 simultáneas por símbolo bajo el 5 %; hedging/netting/pendientes en tests |
| F Respaldo en Drive con IDs reales | ver `backup/DRIVE_BACKUP_STATUS.md` | solo cuentan archivos con ID registrado |
| G Código en GitHub | ver rama `feature/remix-autonomous-quant-lab-v4` | |

## Hallazgos
- La demo Exness tiene apalancamiento ilimitado (2·10⁹): `OrderCalcMargin` devuelve 0; el modelo usa 1:500. Con 1:500 manda el límite de riesgo (0,5 %), no el 5 % de margen.
- La cuenta demo tiene 4 posiciones abiertas (equidad 1.082 USD): no se usa para el probador (ver `MT5_AUTOMATION_VERIFICATION.md`).
- Símbolos descubiertos (nombres exactos): EURUSDm, GBPUSDm, USDJPYm, AUDUSDm, XAUUSDm/XAUUSD247m, XAGUSDm, BTCUSDm/BTCUSDTm, ETHUSDm, US30m, US500m, USTECm (+ variantes `_x10m/_x100m`).
- No se ha investigado ninguna estrategia nueva en esta fase: `research/EXPERIMENT_REGISTER.csv` deja H101–H103 PLANIFICADAS, sin resultados. Ninguna estrategia se declara rentable.

## Pendiente
1. Usuario: iniciar sesión una vez en `C:\REMIX_MT5_LAB\terminal\terminal64.exe /portable` con una demo NUEVA vacía.
2. Ejecutar `automation.first_real_test` (V3 módulo A, EURUSDm H1) y comparar con `results/v3_expected`.
3. Crear `REMIX_EURUSD_V4.mq5` con control de margen/pendientes (`OrderCalcMargin`) y verificarlo en el Tester.

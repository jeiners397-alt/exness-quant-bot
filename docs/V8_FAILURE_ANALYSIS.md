# V8 — Análisis de fallos y resultados negativos

## Resultados negativos (medidos)
1. **La inmensa mayoría de las familias H4/D1 no tiene ventaja:** expectativa media por familia entre −0,03 y −0,08 R en H4; D1 entre −0,07 y +0,09 R; 466 de 890 pruebas clase D y 270 clase F (muestra insuficiente: D1 produce 3–60 eventos por celda en 2,8 años).
2. **Fuera del oro no hay candidatas** en USTEC, BTC, ETH ni EURUSD con muestra suficiente, pese a que el coste/ATR baja a 0,018 (H1) / 0,009 (H4) / 0,004 (D1) en XAU y 0,03–0,08 en el resto en H4.
3. **Entradas/salidas alternativas:** límites de retroceso (−0,3/−0,6 ATR) dejan sin ejecutar entre el 23 % y el 48 % de las señales sin mejorar la expectativa; break-even, trailing, parcial y salida temporal no superan la referencia fuera de muestra. "Mejor por IS" en H4: +0,34 R (IS) → +0,05 R (OOS) = sobreajuste.
4. **H4 `D_EXTREME_REVERSION` invertido en XAUUSD:** t_all 3,33, pero depende de largos (+0,61 R frente a +0,15 R en cortos) y cae en 2026 (+0,48 → +0,59 → +0,12 R por año a 1,5R): no es estable en el último periodo.
5. **H1 1,5R:** 2026 pierde (−92 USD, 96 operaciones); la ventaja se concentra en 2025.
6. **Variante B de H1 (cierre fuera, ventana 96):** IS +0,03 R (t 0,36); el OOS +0,30 R no basta.

## Fallos técnicos y de método (corregidos, con evidencia)
| Hallazgo | Efecto | Corrección |
|---|---|---|
| V7 describía mal la regla XAU H1 (sweep que cierra dentro, no ruptura con cierre fuera) | Podía haberse implementado otra hipótesis | Código recuperado, descripción corregida, ambas probadas por separado |
| Python operaba a las 22–23 UTC con mercado cerrado | 1,9 % de señales no ejecutables (+3,9 R inflados) | Documentado; EA registra `ORDER_FAIL_10018` |
| Descartar velas H4 parciales en Python | 21 operaciones MT5 sin par; 227/233 | Se conservan como en MT5 (4.537 barras = probador); estudio B rehecho |
| Fórmula de R de salidas con SL ≠ 1 ATR (TP medido en ATR, no en R) | `SL1.5_TP3` salía con t=8,7 (artefacto) | Detectado por magnitud implausible; corregido (TP/SL en R) y cubierto por test |
| Estudio de salidas H1 corría sobre M15 por orden de importación (`V7_TF`) | 1.489 eventos en lugar de 320 | Carga H1 explícita + aserción de 320 señales |
| `itertuples` renombra columnas con punto (`expR_net_0.5R`) | Clasificación de todas las pruebas = D | Se usan diccionarios; clases recalculadas |
| `ExecutionMode` del .ini sin efecto | Resultados idénticos con 500 ms / aleatorio / 2 s | No se declara prueba de latencia; se modela como coste |
| Ticks reales: cobertura 9 % en el probador; la sonda `copy_ticks_range` no respondió (>10 min) | No hay validación con ticks reales | `ERROR_DATOS`; sin sustitutos; sonda abortada y su proceso aislado detenido |
| Terminal aislado residual bloqueaba nuevos tests | `SIN_INFORME` en 5 s | Se detuvo solo ese PID (ruta bajo `C:\REMIX_MT5_LAB`) |
| `tester_log.txt` ≈ 229 MB por run | Disco | Excluido de Drive/GitHub; pendiente rotación |

## Sesgos que no se pueden eliminar con los datos actuales
- **Selección sobre el mismo periodo** (3.174 pruebas acumuladas, un solo ciclo de mercado del oro).
- **Régimen alcista del oro 2024–2026**: la ventaja de largos incluye drift (+0,07 R en largos aleatorios).
- **Potencia:** en H4 hay ≈ 240 eventos/regla; detectar un efecto de 0,2 R con t=4 requiere ≈ 400 operaciones independientes.
- Swap real, comisión y deslizamiento sin histórico verificable.


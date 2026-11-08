# REMIX FOREX V1 — FASE 0

Laboratorio inicial **de solo lectura** para Exness + MetaTrader 5 + Python y un Expert Advisor MQL5 de diagnóstico. Esta fase **no envía órdenes**, ni pretende demostrar rentabilidad. **El EA no está compilado ni se ha conectado a la cuenta del usuario desde ChatGPT**: ambas verificaciones se realizan en el Windows del usuario.

## Objetivo

1. Confirmar el terminal Windows 64 bits y que la cuenta activa es **DEMO** usando `ACCOUNT_TRADE_MODE_DEMO`.
2. Leer saldo, patrimonio, margen, catálogo de símbolos y especificaciones (incluido margen estimado, sin órdenes).
3. Extraer las velas cerradas M5 de `EURUSDm` en horario **UTC** y detectar irregularidades básicas.
4. Compilar un EA nativo de diagnóstico con `EnableTrading=false` sin ninguna función de envío de órdenes.

## Preparación en Windows (PowerShell)

Abre MetaTrader 5 y entra en tu cuenta **demo**. Descomprime esta carpeta en Windows y abre PowerShell en ella. Si tu Python no acepta `py`, instala Python 3.11 o 3.12 de 64 bits y vuelve a abrir PowerShell.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m research.mt5_connection
.\.venv\Scripts\python.exe -m research.data_client --symbol EURUSDm --timeframe M5 --days 14
```

Opcional: `powershell -ExecutionPolicy Bypass -File .\run_checks.ps1` (crea venv e inicia todas las verificaciones). También puedes indicar explícitamente tu terminal: `python -m research.mt5_connection --terminal "C:\ruta\terminal64.exe"`.

La primera prueba deja `reports/diagnostico_mt5.json`; la segunda `reports/EURUSDm_M5.csv` y `reports/EURUSDm_M5.metadata.json`. **Nunca compartas contraseñas ni el identificador de inicio de sesión de MT5**. El diagnóstico omite deliberadamente `login`.

Si el símbolo no se llama `EURUSDm`, el diagnóstico muestra alternativas; usa el nombre exacto en `--symbol`. Si MT5 devuelve pocos históricos, revisa *Herramientas → Opciones → Gráficos → Máx. barras en gráfico* y la cobertura del bróker.

## Compilar e instalar EA

1. En MT5, elige **Archivo → Abrir carpeta de datos**; entra a `MQL5\Experts`.
2. Copia `mql5\REMIX_FOREX_V1.mq5` allí.
3. Pulsa **F4** para abrir MetaEditor, abre el archivo y pulsa **F7** para compilar.
4. Verifica **0 errores** y que se generó `REMIX_FOREX_V1.ex5`. La compilación no se ha verificado aquí.
5. En MT5, ve al Navegador (Ctrl+N), actualiza Asesores Expertos y asocia el EA a un gráfico en tu cuenta demo. Deja `EnableTrading=false`.
6. Observa el panel y la pestaña *Expertos*. También puedes ejecutar **Ctrl+R → Probador de estrategias**, sin esperar operaciones.

El EA aborta inicialización en una cuenta no DEMO y si se solicita `EnableTrading=true`. No incluye funciones que puedan enviar operaciones incluso si se cambia el botón de trading algorítmico.

## Interpretación de resultados

- `trade_mode=DEMO` + `connected=true` confirma la cuenta que respondió; no confirma condiciones futuras.
- Un tick en fin de semana puede ser antiguo; inspecciona `tick_time_utc` antes de interpretar el spread.
- `estimated_margin_min_buy` proviene de `order_calc_margin` para un lote mínimo. Es estimación, no comprobación de capacidad real ni pérdida máxima.
- CSV corresponde a velas **cerradas**. Los huecos pueden ser cierres normales o datos incompletos.
- Aún no hay backtests, órdenes, compilación confirmada ni evaluación estadística de estrategias.

## Diseño posterior

Las cinco estrategias previstas (London Breakout, Liquidity Sweep + CHoCH, EMA+ADX Pullback, Asian Range y Donchian+ATR) se investigarán **independientemente** después de validar la infraestructura. El código Binance existente permanece intacto en `main`; este proyecto debe trabajar en rama propia.

## Documentación oficial

- [Integración Python MT5](https://www.mql5.com/en/docs/python_metatrader5)
- [copy_rates_range y UTC](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py)
- [order_calc_margin](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcmargin_py)
- [OnInit](https://www.mql5.com/en/docs/event_handlers/oninit)
- [Strategy Tester](https://www.metatrader5.com/en/terminal/help/algotrading/testing)

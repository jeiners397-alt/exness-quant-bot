# Informe de infraestructura — REMIX FOREX V1 (8 de noviembre de 2026)

## Repositorio inspeccionado

Repositorio privado `jeiners397-alt/exness-quant-bot`, rama predeterminada `main`. Antes de los cambios: cuatro archivos `Bot.py` (1.904 líneas), `Dockerfile`, `README.md`, `requirements.txt`. En `Bot.py` se identificaron `SignalEngine`, `PaperBroker`, cálculo de indicadores NumPy, `WSStream`, `RestClient`, persistencia y Telegram. El código utiliza *Binance USDT-M Futures* (REST/WebSocket) y simulación paper, **no** MT5 ni Exness. `Dockerfile` usa imagen Linux `python:3.10-slim`; esto no sirve para ejecutar la integración local MT5 nativa de Windows sin adaptaciones. La documentación de raíz dice "futuros anuncios". Por tanto, **no debe reemplazarse `main`** ni copiarse directamente una estrategia Binance como si fuera Forex.

**Reutilización posible tras pruebas:** patrones de reconexión, formato de informes, estructura de indicadores matemáticos, logging y pruebas de estadísticas. **No trasladar sin rediseño:** orden de ejecución, marcos de trading, símbolos, fees, WebSocket, nocional, apalancamiento y token de Telegram. El código antiguo contiene un valor de token Telegram por defecto y un chat ID; deben considerarse secretos expuestos en el código y rotar/revocar el token en su proveedor, sin difundirlo en informes nuevos.

## Entregables de Fase 0

- Diagnóstico Python: `research/mt5_connection.py`, solo lectura.
- Extracción Python: `research/data_client.py`, OHLCV M5 cerrado, UTC, CSV y metadatos.
- EA de diagnóstico: `mql5/REMIX_FOREX_V1.mq5`, con cuenta demo requerida, sin lógica de órdenes.
- Pruebas: `tests/test_phase0.py` con dobles/mocks; no usan credenciales ni envían órdenes.
- Ejecución guiada: `README.md` y `run_checks.ps1`.

## Validaciones efectuadas vs. pendientes

- **Efectuadas:** inspección del árbol y fragmentos estructurales del repositorio por conector GitHub; búsqueda de documentación oficial; siete pruebas unitarias locales sin MT5, superadas en Python del entorno de desarrollo. Este resultado no verifica la conexión con el bróker ni la compilación del EA.
- **Pendientes en el Windows del usuario:** conexión real Python→MT5; identificación de símbolos/cuenta actual; descarga real de histórico; compilación `.ex5` y pruebas con Strategy Tester.
- **Prohibición en Fase 0:** órdenes reales o demo automáticas, cambios de credenciales, afirmaciones de rentabilidad sin backtests.

## Criterios para pasar a Fase 1

1. Cuenta actual demostrada como `DEMO` por API de MT5.
2. Diagnóstico sin errores y especificaciones de los instrumentos disponibles.
3. Historias con suficientes velas cerradas y calidad documentada.
4. EA compilado sin errores y panel observable en demo.
5. Configuraciones, símbolos y zona horaria registrados sin contraseñas.

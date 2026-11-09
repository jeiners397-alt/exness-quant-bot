# REMIX EURUSD V2 — laboratorio de investigación cuantitativa (solo simulación)

Laboratorio reproducible para investigar estrategias sobre **EURUSDm (Exness, cuenta demo)**. Python para investigación; MQL5 solo para el Strategy Tester.

**Seguridad:** no envía órdenes a ninguna cuenta (`mt5.order_send` no se usa; el EA aborta fuera del Strategy Tester). No contiene credenciales, tokens, `.env` ni datos de cuenta. Datos históricos pesados, caché de ticks e informes del Tester con datos de cuenta están excluidos.

## REMIX_EURUSD_V2 (EA experimental)

- `mql5/REMIX_EURUSD_V2.mq5` (compila con 0 errores/0 avisos): módulos S01 (referencia), S05/L2, S06/L3, S08/L4, L1; **desactivado por defecto** (Module=NONE, EnableTrading=false); solo Strategy Tester; SL obligatorio; política estricta de lote mínimo.
- `mql5/sets/` configuraciones .set, `docs/V2_TESTER_INSTRUCTIONS.md` pasos para su Strategy Tester, `results/v2_expected/` operaciones esperadas de Python.
- Informe: `docs/REMIX_EURUSD_V2_RESEARCH_REPORT.md`. **Ninguna estrategia está aprobada para producción.**

## Paridad Python-MT5 (V2 / L2)

- `docs/PARITY_V2_L2_REPORT.md`: de 19/48 a 30/30 entradas coincidentes con el Tester (errores: calentamiento, compuertas de spread, ADX MT5 con EMA 2/(n+1), bug de max_bars del EA V2, reapertura de fin de semana, swap del viernes). Diferencia residual de neto 0,56 USD.
- `mql5/REMIX_EURUSD_V2_1.mq5` + `mql5/sets/V2_1_S05_L2_H4.set` (V2 se conserva intacto). `docs/V2_1_TESTER_INSTRUCTIONS.md`, `scripts/compare_bar_diag.py`.

## REMIX V3 (Fase V3)

- `docs/REMIX_EURUSD_V3_REPORT.md`: familias A (False Breakout), B (Volatility Momentum), C (Macro News: pendiente de datos), D (reversión condicionada por régimen). **Ninguna con ventaja demostrada.**
- `mql5/REMIX_EURUSD_V3.mq5` (0 errores/0 avisos; todo desactivado por defecto) y `mql5/sets/V3_*.set`; V1/V2/V2.1 intactos (hash verificado en tests).

## Contenido
- `remix_lab/` motor de datos, indicadores, estrategias S01–S12, backtest (Bid/Ask, SL/TP, riesgo, costes), métricas, Monte Carlo, arnés de Fase D.
- `mql5/REMIX_STRATEGY_RESEARCH_LAB_V1.mq5` EA de investigación (S01–S04), solo Strategy Tester.
- `tests/` 95 pruebas (`python -m pytest -q`).
- `research/` catálogos (448 estrategias, 500 indicadores), diagnósticos de S01, resultados de Fases C y D.
- `docs/` informes de fase (ver `REMIX_EURUSD_PHASE_D_REPORT.md`).
- `scripts/` descarga de datos (solo lectura), compilación del EA, ejecuciones.

## Estado (2026-11-09)
Ninguna estrategia (S01–S12, ni sus inversas) demuestra ventaja estadística tras costes. S01 es la estrategia de referencia. Cuatro «pistas débiles» están congeladas para una evaluación prospectiva única (`research/PROSPECTIVE_FREEZE_2026-11-09.json`). Todo resultado sobre 2025-01→2026-10 es **exploratorio**.

## Reproducir
```
pip install -r requirements.txt
python -m pytest -q
```
Los scripts de datos requieren un terminal MetaTrader 5 con cuenta demo y reconstruyen `data/raw/` (no incluido).

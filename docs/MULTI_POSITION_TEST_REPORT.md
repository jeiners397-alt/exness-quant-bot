# Pruebas de múltiples posiciones (V4)

Ejecutadas en `tests/test_margin_v4.py` (18 pruebas, todas pasan) y con especificaciones reales (`research/MARGIN_ALLOCATION_RESULTS.csv`).
Cubren: ejemplo de la orden (150 USD; 40+50+45 → restante 15 USD), tope del 5 % nunca superado, varias posiciones admitidas mientras haya presupuesto, órdenes pendientes contadas (y desactivables), reservas sin doble uso, límite global entre símbolos, riesgo independiente del margen, rechazo sin redondeo hacia arriba, hedging (compra y venta simultáneas) vs netting (posición única, rechazo de la contraria), conciliación con posiciones del broker. **Son pruebas de simulación**: no hay verificación dentro del Strategy Tester (pendiente, ver informe V4).

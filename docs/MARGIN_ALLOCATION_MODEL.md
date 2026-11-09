# Modelo de asignación de margen y lotaje (V4)

**Dos variables independientes**
- *Margen asignado*: capital comprometido como garantía. Límite = 5 % de la equidad **por símbolo** (150 USD con 3.000 USD), más un límite global configurable (15 % por defecto) contra exposición correlacionada. No es riesgo de pérdida.
- *Riesgo al SL*: pérdida monetaria si se toca el SL (`RiskPercent`, 0,5 % por operación por defecto) y tope agregado (3 %). Una operación con margen pequeño no elude este control.

**Algoritmo (`automation/dynamic_lot_sizing.py`)**
1. Consulta especificaciones reales (`symbol_specifications.py`): volumen min/max/paso/límite, contrato, tick, modo de cálculo.
2. `lots_margen = piso(margen_disponible_símbolo / margen_por_lote)`; `lots_riesgo = piso(riesgo_permitido / pérdida_por_lote_al_SL)`; se toma el mínimo, normalizado **hacia abajo** al paso.
3. Si el resultado < mínimo válido del broker → **rechazo** (nunca se redondea hacia arriba). 0,01 es el mínimo *preferido*, no un máximo ni un obligatorio; instrumentos con mínimo 0,05/0,10 lo respetan.
4. Se re-verifica el margen con el volumen final contra el presupuesto agregado (posiciones + órdenes pendientes + reservas).
5. El controlador reserva el margen (`reserve → commit/release`) para que dos solicitudes no usen el mismo margen. Sin descuento por cobertura.

**Hedging/netting**: hedging registra ticket/magic/estrategia/SL/TP por posición; netting mantiene una sola posición neta (promedio), un único SL real y rechaza la orden contraria (reduciría la posición); `reconcile()` compara con las posiciones del broker.

**Fuente del margen**: `OrderCalcMargin`/`order_calc_margin` del broker. **Hallazgo**: la demo tiene apalancamiento ilimitado (2·10⁹) y el broker devuelve margen 0 en casi todos los símbolos; en ese caso se usa un modelo con el apalancamiento del probador (1:500, marcado como modelo). Con 1:500 el límite que en la práctica manda es el de riesgo (0,5 %), no el del 5 % de margen (`research/DYNAMIC_LOT_RESULTS.csv`).

**Resultados verificados con especificaciones reales** (`research/MARGIN_ALLOCATION_RESULTS.csv`): llenando el presupuesto con entradas sucesivas, el margen del símbolo quedó en 4,80–5,00 % de la equidad en 12 de 14 símbolos (nunca > 5 %); 7–14 posiciones simultáneas admitidas según el instrumento; US500_x100m/USTEC_x100m rechazados por riesgo (mínimo excede 0,5 % con el SL ilustrativo). El SL usado es ilustrativo (0,2 % del precio), no una estrategia.

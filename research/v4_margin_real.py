"""Verificacion con especificaciones y calculos REALES del broker (solo lectura: symbol_info, order_calc_margin, order_calc_profit).
No envia ordenes. Escribe research/MARGIN_ALLOCATION_RESULTS.csv, DYNAMIC_LOT_RESULTS.csv, MULTI_MARKET_SPECS.json."""
import csv
import json
import sys
from pathlib import Path

import MetaTrader5 as mt5

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation.margin_allocator import MarginAllocator  # noqa: E402
from automation.multi_position_controller import MultiPositionController  # noqa: E402
from automation.dynamic_lot_sizing import size  # noqa: E402
from automation.symbol_specifications import SymbolSpec, discover  # noqa: E402

assert mt5.initialize(), mt5.last_error()
acc = mt5.account_info()
print("modo cuenta:", "HEDGING" if acc.margin_mode == mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING else "NETTING/EXCHANGE", "leverage", acc.leverage)
found = discover(mt5)
# 1 simbolo por base prioritaria (nombres EXACTOS del terminal; preferir sufijo 'm' del terminal solo si existe tal cual)
pick, seen = [], set()
for r in found:
    base = r["name"].rstrip("mc").upper()[:6] if r["class"] in ("forex", "metals", "crypto") else r["name"]
    if base in seen or not r["name"].lower().endswith("m"):
        continue
    seen.add(base); pick.append(r["name"])
print("simbolos:", pick)
EQ = 3000.0
mrows, lrows, specs = [], [], {}
for name in pick:
    spec = SymbolSpec.from_mt5(mt5, name, 500.0)          # la demo tiene apalancamiento ilimitado (margen 0): se usa 1:500, el del probador
    tk = mt5.symbol_info_tick(name)
    if not tk or not tk.ask:
        continue
    px = tk.ask
    sl_dist = max(px * 0.002, 30 * spec.point)            # SL ilustrativo: 0,2 % del precio (no es una estrategia)
    sl = px - sl_dist
    specs[name] = spec.as_dict()
    a = MarginAllocator(EQ, 5.0)
    d = size(spec, a, px, sl, True, 0.5, mt5=mt5)
    m_min = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, name, spec.volume_min, px)
    lrows.append(dict(symbol=name, volume_min=spec.volume_min, volume_step=spec.volume_step, volume_max=spec.volume_max, contract=spec.contract_size,
                      price=px, sl=round(sl, spec.digits), margin_min_lot=m_min, lots=d.lots, approved=d.approved, reason=d.reason, margin=d.margin,
                      loss_at_sl=d.loss_at_sl, risk_pct=round(d.risk_pct, 4), lots_by_margin=d.lots_by_margin, lots_by_risk=d.lots_by_risk))
    # llenar el presupuesto de margen con entradas sucesivas (hedging) y comprobar que nunca supera 5 %
    ctl = MultiPositionController(MarginAllocator(EQ, 5.0, global_percent=100), "HEDGING", max_total_risk_pct=100)
    n = 0
    for _ in range(200):
        dd, t = ctl.request_entry(spec, True, px, sl, None, 0.5, mt5=mt5)
        if not t:
            last = dd.reason
            break
        n += 1
    used = ctl.alloc.used(name)
    mrows.append(dict(symbol=name, budget=EQ * 0.05, positions_admitted=n, margin_used=round(used, 4), pct_equity=round(100 * used / EQ, 4),
                      within_5pct=used <= EQ * 0.05 + 1e-9, stop_reason=last, total_risk_money=round(ctl.total_risk_money(), 2)))
for f, rows in (("MARGIN_ALLOCATION_RESULTS.csv", mrows), ("DYNAMIC_LOT_RESULTS.csv", lrows)):
    if rows:
        with open(ROOT / "research" / f, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
(ROOT / "research" / "MULTI_MARKET_SPECS.json").write_text(json.dumps(dict(account_margin_mode="HEDGING" if acc.margin_mode == mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING else "NETTING", leverage=acc.leverage, found=found, specs=specs), indent=1), encoding="utf-8")
mt5.shutdown()
for r in mrows:
    print(r)
for r in lrows:
    print(r["symbol"], r["lots"], r["approved"], r["reason"], "min", r["volume_min"])

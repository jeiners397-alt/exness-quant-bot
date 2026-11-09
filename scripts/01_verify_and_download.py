"""Verifica conexion con Exness (solo lectura), resuelve simbolos, descarga historicos y los valida.

No envia ordenes. No usa credenciales (usa la sesion ya abierta del terminal).
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from remix_lab import load_config, LOGS_DIR  # noqa: E402
from remix_lab import data_engine as de  # noqa: E402

LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler(LOGS_DIR / "lab.log"), logging.StreamHandler()],
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")

cfg = load_config()
if not de.connect():
    sys.exit("No se pudo conectar con MT5")
mt5 = de._mt5()
ti, ai = mt5.terminal_info(), mt5.account_info()
conn = dict(terminal_path=ti.path, data_path=ti.data_path, build=ti.build, connected=ti.connected,
            company=ti.company, server=ai.server, account_trade_mode=ai.trade_mode,
            is_demo=(ai.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO), currency=ai.currency,
            symbols_total=len(mt5.symbols_get() or []), python_mt5_version=mt5.__version__)
print("CONEXION:", conn)
if not conn["is_demo"]:
    sys.exit("ABORTADO: la cuenta NO es DEMO.")
de.save_json(conn, "connection.json")

start = datetime.fromisoformat(cfg["requested_period"]["start"])
end = datetime.fromisoformat(cfg["requested_period"]["end"]).replace(hour=23, minute=59)
specs, report = {}, {}
for base in cfg["symbols"]:
    sym = de.resolve_symbol(base)
    print(f"simbolo {base} -> {sym}")
    if not sym:
        report[base] = "NO ENCONTRADO"
        continue
    specs[sym] = de.symbol_spec(sym)
    for tf in cfg["timeframes"]:
        df = de.fetch_rates(sym, tf, start, end)
        if df.empty:
            report[f"{sym}_{tf}"] = {"ok": False, "reason": "sin datos devueltos por MT5"}
            continue
        de.save_rates(df, sym, tf)
        report[f"{sym}_{tf}"] = de.verify_data(df, tf)
        print(sym, tf, report[f"{sym}_{tf}"])
de.save_json(specs, "symbol_specs.json")
de.save_json(report, "data_verification.json")
mt5.shutdown()

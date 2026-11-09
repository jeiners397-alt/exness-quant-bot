"""Analizador de informes HTML oficiales del Strategy Tester. No inventa metricas: lo que no aparece queda como None."""
from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

LABELS = {   # clave -> etiquetas (EN / ES) tal como aparecen en el informe
    "history_quality": ["History Quality", "Calidad del historial"],
    "bars": ["Bars", "Barras"], "ticks": ["Ticks"], "symbols": ["Symbols", "Símbolos"],
    "initial_deposit": ["Initial Deposit", "Depósito inicial"],
    "total_net_profit": ["Total Net Profit", "Beneficio neto total"],
    "gross_profit": ["Gross Profit", "Beneficio bruto"], "gross_loss": ["Gross Loss", "Pérdidas brutas"],
    "profit_factor": ["Profit Factor", "Factor de beneficio"],
    "expected_payoff": ["Expected Payoff", "Pago esperado", "Beneficio esperado"],
    "recovery_factor": ["Recovery Factor", "Factor de recuperación"],
    "sharpe_ratio": ["Sharpe Ratio", "Ratio de Sharpe", "Coeficiente de Sharpe"],
    "balance_dd_max": ["Balance Drawdown Maximal", "Reducción máxima del balance", "Drawdown máximo del balance"],
    "equity_dd_max": ["Equity Drawdown Maximal", "Reducción máxima de la equidad", "Drawdown máximo de la equidad"],
    "balance_dd_rel": ["Balance Drawdown Relative", "Reducción relativa del balance"],
    "equity_dd_rel": ["Equity Drawdown Relative", "Reducción relativa de la equidad"],
    "total_trades": ["Total Trades", "Total de operaciones", "Total de transacciones"],
    "short_trades_won": ["Short Trades (won %)", "Posiciones cortas (% ganadoras)", "Operaciones cortas (% ganadoras)"],
    "long_trades_won": ["Long Trades (won %)", "Posiciones largas (% ganadoras)", "Operaciones largas (% ganadoras)"],
    "profit_trades": ["Profit Trades (% of total)", "Operaciones con beneficio (% del total)", "Transacciones rentables (% del total)"],
    "loss_trades": ["Loss Trades (% of total)", "Operaciones con pérdidas (% del total)", "Transacciones con pérdidas (% del total)"],
    "largest_profit": ["Largest profit trade", "Mayor operación con beneficio", "Transacción rentable más grande"],
    "largest_loss": ["Largest loss trade", "Mayor operación con pérdidas", "Transacción con pérdidas más grande"],
    "avg_profit": ["Average profit trade", "Operación con beneficio media", "Media de transacciones rentables"],
    "avg_loss": ["Average loss trade", "Operación con pérdidas media", "Media de transacciones con pérdidas"],
    "max_consec_wins": ["Maximum consecutive wins ($)", "Máximo de ganancias consecutivas ($)"],
    "max_consec_losses": ["Maximum consecutive losses ($)", "Máximo de pérdidas consecutivas ($)"],
    "total_deals": ["Total Deals", "Total de transacciones", "Total de tratos"],
}


ES = {   # etiquetas del informe en español de Exness (build 6249); van primero para tener prioridad
    "total_net_profit": ["Beneficio Neto"], "gross_profit": ["Beneficio Bruto"], "gross_loss": ["Pérdidas Brutas"],
    "profit_factor": ["Factor de Beneficio"], "expected_payoff": ["Beneficio Esperado"], "recovery_factor": ["Factor de Recuperación"],
    "total_trades": ["Total de operaciones ejecutadas"], "total_deals": ["Total de transacciones"], "margin_level": ["Nivel de margen"],
    "short_trades_won": ["Posiciones cortas (% rentables)"], "long_trades_won": ["Posiciones largas (% rentables)"],
    "profit_trades": ["Posiciones rentables (% del total)"], "loss_trades": ["Posiciones no rentables (% del total)"],
    "largest_profit": ["La transacción rentable"], "largest_loss": ["La transacción no rentable"],
    "avg_profit": ["Promedio de transacción rentable"], "avg_loss": ["Promedio de transacción no rentable"],
    "max_consec_wins": ["El número máximo de ganancias consecutivas ($)"], "max_consec_losses": ["El número máximo de pérdidas consecutivas ($)"],
}
for _k, _v in ES.items():
    LABELS[_k] = _v + LABELS.get(_k, [])
LABELS["total_trades"] = [l for l in LABELS["total_trades"] if l != "Total de transacciones"]


def read_report(path: Path) -> str:
    b = Path(path).read_bytes()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16", errors="ignore")
    for enc in ("utf-8", "cp1252"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return b.decode("latin-1")


def _num(s: str | None):
    if s is None:
        return None
    s = html.unescape(s).replace("\xa0", " ").strip()
    m = re.match(r"^\s*(-?[\d\s]+(?:[.,]\d+)?)", s)
    if not m:
        return None
    v = m.group(1).replace(" ", "")
    if "," in v and "." not in v:
        v = v.replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return None


def _cells(row_html: str) -> list[str]:
    return [html.unescape(re.sub(r"<[^>]+>", "", c)).replace("\xa0", " ").strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S | re.I)]


def parse_stats(txt: str) -> dict:
    rows = [_cells(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", txt, re.S | re.I)]
    flat = {}
    for cells in rows:
        for i, c in enumerate(cells):
            if c.endswith(":") and i + 1 < len(cells):
                flat[c[:-1].strip()] = cells[i + 1]
    out, raw = {}, {}
    for key, labs in LABELS.items():
        val = next((flat[l] for l in labs if l in flat), None)
        out[key] = _num(val) if val is not None else None
        raw[key] = val
    out["_raw"] = raw
    for k in ("profit_trades", "loss_trades", "short_trades_won", "long_trades_won", "equity_dd_max", "equity_dd_rel", "balance_dd_max", "balance_dd_rel"):
        r = raw.get(k)
        if r:
            m = re.search(r"\(([\d.,]+)%\)", r)
            out[k + "_pct"] = float(m.group(1).replace(",", ".")) if m else None
            if k.endswith("dd_max") and "(" in r:
                m2 = re.search(r"\(([\d.,]+)%\)", r)
                out[k + "_pct"] = float(m2.group(1).replace(",", ".")) if m2 else None
            m3 = re.search(r"([\d.,]+)%\s*\(([\d\s.,]+)\)", r)
            if m3:
                out[k + "_pct"], out[k] = float(m3.group(1).replace(",", ".")), _num(m3.group(2))
    return out


def parse_deals(txt: str) -> list[dict]:
    """Tabla de transacciones (Deals). Devuelve filas con las columnas del informe."""
    rows = [_cells(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", txt, re.S | re.I)]
    hdr_i = next((i for i, c in enumerate(rows) if c and c[0] in ("Time", "Hora", "Fecha", "Fecha/Hora") and any(x in c for x in ("Deal", "Trato", "Transacción", "Transaccion"))), None)
    if hdr_i is None:
        return []
    hdr = rows[hdr_i]
    deals = []
    for c in rows[hdr_i + 1:]:
        if len(c) < len(hdr) - 1 or not re.match(r"^\d{4}\.\d{2}\.\d{2}", c[0] or ""):
            if deals and len(c) < 3:
                break
            continue
        d = dict(zip(hdr, c))
        deals.append(d)
    return deals


def pair_trades(deals: list[dict]) -> list[dict]:
    """Empareja entradas (in) y salidas (out) por Order/Position; devuelve operaciones cerradas."""
    keys = {k.lower(): k for k in deals[0]} if deals else {}
    g = lambda d, *names: next((d[keys[n]] for n in names if n in keys), None)
    open_ = {}
    out = []
    for d in deals:
        direction = (g(d, "direction", "dirección", "direccion") or "").lower()
        typ = (g(d, "type", "tipo") or "").lower()
        if direction == "in" or direction == "entrada":
            open_.setdefault("q", []).append(d)
        elif direction in ("out", "salida") and open_.get("q"):
            e = open_["q"].pop(0)
            out.append(dict(open_time=g(e, "time", "hora", "fecha/hora"), close_time=g(d, "time", "hora", "fecha/hora"), symbol=g(d, "symbol", "símbolo", "simbolo"),
                            type=g(e, "type", "tipo"), lots=_num(g(e, "volume", "volumen")), price_open=_num(g(e, "price", "precio")),
                            price_close=_num(g(d, "price", "precio")), commission=_num(g(d, "commission", "comisión", "comision")),
                            swap=_num(g(d, "swap")), profit=_num(g(d, "profit", "beneficio")), balance=_num(g(d, "balance", "saldo")),
                            comment=g(d, "comment", "comentario"), order_open=g(e, "order", "orden"), order_close=g(d, "order", "orden")))
    return out


def parse_report(path: Path, out_dir: Path | None = None) -> dict:
    txt = read_report(path)
    stats = parse_stats(txt)
    deals = parse_deals(txt)
    trades = pair_trades(deals) if deals else []
    res = dict(source=str(path), stats={k: v for k, v in stats.items() if k != "_raw"}, stats_raw=stats["_raw"], n_deal_rows=len(deals), n_trades=len(trades),
               complete=stats.get("total_net_profit") is not None and stats.get("total_trades") is not None)
    if out_dir:
        out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "stats.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        for name, rows in (("deals.csv", deals), ("trades.csv", trades)):
            if rows:
                with (out_dir / name).open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    return res


if __name__ == "__main__":
    r = parse_report(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None)
    print(json.dumps(r["stats"], indent=1, ensure_ascii=False)); print(r["n_deal_rows"], r["n_trades"], r["complete"])

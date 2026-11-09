"""Candidatos a duplicado por similitud de nombre normalizado (capa fina sobre las familias de build_catalogs.py).

Solo propone pares para REVISION HUMANA/MATEMATICA. Una similitud alta de nombre NO prueba equivalencia de reglas.
"""
import csv
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

R = Path(__file__).resolve().parent.parent
STOP = re.compile(r"\b(1m|3m|5m|15m|1h|4h|1d|scalp|scalping|strategy|estrategia|indicator|indicador|signal|signals|senal|auto|advanced|"
                  r"suite|overlay|tracker|detector|monitor|index|the|de|del|la|el|con|y|and|with)\b")


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9% ]+", " ", s)
    s = STOP.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


out = {}
for kind, fn in (("strategies", "CATALOG_STRATEGIES.csv"), ("indicators", "CATALOG_INDICATORS.csv")):
    rows = list(csv.DictReader(open(R / fn, encoding="utf-8-sig")))
    for r in rows:
        r["_n"] = norm(r["name"])
    pairs = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            if a["source"] == b["source"] or a["source"] == "LAB_USER_SPEC" or b["source"] == "LAB_USER_SPEC":
                continue                      # solo pares entre fuentes distintas
            if not a["_n"] or not b["_n"]:
                continue
            ratio = 1.0 if a["_n"] == b["_n"] else SequenceMatcher(None, a["_n"], b["_n"]).ratio()
            if ratio >= 0.82:
                pairs.append((round(ratio, 3), a["canonical_id"], a["name"], b["canonical_id"], b["name"],
                              "NOMBRE_NORMALIZADO_IDENTICO" if ratio == 1.0 else "NOMBRE_MUY_SIMILAR"))
    pairs.sort(key=lambda x: -x[0])
    with open(R / f"DUP_CANDIDATES_{kind}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["similarity", "id_a", "name_a", "id_b", "name_b", "type", "decision"])
        for p in pairs:
            w.writerow([*p, "PENDIENTE_REVISION_MATEMATICA"])
    ids = set()
    for p in pairs:
        ids.update([p[1], p[3]])
    out[kind] = dict(pairs=len(pairs), identical=sum(1 for p in pairs if p[0] == 1.0), entries_involved=len(ids), total=len(rows))
print(json.dumps(out, indent=1))
(R / "dup_stats.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

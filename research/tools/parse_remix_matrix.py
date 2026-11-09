"""Parser de la Fuente A (MATRIZ_200_ESTRATEGIAS_INDICADORES.xlsx) a partir de la lectura de texto del conector.

Entrada: JSON guardado por read_file_content ({"fileContent": ...}). Salida: CSV de staging por seccion.
No altera el contenido; solo separa filas/columnas y retira escapes de Markdown (\\_).
"""
import csv
import io
import json
import re
import sys
from pathlib import Path

src, outdir = Path(sys.argv[1]), Path(sys.argv[2])
outdir.mkdir(parents=True, exist_ok=True)
t = json.loads(src.read_text(encoding="utf-8"))["fileContent"]
t = t.replace("\\_", "_")

i_s, i_i = t.find("Estrategias (100)"), t.find("Indicadores (100)")
assert 0 < i_s < i_i, "no se encontraron las secciones"
HDR = "N°,Categoría,Nombre literal del usuario,Descripción original,Viabilidad para Exness MT5,Prioridad de diseño,Motivo / limitación,Siguiente acción,Fuente técnica 1"


def parse(block: str, label: str):
    k = block.find("Fuente técnica")      # el '1' que sigue es el N° de la primera fila, no parte del encabezado
    body = block[k + len("Fuente técnica"):].strip()
    body = re.sub(r"(https?://\S+) (\d{1,3},)", r"\1\n\2", body)   # delimitar filas
    rows = []
    for line in body.split("\n"):
        r = next(csv.reader(io.StringIO(line.strip())))
        rows.append(r)
    bad = [r for r in rows if len(r) != 9]
    return rows, bad


for label, block in (("strategies", t[i_s:i_i]), ("indicators", t[i_i:])):
    rows, bad = parse(block, label)
    print(label, "filas:", len(rows), "filas con != 9 columnas:", len(bad))
    for b in bad[:3]:
        print("  MAL:", len(b), b[:3])
    with open(outdir / f"REMIX_{label}_staging.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(HDR.split(","))
        w.writerows(rows)

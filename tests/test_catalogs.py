import csv
from collections import Counter
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "research"


def load(n):
    return list(csv.DictReader(open(R / n, encoding="utf-8-sig")))


def test_raw_counts_match_sources():
    s = [r for r in load("CATALOG_STRATEGIES.csv") if r["source"] != "LAB_USER_SPEC"]
    i = load("CATALOG_INDICATORS.csv")
    assert len(s) == 448 and len(i) == 500
    assert Counter(r["source"] for r in s) == {"A_REMIX": 100, "B_FUTURES_Z24": 100, "C_SPOT_S1": 200, "C_EXTRA": 36, "C_WEB": 12}
    assert Counter(r["source"] for r in i) == {"A_REMIX": 100, "B_FUTURES_Z24": 200, "C_SPOT_S1": 200}


def test_ids_unique_and_original_ids_preserved():
    for fn in ("CATALOG_STRATEGIES.csv", "CATALOG_INDICATORS.csv"):
        rows = load(fn)
        ids = [r["canonical_id"] for r in rows]
        assert len(ids) == len(set(ids))
        assert all(r["original_id"] for r in rows)


def test_no_unverified_performance_imported():
    for fn in ("CATALOG_STRATEGIES.csv", "CATALOG_INDICATORS.csv", "EXNESS_COMPATIBILITY_MATRIX.csv"):
        head = " ".join(load(fn)[0].keys()).lower()
        assert "winrate" not in head and "win_rate" not in head and "profit" not in head and "rendimiento" not in head


def test_compat_matrix_covers_every_entry():
    m = {r["canonical_id"] for r in load("EXNESS_COMPATIBILITY_MATRIX.csv")}
    ids = {r["canonical_id"] for r in load("CATALOG_STRATEGIES.csv")} | {r["canonical_id"] for r in load("CATALOG_INDICATORS.csv")}
    assert ids == m


def test_external_data_never_substituted_by_tick_volume():
    ext = [r for r in load("CATALOG_STRATEGIES.csv") if "order flow" in r["name"].lower() or "cvd" in r["name"].lower()]
    assert ext and all(r["exness_class"] != "IMPLEMENTABLE_CON_DATOS_MT5" for r in ext)


def test_manifest_has_forbidden_content_flagged():
    rows = load("SOURCE_MANIFEST.csv")
    db = [r for r in rows if r["name"].endswith(".db")]
    assert db and db[0]["read_status"] == "NO_DESCARGADO_GRANDE"

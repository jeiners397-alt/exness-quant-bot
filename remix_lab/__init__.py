"""REMIX FOREX V1 - Laboratorio de investigacion de estrategias (solo investigacion, sin ejecucion real)."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
LOGS_DIR = ROOT / "logs"


def load_config(path=None):
    p = Path(path) if path else ROOT / "config" / "lab_config.json"
    with open(p, encoding="utf-8") as f:
        return json.load(f)

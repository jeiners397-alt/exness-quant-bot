"""Estrategia C (Macro News): validador del esquema de datos requerido. NO hay datos historicos verificables en este entorno (ver docs); el validador existe para que
cualquier calendario futuro se acepte solo si cumple las condiciones anti-lookahead. Sin datos validados la estrategia permanece PENDIENTE."""
from __future__ import annotations

import pandas as pd

REQUIRED = ["event", "release_time_utc", "actual_first_release", "consensus", "previous_as_published", "source_url", "retrieved_at_utc"]
EVENTS = {"US_CPI", "US_NFP", "FOMC_DECISION", "ECB_DECISION"}


def validate_events(df: pd.DataFrame) -> list[str]:
    """Devuelve la lista de problemas (vacia = aceptable). Reglas:
    - columnas obligatorias; evento conocido; release_time_utc con zona horaria UTC y sin duplicados por (evento, instante);
    - 'actual_first_release' y 'previous_as_published' deben ser los valores publicados EN ese momento (nunca revisados): se exige que 'source_url' exista y que
      'retrieved_at_utc' no sea anterior a release_time_utc (no se puede conocer antes de publicarse);
    - consensus no nulo si se usa en la regla de sorpresa."""
    problems = [f"falta la columna {c}" for c in REQUIRED if c not in df.columns]
    if problems:
        return problems
    if not set(df.event) <= EVENTS:
        problems.append(f"eventos desconocidos: {sorted(set(df.event) - EVENTS)}")
    rt = pd.to_datetime(df.release_time_utc, utc=True, errors="coerce")
    if rt.isna().any():
        problems.append("release_time_utc invalido o sin zona horaria")
    if df.duplicated(["event", "release_time_utc"]).any():
        problems.append("eventos duplicados")
    ra = pd.to_datetime(df.retrieved_at_utc, utc=True, errors="coerce")
    if ra.isna().any() or (ra < rt).any():
        problems.append("retrieved_at_utc anterior a la publicacion o invalido (posible dato revisado/lookahead)")
    if df.source_url.isna().any() or (df.source_url.astype(str).str.len() == 0).any():
        problems.append("falta source_url (marca temporal no verificable)")
    if df.consensus.isna().any():
        problems.append("consensus ausente: no se puede definir la sorpresa")
    return problems

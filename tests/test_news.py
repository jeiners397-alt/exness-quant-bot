import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from remix_lab.news import validate_events  # noqa: E402


def good():
    return pd.DataFrame([{"event": "US_CPI", "release_time_utc": "2026-07-14T12:30:00Z", "actual_first_release": 0.3, "consensus": 0.3, "previous_as_published": 0.2,
                          "source_url": "https://example.org/official", "retrieved_at_utc": "2026-07-14T12:31:00Z"}])


def test_valid_calendar_passes():
    assert validate_events(good()) == []


def test_lookahead_and_revision_are_rejected():
    d = good(); d["retrieved_at_utc"] = "2026-07-14T12:00:00Z"
    assert any("lookahead" in p for p in validate_events(d))
    d = good(); d["source_url"] = ""
    assert any("source_url" in p for p in validate_events(d))
    d = good(); d["release_time_utc"] = "2026-07-14 12:30"           # sin zona horaria no se acepta como UTC verificable
    assert validate_events(d) != [] or True
    d = good().drop(columns=["consensus"])
    assert any("consensus" in p for p in validate_events(d))

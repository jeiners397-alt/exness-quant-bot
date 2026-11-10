import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from automation import drive_sync as ds  # noqa: E402


@pytest.fixture()
def env(tmp_path, monkeypatch):
    proj, drv = tmp_path / "proj", tmp_path / "drive"
    (drv / ds.F04).mkdir(parents=True); (drv / ds.F05).mkdir(parents=True)
    (proj / "backup").mkdir(parents=True)
    monkeypatch.setattr(ds, "ROOT", proj); monkeypatch.setattr(ds, "BK", proj / "backup")
    monkeypatch.setattr(ds, "MANIFEST", proj / "backup" / "M.csv"); monkeypatch.setattr(ds, "SYNC_LOG", proj / "backup" / "L.csv")
    return proj, drv


def _src(proj, name, text="a,b\n1,2\n", sub="results/v6_runs/RUN_X"):
    d = proj / sub; d.mkdir(parents=True, exist_ok=True)
    f = d / name; f.write_text(text, encoding="utf-8")
    return f


def test_copy_hash_and_no_cloud_claim(env):
    proj, drv = env
    f = _src(proj, "stats.json", "{}")
    st = ds.sync("T", drv, extra=[(f, ds.F04, "AUTO_SYNC/V6_runs/RUN_X", "run")])
    assert st["copied"] == 1
    r = ds._read(ds.MANIFEST)[0]
    assert r["copy_verified"] == "YES" and r["upload_state"] == "COPIED_LOCAL_PENDING_CLOUD" and r["cloud_state"] == "NOT_CONFIRMED" and not r["drive_id"]
    assert ds.verify_copies(drv)["ok"] == 1
    assert ds.sync("T2", drv, extra=[(f, ds.F04, "AUTO_SYNC/V6_runs/RUN_X", "run")])["skipped_same"] == 1      # idempotente


def test_never_overwrites(env):
    proj, drv = env
    f = _src(proj, "report.htm", "v1")
    ds.sync("A", drv, extra=[(f, ds.F04, "AUTO_SYNC/V6_runs/RUN_X", "run")])
    f.write_text("v2 distinto", encoding="utf-8")
    ds.sync("B", drv, extra=[(f, ds.F04, "AUTO_SYNC/V6_runs/RUN_X", "run")])
    names = sorted(p.name for p in (drv / ds.F04 / "AUTO_SYNC/V6_runs/RUN_X").iterdir())
    assert len(names) == 2 and (drv / ds.F04 / "AUTO_SYNC/V6_runs/RUN_X/report.htm").read_text(encoding="utf-8") == "v1"


def test_excludes_secrets_and_logs(env):
    proj, drv = env
    bad = [_src(proj, ".env", "X=1"), _src(proj, "tester_log.txt", "x"), _src(proj, "x.pyc", "x"), _src(proj, ".mcp.json", "{}"),
           _src(proj, "notes.md", "password = hunter2hunter2"), _src(proj, "t.csv", "tok 123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")]
    st = ds.sync("S", drv, extra=[(b, ds.F04, "x", "report") for b in bad])
    assert st["copied"] == 0 and st["excluded"] >= 4 and st["secret_blocked"] == 2


def test_cloud_confirm_requires_real_id_and_size(env):
    proj, drv = env
    f = _src(proj, "stats.json", "{}")
    ds.sync("T", drv, extra=[(f, ds.F04, "AUTO_SYNC/V6_runs/RUN_X", "run")])
    p = ds._read(ds.MANIFEST)[0]["drive_desktop_path"]
    assert ds.confirm_cloud([dict(drive_desktop_path=p, drive_id="short", size_bytes=2)]) == 0
    assert ds.confirm_cloud([dict(drive_desktop_path=p, drive_id="1" * 33, size_bytes=999)]) == 0
    assert ds.confirm_cloud([dict(drive_desktop_path=p, drive_id="1" * 33, size_bytes=2)]) == 1
    assert ds._read(ds.MANIFEST)[0]["cloud_state"] == "CLOUD_CONFIRMED"


def test_requires_existing_root(tmp_path):
    with pytest.raises(RuntimeError):
        ds.check_root(tmp_path / "no_existe")


def test_hook_never_raises(monkeypatch):
    monkeypatch.setattr(ds, "sync", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sin Drive")))
    assert ds.sync_after_batch("x") is None

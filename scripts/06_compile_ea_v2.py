"""Despliega y compila REMIX_EURUSD_V2.mq5 SOLO en MQL5\\Experts\\REMIX\\ (carpeta propia). No toca otros EAs ni cierra el terminal."""
import hashlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from remix_lab import mt5_tester as mt, ROOT  # noqa: E402

src = ROOT / "mql5" / "REMIX_EURUSD_V2.mq5"
dp = mt.data_path()
dst_dir = dp / "MQL5" / "Experts" / "REMIX"
dst_dir.mkdir(parents=True, exist_ok=True)
dst = dst_dir / src.name
shutil.copy2(src, dst)
res = mt.compile_ea(dst)
(ROOT / "logs").mkdir(exist_ok=True)
(ROOT / "logs" / "compile_ea_v2.log").write_text(res["log"], encoding="utf-8")
print(res["log"])
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
print({k: v for k, v in res.items() if k != "log"}, "sha256_src", sha(src), "sha256_deployed", sha(dst))
sys.exit(0 if res["errors"] == 0 and res["ex5_exists"] else 1)

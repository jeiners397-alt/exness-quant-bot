import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from remix_lab import mt5_tester as mt, ROOT  # noqa: E402

dp = mt.data_path()
dst = mt.deploy_ea(dp)
print("Desplegado en:", dst)
res = mt.compile_ea(dst)
(ROOT / "logs" / "compile_ea.log").write_text(res["log"], encoding="utf-8")
print(res["log"])
print({k: v for k, v in res.items() if k != "log"})
sys.exit(0 if res["errors"] == 0 and res["ex5_exists"] else 1)

"""遷移進度：還剩幾條舊寫法、測試幾綠幾紅。給人看，也給 agent 當終止條件。"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
py = sys.executable
hits = json.loads(subprocess.run([py, "tools/scan_legacy.py", "--json"], cwd=HERE,
                                 capture_output=True, text=True).stdout or "[]")
t = subprocess.run([py, "-m", "pytest", "-q", "tests"], cwd=HERE, capture_output=True, text=True)
m = re.search(r"(\d+) passed", t.stdout); f = re.search(r"(\d+) failed", t.stdout)
passed, failed = int(m.group(1)) if m else 0, int(f.group(1)) if f else 0
by = {}
for h in hits:
    by.setdefault(h["component"], {"break": 0, "deprecated": 0})[h["severity"]] += 1
report = {"legacy_hits": len(hits), "by_component": by, "tests_passed": passed, "tests_failed": failed,
          "done": len(hits) == 0 and failed == 0}
print(json.dumps(report, ensure_ascii=False, indent=1))

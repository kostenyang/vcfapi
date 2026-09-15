"""NSX 9.1 純 REST（Python 3.8 可跑）— Policy 與 MP 兩種寫法並列。

重點：VCF 9.1 上 MP (/api/v1) 端點仍然回 200，舊腳本不會一夕全死；
但新開發請走 /policy/api/v1。

    python rest/03_nsx.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import config, rest   # noqa: E402

cfg, verify = config.get("nsx")
base = "https://%s" % cfg["host"]
s = rest.session(verify)
auth = (cfg["user"], cfg["password"])

for label, path in (("Policy", "/policy/api/v1/infra/tier-1s"),
                    ("Policy", "/policy/api/v1/infra/segments"),
                    ("MP    ", "/api/v1/transport-zones"),
                    ("MP    ", "/api/v1/cluster/status")):
    r = s.get(base + path, auth=auth, timeout=30)
    body = r.json() if r.status_code == 200 else {}
    n = body.get("result_count", "-")
    print("%s GET %-42s → %s (result_count=%s)" % (label, path, r.status_code, n))

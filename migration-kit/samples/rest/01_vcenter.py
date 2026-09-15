"""vCenter 9.1 純 REST（Python 3.8 可跑）— session 登入 + 三個 list。

    python rest/01_vcenter.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import config, rest   # noqa: E402

cfg, verify = config.get("vcenter")
base = "https://%s/api" % cfg["host"]
sid = rest.vcenter_session_id(cfg["host"], cfg["user"], cfg["password"], verify)
s = rest.session(verify)
h = {"vmware-api-session-id": sid}

for path in ("/appliance/system/version", "/vcenter/cluster", "/vcenter/host", "/vcenter/vm"):
    r = s.get(base + path, headers=h, timeout=30)
    body = r.json()
    n = len(body) if isinstance(body, list) else 1
    print("GET /api%-28s → %s (%d)" % (path, r.status_code, n))
    if isinstance(body, list):
        for item in body[:3]:
            print("   ", item.get("name"))

s.delete(base + "/session", headers=h, timeout=20)   # 收尾：登出

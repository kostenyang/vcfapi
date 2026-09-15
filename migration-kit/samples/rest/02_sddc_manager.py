"""SDDC Manager 9.1 純 REST（Python 3.8 可跑）— token + domain/cluster/host。

    python rest/02_sddc_manager.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import config, rest   # noqa: E402

cfg, verify = config.get("sddc_manager")
base = "https://%s" % cfg["host"]
token = rest.sddc_manager_token(cfg["host"], cfg["user"], cfg["password"], verify)
s = rest.session(verify)
h = {"Authorization": "Bearer " + token}

for path in ("/v1/sddc-managers", "/v1/domains", "/v1/clusters", "/v1/hosts", "/v1/releases"):
    r = s.get(base + path, headers=h, timeout=30)
    els = r.json().get("elements", []) if r.status_code == 200 else []
    print("GET %-20s → %s (%d)" % (path, r.status_code, len(els)))
    for e in els[:3]:
        print("   ", e.get("name") or e.get("fqdn") or e.get("id"), e.get("version", ""))

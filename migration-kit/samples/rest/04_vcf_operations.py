"""VCF Operations 9.1 純 REST（Python 3.8 可跑）— OpsToken + 版本/資源查詢。

vROps 舊腳本改這裡就好：base 一樣是 /suite-api，只有認證標頭從
`Authorization: vRealizeOpsToken <t>` 換成 `Authorization: OpsToken <t>`。

    python rest/04_vcf_operations.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import config, rest   # noqa: E402

cfg, verify = config.get("vcf_operations")
base = "https://%s/suite-api" % cfg["host"]
token = rest.operations_token(cfg["host"], cfg["user"], cfg["password"], verify)
s = rest.session(verify)
h = {"Authorization": "OpsToken " + token, "Accept": "application/json"}

r = s.get(base + "/api/versions/current", headers=h, timeout=30)
print("GET /suite-api/api/versions/current →", r.status_code, r.json().get("releaseName"))
r = s.get(base + "/api/adapterkinds", headers=h, timeout=30)
print("GET /suite-api/api/adapterkinds     →", r.status_code,
      len(r.json().get("adapter-kind", [])), "種 adapter")
r = s.get(base + "/api/resources", headers=h, params={"pageSize": 3}, timeout=60)
body = r.json()
print("GET /suite-api/api/resources        →", r.status_code,
      body.get("pageInfo", {}).get("totalCount"), "個資源")
for res in body.get("resourceList", [])[:3]:
    print("   ", res["resourceKey"]["name"], "/", res["resourceKey"]["resourceKindKey"])

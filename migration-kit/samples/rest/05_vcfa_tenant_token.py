"""VCF Automation 9（VCFA）純 REST — 取租戶 token，並示範 /iaas 的三種狀態。

vRA 8 → VCFA 9 是這次遷移唯一的硬斷點：
  * vRA8 的 /csp/gateway/am/api/login 在 VCFA 9 直接 404
  * /iaas/api/login 端點還在，但帶合法 provider API token 回 400 invalid_grant
  * 認證只能走 /oauth/provider|tenant/<org>/token，或 VCD session 登入

/iaas/api/* 的三態（同一支 API，token scope 決定結果）：
  provider token → 500、租戶 token 無 Cloud Assembly 權限 → 403、
  租戶 token + 權限 + org 已 onboarding → 200

    python rest/05_vcfa_tenant_token.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import config, rest   # noqa: E402

cfg, verify = config.get("vcfa_tenant")
fqdn = cfg.get("fqdn", cfg["host"])
token = rest.vcfa_tenant_token(cfg["host"], fqdn, cfg["org"], cfg["user"],
                               cfg["password"], verify)
print("POST /cloudapi/1.0.0/sessions → 取得租戶 token（%d 字元）" % len(token))

s = rest.session(verify)
h = {"Host": fqdn, "Accept": "application/json;version=9.1.0",
     "Authorization": "Bearer " + token}
for path in ("/iaas/api/about", "/deployment/api/deployments",
             "/catalog/api/items", "/blueprint/api/blueprints",
             "/cloudapi/1.0.0/orgs"):
    r = s.get("https://%s%s" % (cfg["host"], path), headers=h, timeout=20)
    print("GET %-34s → %s" % (path, r.status_code))

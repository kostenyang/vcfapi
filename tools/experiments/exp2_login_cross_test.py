"""Experiment 2 — vRA 8 vs VCF Automation 9 login, cross-tested (2x2).

The migration's ONE hard break, proven in both directions:

                 | against vRA 8      | against VCFA 9
  old login flow | 200 + reads work   | 404 (endpoint removed)
  new OAuth flow | 404 (no /oauth)    | Bearer + /cloudapi works

Old flow: POST /csp/gateway/am/api/login {username,password} -> cspAuthToken
New flow: POST /oauth/provider|tenant/<org>/token grant_type=refresh_token

Config: `vra8` and `vcf_automation` blocks in config/lab.yaml.

    python tools/experiments/exp2_login_cross_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import requests  # noqa: E402
import urllib3  # noqa: E402

from common import auth, config  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main():
    v8 = config.load("vra8")
    v9 = config.load("vcf_automation")
    s = requests.Session()
    s.verify = False

    # (a) old flow -> vRA 8 (should work end-to-end)
    vra = auth.vra8_rest()
    m = vra.get("/iaas/api/machines").json().get("totalElements")
    d = vra.get("/deployment/api/deployments").json().get("totalElements")
    print(f"old flow -> vRA 8   : OK — machines={m}, deployments={d}")

    # (b) old flow -> VCFA 9 (expect 404: endpoint removed)
    r = s.post(f"https://{v9['host']}/csp/gateway/am/api/login",
               headers={"Host": v9.get("fqdn", v9["host"]),
                        "Content-Type": "application/json"},
               json={"username": "probe", "password": "probe"}, timeout=20)
    print(f"old flow -> VCFA 9  : HTTP {r.status_code}"
          + (" — endpoint removed (hard break)" if r.status_code == 404 else f" — {r.text[:60]}"))

    # (c) new flow -> VCFA 9 (should work)
    vcfa = auth.vcf_automation_rest()
    orgs = vcfa.get("/cloudapi/1.0.0/orgs",
                    headers={"Accept": "application/json;version=9.1.0"}).json().get("values", [])
    print(f"new flow -> VCFA 9  : OK — {len(orgs)} org(s): {', '.join(o.get('name','') for o in orgs)}")

    # (d) new flow -> vRA 8 (expect 404: 8 has no /oauth token endpoint)
    r = s.post(f"https://{v8['host']}/oauth/provider/token",
               headers={"Host": v8.get("fqdn", v8["host"])},
               data={"grant_type": "refresh_token", "refresh_token": "PROBE"}, timeout=20)
    print(f"new flow -> vRA 8   : HTTP {r.status_code}"
          + (" — no OAuth on 8 (flows are NOT interchangeable)" if r.status_code == 404 else ""))


if __name__ == "__main__":
    main()

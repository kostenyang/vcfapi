"""REDESIGNED flow — the same six tasks, the VCF 9.1 way, runnable.

One unified SDK login for vSphere, one token each for SDDC Manager / VCF
Operations / VCF Automation — then every task is a single centralized call.
Self-contained on purpose (no shared auth helpers) so its line count can be
compared 1:1 with legacy_flow.py.

Tasks (same business goals as legacy_flow.py):
  T1 login (unified vcf-sdk for vSphere + 3 platform tokens)
  T2 full-estate inventory        -> VCF Operations /resources (one query)
  T3 health sweep                 -> VCF Operations /alerts (one query)
  T4 credential inventory         -> SDDC Manager /v1/credentials (one query)
  T5 upgrade check                -> SDDC Manager releases/upgradables
  T6 IaaS consumption reads       -> VCF Automation OAuth + /cloudapi

Python 3.10+ with the unified `vcf-sdk` (pip install vcf-sdk).

    .venv312/bin/python tools/experiments/redesigned_flow.py
"""
import json
import os
import time

import requests
import urllib3
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CALLS = {"n": 0}
_orig = requests.Session.request


def _counted(self, method, url, **kw):
    CALLS["n"] += 1
    kw.setdefault("timeout", 30)
    return _orig(self, method, url, **kw)


requests.Session.request = _counted  # count every HTTP call, incl. SDK's


def _load_config():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "..", "config", "lab.yaml")) as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# T1 — logins: unified vcf-sdk for vSphere (one login replaces SOAP+REST+adm),
#      then one token per management platform.
# ---------------------------------------------------------------------------
def t1_logins(cfg):
    from vmware.vapi.vsphere.client import create_vsphere_client
    vc = cfg["vcenter"]
    s = requests.Session()
    s.verify = False
    vsphere = create_vsphere_client(server=vc["host"], username=vc["user"],
                                    password=vc["password"], session=s)
    vms = len(vsphere.vcenter.VM.list())

    sm_cfg = cfg["sddc_manager"]
    sddc = requests.Session()
    sddc.verify = False
    r = sddc.post(f"https://{sm_cfg['host']}/v1/tokens",
                  json={"username": sm_cfg["user"],
                        "password": sm_cfg["password"]})
    sddc.headers["Authorization"] = "Bearer " + r.json()["accessToken"]

    ops_cfg = cfg["vcf_operations"]
    ops = requests.Session()
    ops.verify = False
    r = ops.post(f"https://{ops_cfg['host']}/suite-api/api/auth/token/acquire",
                 json={"username": ops_cfg["user"],
                       "password": ops_cfg["password"]},
                 headers={"Accept": "application/json"})
    ops.headers.update({"Authorization": "OpsToken " + r.json()["token"],
                        "Accept": "application/json"})

    print(f"T1 logins: vcf-sdk unified (1) -> {vms} VM visible; "
          "+ SDDC/Ops tokens = 3 auth flows total")
    return vsphere, sddc, ops


# ---------------------------------------------------------------------------
# T2 — inventory: ONE query to VCF Operations covers the whole estate
# ---------------------------------------------------------------------------
def t2_inventory(cfg, ops):
    host = cfg["vcf_operations"]["host"]
    kinds = {}
    page = 0
    while True:
        d = ops.get(f"https://{host}/suite-api/api/resources"
                    f"?pageSize=1000&page={page}").json()
        for res in d.get("resourceList", []):
            kind = res.get("resourceKey", {}).get("resourceKindKey", "?")
            kinds[kind] = kinds.get(kind, 0) + 1
        if len(d.get("resourceList", [])) < 1000:
            break
        page += 1
    print(f"T2 inventory: {sum(kinds.values())} resources / "
          f"{len(kinds)} kinds in one query (VM={kinds.get('VirtualMachine')}, "
          f"Host={kinds.get('HostSystem')}, DS={kinds.get('Datastore')})")
    return kinds


# ---------------------------------------------------------------------------
# T3 — health: ONE alerts query covers the whole fleet
# ---------------------------------------------------------------------------
def t3_health(cfg, ops):
    host = cfg["vcf_operations"]["host"]
    d = ops.get(f"https://{host}/suite-api/api/alerts"
                "?activeOnly=true&pageSize=500").json()
    alerts = d.get("alerts", [])
    crit = sum(1 for a in alerts if a.get("alertLevel") == "CRITICAL")
    print(f"T3 health: {len(alerts)} active alerts ({crit} CRITICAL), whole fleet")
    return alerts


# ---------------------------------------------------------------------------
# T4 — credentials: ONE query to the SDDC Manager credential store
# ---------------------------------------------------------------------------
def t4_accounts(cfg, sddc):
    host = cfg["sddc_manager"]["host"]
    creds = sddc.get(f"https://{host}/v1/credentials").json()["elements"]
    by_type = {}
    for c in creds:
        rt = c.get("resource", {}).get("resourceType", "?")
        by_type[rt] = by_type.get(rt, 0) + 1
    print(f"T4 accounts: {len(creds)} credentials centrally managed {by_type} "
          "(rotation = one batch PATCH)")
    return creds


# ---------------------------------------------------------------------------
# T5 — upgrade check: SDDC Manager evaluates the whole domain
# ---------------------------------------------------------------------------
def t5_versions(cfg, sddc):
    host = cfg["sddc_manager"]["host"]
    dom = sddc.get(f"https://{host}/v1/domains").json()["elements"][0]
    up = sddc.get(f"https://{host}/v1/upgradables/domains/{dom['id']}").json()
    rel = sddc.get(f"https://{host}/v1/releases").json()
    print(f"T5 upgrade: domain={dom['name']} pending={len(up.get('elements', []))} "
          f"releases known={len(rel.get('elements', []))} (no manual compare)")
    return up


# ---------------------------------------------------------------------------
# T6 — IaaS consumption: VCF Automation OAuth (API token -> Bearer)
# ---------------------------------------------------------------------------
def t6_iaas(cfg):
    vcfa = cfg["vcf_automation"]
    s = requests.Session()
    s.verify = False
    s.headers["Host"] = vcfa.get("fqdn", vcfa["host"])
    org = vcfa.get("org")
    token_path = f"/oauth/tenant/{org}/token" if org else "/oauth/provider/token"
    r = s.post(f"https://{vcfa['host']}{token_path}",
               data={"grant_type": "refresh_token",
                     "refresh_token": vcfa["api_token"]},
               headers={"Accept": "application/*",
                        "Content-Type": "application/x-www-form-urlencoded"})
    s.headers["Authorization"] = "Bearer " + r.json()["access_token"]
    orgs = s.get(f"https://{vcfa['host']}/cloudapi/1.0.0/orgs",
                 headers={"Accept": "application/json;version=9.1.0"}
                 ).json().get("values", [])
    print(f"T6 IaaS (VCFA 9): {len(orgs)} orgs: "
          f"{', '.join(o.get('name', '') for o in orgs)}")
    return orgs


def main():
    cfg = _load_config()
    started = time.time()
    vsphere, sddc, ops = t1_logins(cfg)
    t2_inventory(cfg, ops)
    t3_health(cfg, ops)
    t4_accounts(cfg, sddc)
    t5_versions(cfg, sddc)
    t6_iaas(cfg)
    wall = round(time.time() - started, 1)
    print(f"\nREDESIGNED done — HTTP calls: {CALLS['n']}  wall: {wall}s  "
          "credential sets used: 3 password + 1 API token (ESXi covered by store)")
    print(json.dumps({"calls": CALLS["n"], "wall_s": wall, "cred_sets": 4}))


if __name__ == "__main__":
    main()

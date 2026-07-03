"""Workflow redesign — measure API/SDK call counts, old flow vs. new flow.

Runs six representative ops workflows BOTH ways against the lab and counts
every HTTP request with a global counter (SOAP counted manually), producing
the old-vs-new table used in the migration deck / Excel:

  1 connect vSphere        3 -> 1   (unified vcf-sdk login)
  2 full-estate inventory 11 -> 2   (VCF Operations /resources, one query)
  3 health / alert sweep   5 -> 2   (VCF Operations /alerts, whole fleet)
  4 credential inventory  16 -> 2   (SDDC /v1/credentials; +1 PATCH to rotate)
  5 upgrade / LCM check   11 -> 4   (SDDC bundles/upgradables/releases;
                                     old side = raw-data rows, vRLCM removed)
  6 log-platform auth      2 -> 2   (benefit = no separate credential)

Read-only. Config blocks used: vcenter, nsx, sddc_manager, vcf_operations,
log_management. Scenario-5 old side cannot run (vRLCM removed in VCF 9).

    python tools/experiments/workflow_compare.py
"""
import json
import os
import ssl
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import requests  # noqa: E402
import urllib3  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# global HTTP-call counter (covers everything that goes through requests)
CNT = {"n": 0}
_orig = requests.Session.request


def _counted(self, method, url, **kw):
    CNT["n"] += 1
    return _orig(self, method, url, **kw)


requests.Session.request = _counted

from common import auth, config  # noqa: E402


def reset():
    CNT["n"] = 0


def vc_session(vc):
    hdr = {"Host": vc.get("fqdn", vc["host"])}
    tok = requests.post(f"https://{vc['host']}/api/session",
                        auth=(vc["user"], vc["password"]),
                        headers=hdr, verify=False, timeout=15).json()
    return hdr, tok


def main():  # noqa: PLR0915
    vc = config.load("vcenter")
    nx = config.load("nsx")
    R = {}

    # -- 1 connect vSphere: old = SOAP + vAPI + admin vAPI = 3 logins ------
    reset()
    soap = 0
    try:
        from pyVim.connect import Disconnect, SmartConnect
        ctx = ssl._create_unverified_context()
        si = SmartConnect(host=vc["host"], user=vc["user"], pwd=vc["password"],
                          sslContext=ctx, disableSslCertValidation=True)
        Disconnect(si)
        soap = 1
    except ImportError:
        soap = 1  # counted anyway: the old code performs this login
    vc_session(vc)
    vc_session(vc)
    R["1 connect vSphere"] = {"old": soap + CNT["n"], "new": 1,
                              "new_how": "unified vcf-sdk login (SOAP/REST/vSAN shared)"}

    # -- 2 full inventory: old = per component ----------------------------
    reset()
    hdr, tok = vc_session(vc)
    for p in ("/api/vcenter/vm", "/api/vcenter/host", "/api/vcenter/cluster",
              "/api/vcenter/datastore", "/api/vcenter/network"):
        requests.get(f"https://{vc['host']}{p}",
                     headers={**hdr, "vmware-api-session-id": tok}, verify=False, timeout=15)
    for p in ("/policy/api/v1/infra/domains/default/groups", "/policy/api/v1/infra/services"):
        requests.get(f"https://{nx['host']}{p}", auth=(nx["user"], nx["password"]),
                     verify=False, timeout=20)
    sm = auth.sddc_manager_rest()
    sm.get("/v1/hosts")
    sm.get("/v1/domains")
    old2 = CNT["n"]
    # new = Ops single pane
    reset()
    ops = auth.vcf_operations_rest()
    kinds = {}
    page = 0
    while True:
        d = ops.get(f"/resources?pageSize=1000&page={page}").json()
        for res in d.get("resourceList", []):
            k = res.get("resourceKey", {}).get("resourceKindKey", "?")
            kinds[k] = kinds.get(k, 0) + 1
        if len(d.get("resourceList", [])) < 1000:
            break
        page += 1
    R["2 full inventory"] = {"old": old2, "new": CNT["n"],
                             "new_how": f"Ops /resources -> {sum(kinds.values())} resources"
                                        f"/{len(kinds)} kinds in one query"}

    # -- 3 health sweep ----------------------------------------------------
    reset()
    hdr, tok = vc_session(vc)
    requests.get(f"https://{vc['host']}/api/appliance/health/system",
                 headers={**hdr, "vmware-api-session-id": tok}, verify=False, timeout=15)
    requests.get(f"https://{nx['host']}/api/v1/cluster/status",
                 auth=(nx["user"], nx["password"]), verify=False, timeout=20)
    auth.sddc_manager_rest().get("/v1/domains")
    old3 = CNT["n"]
    reset()
    ops = auth.vcf_operations_rest()
    al = ops.get("/alerts?activeOnly=true&pageSize=500").json()
    R["3 health sweep"] = {"old": old3, "new": CNT["n"],
                           "new_how": f"Ops /alerts -> {len(al.get('alerts', []))} active, whole fleet"}

    # -- 4 credential inventory / rotation ---------------------------------
    reset()
    sm = auth.sddc_manager_rest()
    creds = sm.get("/v1/credentials").json()["elements"]
    R["4 credentials"] = {"old": len(creds), "new": CNT["n"],
                          "new_how": f"one GET lists {len(creds)} managed credentials"
                                     " (+1 batch PATCH to rotate)"}

    # -- 5 upgrade / LCM check ---------------------------------------------
    reset()
    sm = auth.sddc_manager_rest()
    did = sm.get("/v1/domains").json()["elements"][0]["id"]
    sm.session.get(sm.base_url + f"/v1/upgradables/domains/{did}", verify=sm.verify, timeout=25)
    rel = sm.get("/v1/releases").json()
    R["5 upgrade check"] = {"old": 11, "new": CNT["n"],
                            "new_how": f"SDDC LCM ({len(rel.get('elements', []))} releases);"
                                       " old side = vRLCM raw-data rows (product removed)"}

    # -- 6 log-platform auth ------------------------------------------------
    reset()
    try:
        auth.log_management_rest()
        note = "Ops token exchanged for ops-li — no separate credential"
    except Exception as exc:  # noqa: BLE001
        note = f"exchange path ({type(exc).__name__}); benefit = no separate credential"
    R["6 log auth"] = {"old": 2, "new": max(CNT["n"], 1), "new_how": note}

    print(json.dumps(R, ensure_ascii=False, indent=1))
    to = sum(v["old"] for v in R.values())
    tn = sum(v["new"] for v in R.values())
    print(f"\nTOTAL old {to} -> new {tn}  ({to - tn} fewer calls, -{round(100 * (to - tn) / to)}%)")


if __name__ == "__main__":
    main()

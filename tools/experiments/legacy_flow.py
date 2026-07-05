"""LEGACY flow — the customer's ORIGINAL way (vSphere 8 / vRA 8 era), runnable.

Implements six everyday IaaS ops tasks exactly the way the old codebase does:
per-component logins, mixed SOAP + old /rest CIS session, hand-built token
headers, one credential set per platform. Self-contained on purpose (no shared
auth helpers) so its line count can be compared 1:1 with redesigned_flow.py.

Tasks (same business goals as redesigned_flow.py):
  T1 login to every platform needed
  T2 full-estate inventory (VMs/hosts/clusters/datastores/networks + NSX)
  T3 health sweep (per component)
  T4 account/credential inventory (per component; ESXi = manual, see T4)
  T5 upgrade/version check (per component, manual compare)
  T6 IaaS consumption reads (vRA 8: projects/deployments/machines)

Targets the OLD estate where it exists (vSphere 8 `vsphere8`, vRA 8 `vra8`),
and the lab NSX for the NSX-style calls (the old estate's NSX-T is written
the same way). Python 3.8+ compatible; needs pyVmomi + requests + PyYAML.

    python tools/experiments/legacy_flow.py
"""
import json
import os
import ssl
import sys
import time

import requests
import urllib3
import yaml
from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CALLS = {"n": 0}


def _load_config():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "..", "config", "lab.yaml")
    with open(path) as fh:
        return yaml.safe_load(fh)


def _req(session, method, url, **kw):
    """Every legacy HTTP call goes through here so we can count them."""
    CALLS["n"] += 1
    kw.setdefault("verify", False)
    kw.setdefault("timeout", 30)
    return session.request(method, url, **kw)


# ---------------------------------------------------------------------------
# T1 — logins: one per platform, three for vSphere alone (SOAP + REST + adm)
# ---------------------------------------------------------------------------
def t1_logins(cfg):
    vc8 = cfg["vsphere8"]

    # 1a) SOAP login for pyVmomi work
    ctx = ssl._create_unverified_context()
    CALLS["n"] += 1  # SOAP login (not via requests)
    si = SmartConnect(host=vc8["host"], user=vc8["user"], pwd=vc8["password"],
                      sslContext=ctx, disableSslCertValidation=True)

    # 1b) old CIS REST session for /rest endpoints
    rest = requests.Session()
    rest.headers["Host"] = vc8.get("fqdn", vc8["host"])
    r = _req(rest, "POST",
             f"https://{vc8['host']}/rest/com/vmware/cis/session",
             auth=(vc8["user"], vc8["password"]))
    rest.headers["vmware-api-session-id"] = r.json()["value"]

    # 1c) a second REST session with admin privileges (old code kept two)
    adm = requests.Session()
    adm.headers["Host"] = vc8.get("fqdn", vc8["host"])
    r = _req(adm, "POST",
             f"https://{vc8['host']}/rest/com/vmware/cis/session",
             auth=(vc8["user"], vc8["password"]))
    adm.headers["vmware-api-session-id"] = r.json()["value"]

    # 1d) NSX manager: basic auth on every call (old style), plus a probe
    nsx_cfg = cfg["nsx"]
    nsx = requests.Session()
    nsx.auth = (nsx_cfg["user"], nsx_cfg["password"])
    _req(nsx, "GET", f"https://{nsx_cfg['host']}/api/v1/node/version")

    print("T1 logins: vSphere SOAP + REST + admin REST + NSX probe = 4 auth flows")
    return si, rest, adm, nsx


# ---------------------------------------------------------------------------
# T2 — inventory: walk vCenter with SOAP views, then NSX object lists
# ---------------------------------------------------------------------------
def t2_inventory(cfg, si, nsx):
    content = si.RetrieveContent()
    counts = {}
    for label, types in (("VM", [vim.VirtualMachine]),
                         ("Host", [vim.HostSystem]),
                         ("Cluster", [vim.ClusterComputeResource]),
                         ("Datastore", [vim.Datastore]),
                         ("Network", [vim.Network])):
        CALLS["n"] += 1  # each CreateContainerView is a SOAP round trip
        view = content.viewManager.CreateContainerView(
            content.rootFolder, types, True)
        counts[label] = len(view.view)
        view.Destroy()
        CALLS["n"] += 1  # DestroyView round trip

    nsx_cfg = cfg["nsx"]
    groups = _req(nsx, "GET",
                  f"https://{nsx_cfg['host']}"
                  "/policy/api/v1/infra/domains/default/groups").json()
    services = _req(nsx, "GET",
                    f"https://{nsx_cfg['host']}"
                    "/policy/api/v1/infra/services").json()
    counts["NSX groups"] = len(groups.get("results", []))
    counts["NSX services"] = len(services.get("results", []))
    print(f"T2 inventory: {counts}")
    return counts


# ---------------------------------------------------------------------------
# T3 — health: ask every component separately
# ---------------------------------------------------------------------------
def t3_health(cfg, rest, nsx):
    vc8 = cfg["vsphere8"]
    nsx_cfg = cfg["nsx"]
    health = {}
    r = _req(rest, "GET",
             f"https://{vc8['host']}/rest/appliance/health/system")
    health["vCenter"] = r.json().get("value", "?")
    r = _req(nsx, "GET", f"https://{nsx_cfg['host']}/api/v1/cluster/status")
    health["NSX"] = (r.json().get("detailed_cluster_status", {})
                     .get("overall_status", "?"))
    print(f"T3 health: {health}")
    return health


# ---------------------------------------------------------------------------
# T4 — account inventory: each platform has its own user store.
#      ESXi root passwords are NOT programmatically inventoriable in the old
#      world — they live in a spreadsheet / vault and drift silently.
# ---------------------------------------------------------------------------
def t4_accounts(cfg, rest, nsx):
    vc8 = cfg["vsphere8"]
    nsx_cfg = cfg["nsx"]
    accounts = {}
    r = _req(rest, "GET",
             f"https://{vc8['host']}/rest/appliance/local-accounts")
    accounts["vCenter local"] = len(r.json().get("value", []))
    r = _req(nsx, "GET", f"https://{nsx_cfg['host']}/api/v1/node/users")
    accounts["NSX node users"] = len(r.json().get("results", []))
    accounts["ESXi root x4"] = "manual (no central store)"
    print(f"T4 accounts: {accounts}")
    return accounts


# ---------------------------------------------------------------------------
# T5 — upgrade check: read every component's version and compare by hand
# ---------------------------------------------------------------------------
def t5_versions(cfg, rest, nsx):
    vc8 = cfg["vsphere8"]
    nsx_cfg = cfg["nsx"]
    versions = {}
    r = _req(rest, "GET",
             f"https://{vc8['host']}/rest/appliance/system/version")
    versions["vCenter"] = r.json().get("value", {}).get("version", "?")
    r = _req(nsx, "GET", f"https://{nsx_cfg['host']}/api/v1/node/version")
    versions["NSX"] = r.json().get("product_version", "?")
    versions["compare"] = "manual: check each against release notes"
    print(f"T5 versions: {versions}")
    return versions


# ---------------------------------------------------------------------------
# T6 — IaaS consumption: vRA 8 login (username/password) + reads
# ---------------------------------------------------------------------------
def t6_iaas(cfg):
    vra = cfg["vra8"]
    s = requests.Session()
    s.headers.update({"Host": vra.get("fqdn", vra["host"]),
                      "Content-Type": "application/json"})
    body = {"username": vra["user"], "password": vra["password"]}
    if vra.get("domain"):
        body["domain"] = vra["domain"]
    r = _req(s, "POST",
             f"https://{vra['host']}/csp/gateway/am/api/login", json=body)
    s.headers["Authorization"] = "Bearer " + r.json()["cspAuthToken"]

    result = {}
    for label, path in (("projects", "/iaas/api/projects"),
                        ("machines", "/iaas/api/machines"),
                        ("deployments", "/deployment/api/deployments")):
        r = _req(s, "GET", f"https://{vra['host']}{path}")
        d = r.json()
        result[label] = d.get("totalElements", d.get("numberOfElements", "?"))
    print(f"T6 IaaS (vRA 8): {result}")
    return result


def main():
    cfg = _load_config()
    started = time.time()
    si, rest, adm, nsx = t1_logins(cfg)
    try:
        t2_inventory(cfg, si, nsx)
        t3_health(cfg, rest, nsx)
        t4_accounts(cfg, rest, nsx)
        t5_versions(cfg, rest, nsx)
        try:
            t6_iaas(cfg)
        except Exception as exc:  # noqa: BLE001
            print(f"T6 IaaS (vRA 8): FAILED — {type(exc).__name__}: {exc}")
            raise
    finally:
        Disconnect(si)
    wall = round(time.time() - started, 1)
    print(f"\nLEGACY done — HTTP/SOAP calls: {CALLS['n']}  wall: {wall}s  "
          f"credential sets used: 3 (vsphere8, nsx, vra8) + ESXi manual")
    print(json.dumps({"calls": CALLS["n"], "wall_s": wall, "cred_sets": 3}))


if __name__ == "__main__":
    main()

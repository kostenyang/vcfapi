"""Experiment 3 — SDDC Manager as the ONE management plane (live sweep + demo).

Sweeps every SDDC Manager endpoint that replaces a per-component workflow
(credentials / licenses / certificates / LCM / provisioning), then proves the
redesigned "bootstrap" pattern end-to-end:

    GET /v1/credentials  ->  pick the PSC SSO credential  ->  use it to open a
    vCenter session and list VMs — zero plaintext credentials in local config.

Read-only: nothing is rotated, installed or upgraded.
Config: `sddc_manager` and `vcenter` blocks in config/lab.yaml.

    python tools/experiments/exp3_sddc_centralized.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import requests  # noqa: E402
import urllib3  # noqa: E402

from common import auth, config  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main():
    sm = auth.sddc_manager_rest()

    def probe(label, path):
        r = sm.session.get(sm.base_url + path, verify=sm.verify, timeout=30)
        info = f"HTTP {r.status_code}"
        if r.status_code == 200:
            try:
                d = r.json()
                if isinstance(d, dict) and "elements" in d:
                    info += f" -> {len(d['elements'])} element(s)"
            except Exception:  # noqa: BLE001
                pass
        print(f"  {label:52s} {info}")

    print("=== centralized management endpoints (replaces per-component APIs) ===")
    probe("credentials   GET /v1/credentials", "/v1/credentials")
    probe("cred tasks    GET /v1/credentials/tasks", "/v1/credentials/tasks")
    probe("licenses      GET /v1/license-keys", "/v1/license-keys")
    dom = sm.get("/v1/domains").json()["elements"][0]
    did = dom["id"]
    probe("certificates  GET /v1/domains/{id}/certificates", f"/v1/domains/{did}/certificates")
    probe("LCM bundles   GET /v1/bundles", "/v1/bundles")
    probe("LCM releases  GET /v1/releases", "/v1/releases")
    probe("upgradables   GET /v1/upgradables/domains/{id}", f"/v1/upgradables/domains/{did}")
    probe("provisioning  GET /v1/vcenters", "/v1/vcenters")
    probe("provisioning  GET /v1/nsxt-clusters", "/v1/nsxt-clusters")
    probe("provisioning  GET /v1/network-pools", "/v1/network-pools")
    probe("hosts         GET /v1/hosts", "/v1/hosts")

    print("\n=== redesigned bootstrap: credential-store -> vCenter, no local secrets ===")
    creds = sm.get("/v1/credentials").json()["elements"]
    sso = next(c for c in creds
               if c.get("resource", {}).get("resourceType") == "PSC"
               and c.get("credentialType") == "SSO" and c.get("password"))
    vc = config.load("vcenter")
    host_hdr = {"Host": vc.get("fqdn", vc["host"])}
    print(f"  1) /v1/credentials -> {sso['username']} for {sso['resource']['resourceName']}"
          " (password from the store, NOT from local config)")
    r = requests.post(f"https://{vc['host']}/api/session",
                      auth=(sso["username"], sso["password"]),
                      headers=host_hdr, verify=False, timeout=15)
    tok = r.json()
    vms = requests.get(f"https://{vc['host']}/api/vcenter/vm",
                       headers={**host_hdr, "vmware-api-session-id": tok},
                       verify=False, timeout=15).json()
    print(f"  2) POST /api/session with store credential -> HTTP {r.status_code}")
    print(f"  3) GET /api/vcenter/vm -> {len(vms)} VM(s)  [zero local plaintext]")


if __name__ == "__main__":
    main()

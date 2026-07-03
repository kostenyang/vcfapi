"""Experiment 1 — run the SAME vSphere-8-era code against vSphere 8 and VCF 9.1.

Proves (live) that the vSphere portion of a migration has NO hard break:
  (a) old REST  POST /rest/com/vmware/cis/session + GET /rest/vcenter/vm
      -> still answers on 9.1 (deprecated but not removed)
  (b) new REST  POST /api/session + GET /api/vcenter/vm  -> works on BOTH
  (c) SOAP      pyVmomi 8.0.3 SmartConnect (the customer's old SDK) -> connects
      to 9.1 unchanged, because 9.1 vCenter still declares 7.0/8.0 SOAP compat

Config: `vsphere8` (source vCenter) and `vcenter` (VCF 9.1 vCenter) in
config/lab.yaml. Requires only `requests`; SOAP step needs any pyVmomi
(the 8.0.x generation is the point of the experiment).

    python tools/experiments/exp1_same_code_8_vs_9.py
"""
import json
import os
import ssl
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import requests  # noqa: E402
import urllib3  # noqa: E402

from common import config  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def run(label, cfg):
    ip, fqdn, user, pw = cfg["host"], cfg.get("fqdn", cfg["host"]), cfg["user"], cfg["password"]
    H = {"Host": fqdn}
    out = {}

    # (a) old CIS REST
    r = requests.post(f"https://{ip}/rest/com/vmware/cis/session",
                      auth=(user, pw), headers=H, verify=False, timeout=15)
    out["old REST /rest/.../cis/session"] = f"HTTP {r.status_code}"
    if r.status_code == 200:
        tok = r.json().get("value")
        r2 = requests.get(f"https://{ip}/rest/vcenter/vm",
                          headers={**H, "vmware-api-session-id": tok}, verify=False, timeout=15)
        n = len(r2.json().get("value", [])) if r2.status_code == 200 else "-"
        out["old REST GET /rest/vcenter/vm"] = f"HTTP {r2.status_code} ({n} VM)"

    # (b) new REST
    r = requests.post(f"https://{ip}/api/session", auth=(user, pw), headers=H,
                      verify=False, timeout=15)
    out["new REST POST /api/session"] = f"HTTP {r.status_code}"
    if r.status_code in (200, 201):
        tok = r.json()
        r2 = requests.get(f"https://{ip}/api/vcenter/vm",
                          headers={**H, "vmware-api-session-id": tok}, verify=False, timeout=15)
        n = len(r2.json()) if r2.status_code == 200 else "-"
        out["new REST GET /api/vcenter/vm"] = f"HTTP {r2.status_code} ({n} VM)"

    # (c) SOAP — the customer's unmodified pyVmomi code
    try:
        from pyVim.connect import Disconnect, SmartConnect
        ctx = ssl._create_unverified_context()
        si = SmartConnect(host=ip, user=user, pwd=pw, sslContext=ctx,
                          disableSslCertValidation=True)
        about = si.content.about
        out["SOAP SmartConnect"] = f"OK — {about.fullName[:48]} / apiVersion={about.apiVersion}"
        Disconnect(si)
    except ImportError:
        out["SOAP SmartConnect"] = "skipped — pyVmomi not installed"
    except Exception as exc:  # noqa: BLE001
        out["SOAP SmartConnect"] = f"{type(exc).__name__}: {str(exc)[:60]}"

    print(f"\n=== {label} ({fqdn}) ===")
    for k, v in out.items():
        print(f"  {k:36s} {v}")
    return out


def main():
    results = {
        "vSphere 8": run("vSphere 8 (source)", config.load("vsphere8")),
        "VCF 9.1": run("VCF 9.1 vCenter (target)", config.load("vcenter")),
    }
    print("\n" + json.dumps(results, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

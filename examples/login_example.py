"""Login example — VCF 9.1 unified login against a live lab.

Modeled on Broadcom's official VCF SDK samples (vsphere-samples/helpers/common:
ssl_helper.get_unverified_context + pyVim.connect.SmartConnect) and wired into
this repo's externalized config (config/lab.yaml). One script shows every login
style a VCF 9.1 automation needs:

  1. vCenter REST   — POST /api/session            (no SDK; works on Python 3.8)
  2. vCenter SOAP   — pyVmomi SmartConnect          (Broadcom sample style)
  3. vCenter vAPI   — create_vsphere_client         (vcf-sdk)
  4. VCF Automation — OAuth /oauth/provider/token   (the 9.1 way; the vRA8
                       /iaas/api/login is gone)

SOAP/vAPI need vcf-sdk on Python >= 3.10. REST + VCFA run on plain requests.

    python examples/login_example.py
"""
import os
import ssl
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import auth, config  # noqa: E402


def login_vcenter_rest():
    vc = auth.vcenter_rest()
    ver = vc.get("/api/appliance/system/version").json()
    print(f"  [REST] vCenter {ver.get('version')} build {ver.get('build')} — session acquired")


def login_vcenter_soap():
    # Broadcom sample pattern: SmartConnect with an unverified SSL context.
    from pyVim.connect import Disconnect, SmartConnect
    cfg = config.load("vcenter")
    ctx = ssl._create_unverified_context()       # == helpers.common.ssl_helper.get_unverified_context()
    si = SmartConnect(host=cfg["host"], user=cfg["user"], pwd=cfg["password"],
                      sslContext=ctx)
    try:
        about = si.RetrieveContent().about
        print(f"  [SOAP] {about.fullName} — pyVmomi SmartConnect OK (api {about.apiVersion})")
    finally:
        Disconnect(si)


def login_vcenter_vapi():
    client = auth.vsphere_automation_client()
    print(f"  [vAPI] create_vsphere_client OK — {len(client.vcenter.VM.list())} VM(s) visible")


def login_vcf_automation():
    cfg = config.load("vcf_automation")
    vra = auth.vcf_automation_rest(cfg)           # OAuth refresh-token exchange
    orgs = vra.get("/cloudapi/1.0.0/orgs",
                   headers={"Accept": "application/json;version=9.1.0"}).json().get("values", [])
    scope = f"tenant '{cfg['org']}'" if cfg.get("org") else "provider"
    print(f"  [VCFA] OAuth login OK ({scope}) — {len(orgs)} org(s); API token reused (90-day)")


def main():
    print("VCF 9.1 unified login example\n" + "-" * 32)
    for name, fn in [("vCenter REST", login_vcenter_rest),
                     ("vCenter SOAP", login_vcenter_soap),
                     ("vCenter vAPI", login_vcenter_vapi),
                     ("VCF Automation", login_vcf_automation)]:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            print(f"  [{name}] skipped — {type(exc).__name__}: {str(exc)[:90]}")


if __name__ == "__main__":
    main()

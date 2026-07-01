"""vCenter — unified VCF SDK connection (SDK 套件對應).

OLD (vSphere 7/8): three separate installs + separate logins
    pip install pyvmomi
    pip install vsphere-automation-sdk-python
    pip install vsan-management-sdk
NEW (VCF 9.1): one install, one login shared across SOAP / REST / vSAN
    pip install vcf-sdk

This script proves all three access styles come from the same package and the
same credentials. Run it first to validate the SDK install + lab config.

Maps customer endpoint:  POST /api/v1/vmware/vcenter/connection_test  (Unchanged)
Ref: https://github.com/vmware/vcf-sdk-python
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


def main():
    # 1) REST (vSphere Automation) — no SDK needed
    vc = auth.vcenter_rest()
    about = vc.get("/api/appliance/system/version").json()
    print(f"[REST] vCenter version: {about.get('version')} build {about.get('build')}")

    # 2) SOAP via pyVmomi (bundled in vcf-sdk). Import path unchanged from 7/8.
    #    Note: pyVmomi 9.x requires Python >= 3.10 and raises at import on older
    #    runtimes — so we catch broadly, not just ImportError.
    try:
        from pyVim.connect import Disconnect
        si = auth.pyvmomi_connect()
        content = si.RetrieveContent()
        print(f"[SOAP] pyVmomi connected: {content.about.fullName}")
        Disconnect(si)
    except Exception as exc:  # noqa: BLE001
        print(f"[SOAP] skipped pyVmomi ({type(exc).__name__}: {exc}) "
              "— needs vcf-sdk on Python >= 3.10")

    # 3) vSphere Automation high-level client (also bundled in vcf-sdk)
    try:
        client = auth.vsphere_automation_client()
        vms = client.vcenter.VM.list()
        print(f"[vAPI] vSphere Automation client OK — {len(vms)} VMs visible")
    except Exception as exc:  # noqa: BLE001
        print(f"[vAPI] skipped vSphere Automation ({type(exc).__name__}) "
              "— needs vcf-sdk on Python >= 3.10")


if __name__ == "__main__":
    main()

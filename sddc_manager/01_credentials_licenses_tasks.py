"""SDDC Manager / SDDC Lifecycle (was vRealize Lifecycle Manager / vRLCM).

升級改寫對照表 — the vRLCM "Locker" (passwords / certs / licenses) and
environment/request model moved into SDDC Manager + SDDC Lifecycle APIs:

    /lcm/lcops/api/v1/locker/passwords   -> GET/PATCH /v1/credentials
    /lcm/lcops/api/v1/locker/licenses    -> GET/POST  /v1/license-keys
    /lcm/lcops/api/v2/environments       -> GET       /sddc-lcm/v1/components
    /lcm/request/api/v2/requests/{id}    -> GET       /sddc-lcm/v1/tasks/{id}
    /lcm/lcops/api/v2/health             -> GET       /sddc-lcm/v1/health

This whole bucket is REST-only (no SDK), so it integrates cleanly with CI/CD
secret management.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import auth  # noqa: E402


def list_credentials(sddc):
    return sddc.get("/v1/credentials").json().get("elements", [])


def list_license_keys(sddc):
    return sddc.get("/v1/license-keys").json().get("elements", [])


def list_domains(sddc):
    return sddc.get("/v1/domains").json().get("elements", [])


def lifecycle_health(sddc):
    # SDDC Lifecycle health (was /lcm/lcops/api/v2/health). May 404 on minimal
    # deployments — treat as optional.
    try:
        return sddc.get("/sddc-lcm/v1/health").json()
    except Exception as exc:  # noqa: BLE001
        return {"unavailable": str(exc)}


def main():
    sddc = auth.sddc_manager_rest()
    print("Authenticated to SDDC Manager (Bearer token from POST /v1/tokens).")

    domains = list_domains(sddc)
    print(f"\nWorkload domains ({len(domains)}):")
    for d in domains:
        print(f"  - {d['name']:24} type={d['type']:12} status={d.get('status','')}")

    creds = list_credentials(sddc)
    print(f"\nManaged credentials ({len(creds)}):  (Password Locker successor)")
    for c in creds[:12]:
        res = c.get("resource", {})
        print(f"  - {res.get('resourceType',''):16} {res.get('resourceName',''):28} "
              f"{c.get('username','')} ({c.get('credentialType','')})")

    keys = list_license_keys(sddc)
    print(f"\nLicense keys ({len(keys)}):  (License Locker successor)")
    for k in keys:
        print(f"  - {k.get('productType',''):16} {k.get('key','')}  {k.get('description','')}")

    print(f"\nSDDC Lifecycle health: {lifecycle_health(sddc)}")


if __name__ == "__main__":
    main()

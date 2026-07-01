"""Migration — vRealize Lifecycle Manager (vRLCM)  ->  SDDC Manager.

OLD (product removed in VCF 9.1; /lcm/ no longer serves):
    GET/PUT /lcm/lcops/api/v1/locker/passwords      # Password Locker
    GET/PUT /lcm/lcops/api/v1/locker/certificates   # Cert Locker
    GET/PUT /lcm/lcops/api/v1/locker/licenses        # License Locker
    GET     /lcm/lcops/api/v2/environments           # environments

NEW — SDDC Manager (REST or SDK):
    GET/PATCH /v1/credentials        (Password Locker -> Credentials)
    GET/POST  /v1/license-keys       (License Locker -> License Keys)
    GET       /v1/domains            (environments -> workload domains)
    SDDC Lifecycle: /sddc-lcm/v1/components, /sddc-lcm/v1/tasks/{id}

REST shown here; SDK equivalent is sddc_manager/02_credentials_licenses_sdk.py
(vmware.sddc_manager_client -> client.v1.Credentials / client.v1.Domains).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import auth  # noqa: E402


def main():
    sddc = auth.sddc_manager_rest()       # Bearer via POST /v1/tokens
    print("Logged in to SDDC Manager (replaces vRLCM).")

    creds = sddc.get("/v1/credentials").json().get("elements", [])
    print(f"\nCredentials (was Password/Cert Locker): {len(creds)}")
    for c in creds[:8]:
        res = c.get("resource", {})
        print(f"  - {res.get('resourceType',''):14} {res.get('resourceName',''):26} "
              f"{c.get('username','')} ({c.get('credentialType','')})")

    keys = sddc.get("/v1/license-keys").json().get("elements", [])
    print(f"\nLicense keys (was License Locker): {len(keys)}")

    domains = sddc.get("/v1/domains").json().get("elements", [])
    print(f"Workload domains (was environments): {len(domains)}")
    for d in domains:
        print(f"  - {d['name']} ({d['type']})")


if __name__ == "__main__":
    main()

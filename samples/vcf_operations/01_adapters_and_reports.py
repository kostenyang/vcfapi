"""VCF Operations (was vRealize Operations / vROps) — adapters, resources, reports.

升級改寫對照表 expected the base path to move /suite-api/api/ -> /api/. VERIFIED
against VCF Operations 9.1 (home.lab) this did NOT happen — the Suite API is
still served at /suite-api/api/, and BOTH the "OpsToken" and legacy
"vRealizeOpsToken" auth headers are accepted. So for this build the existing
vROps automation needs almost no change (auth + schema identical). Real lab
beats the doc — re-confirm the base path per release before assuming /api/.

Endpoints used (verified, /suite-api/api base baked into the client):
    POST /suite-api/api/auth/token/acquire   (handled in common.auth)
    GET  /suite-api/api/adapters
    GET  /suite-api/api/resources?resourceKind=...
    POST /suite-api/api/reports               (generate)
    GET  /suite-api/api/reports/{id}           (status)
    GET  /suite-api/api/reports/{id}/download
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


# Paths are relative to the Suite API base (/suite-api/api) baked into the client.
def list_adapters(ops):
    data = ops.get("/adapters").json()
    return data.get("adapterInstancesInfoDto", data.get("adapter", []))


def list_resources(ops, resource_kind="vSphere World"):
    return ops.get("/resources",
                   params={"resourceKind": resource_kind}).json().get("resourceList", [])


def main():
    ops = auth.vcf_operations_rest()
    print("Authenticated to VCF Operations (OpsToken).")

    adapters = list_adapters(ops)
    print(f"\nAdapter instances ({len(adapters)}):")
    for a in adapters[:15]:
        res = a.get("resourceKey", {})
        print(f"  - {res.get('name','?'):30} {res.get('adapterKindKey','')}")

    worlds = list_resources(ops, "vSphere World")
    print(f"\nvSphere World resources ({len(worlds)}):")
    for r in worlds[:5]:
        print(f"  - {r['resourceKey']['name']:30} {r['identifier']}")


if __name__ == "__main__":
    main()

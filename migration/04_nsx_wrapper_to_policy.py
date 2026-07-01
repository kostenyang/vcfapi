"""Migration — NSX-T internal IaaS wrapper  ->  NSX 9 Policy API.

OLD (customer-built internal wrapper, NOT an official NSX endpoint — not
guaranteed to exist in VCF 9.1):
    GET/POST /api/v1/vmware/nsx-t/dfw/groups
    GET/POST /api/v1/vmware/nsx-t/dfw/services
    GET/POST /api/v1/vmware/nsx-t/dfw/rules

NEW — call the NSX Policy API directly (official long-term path, plain HTTP,
no SDK version binding):
    GET /policy/api/v1/infra/domains/default/groups
    PUT /policy/api/v1/infra/domains/default/groups/{id}        (declarative)
    GET /policy/api/v1/infra/services
    GET /policy/api/v1/infra/domains/default/security-policies

REST shown here; SDK equivalent is nsx/02_dfw_policy_sdk.py
(vcf.nsx.policy -> client.infra.domains.Groups.policy_list_group_for_domain).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import auth  # noqa: E402

DOMAIN = "default"


def main():
    nsx = auth.nsx_rest()                 # basic auth to NSX Policy API
    print("Connected to NSX Policy API (replaces the internal NSX-T wrapper).")

    groups = nsx.get(f"/policy/api/v1/infra/domains/{DOMAIN}/groups").json().get("results", [])
    print(f"\nDFW groups (was /api/v1/vmware/nsx-t/dfw/groups): {len(groups)}")
    for g in groups[:10]:
        print(f"  - {g.get('display_name','?'):30} {g.get('path','')}")

    services = nsx.get("/policy/api/v1/infra/services").json().get("results", [])
    print(f"\nServices (was /api/v1/vmware/nsx-t/dfw/services): {len(services)}")


if __name__ == "__main__":
    main()

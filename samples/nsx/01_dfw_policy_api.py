"""NSX 9 — Distributed Firewall via the Policy API (was NSX-T).

遷移策略比較 → NSX DFW (90 項): "建議改用 REST API". The Policy API
(/policy/api/v1/infra/) is NSX's official long-term path and is plain HTTP, so
it removes the SDK version-binding problem. The customer's internal NSX-T DFW
wrapper (/api/v1/vmware/nsx-t/, 9 項) is "不可行 / 升級風險最高" — re-point it
straight at the Policy API as shown here.

Declarative model — PUT/PATCH the intent; NSX realises it. Endpoints used:
    GET /policy/api/v1/infra/domains/default/groups
    PUT /policy/api/v1/infra/domains/default/groups/{id}
    GET /policy/api/v1/infra/services
    GET /policy/api/v1/infra/domains/default/security-policies
    PUT /policy/api/v1/infra/domains/default/security-policies/{id}
Ref: https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402

DOMAIN = "default"


def list_groups(nsx):
    return nsx.get(f"/policy/api/v1/infra/domains/{DOMAIN}/groups").json().get("results", [])


def upsert_group(nsx, group_id, display_name, ip_addresses):
    """Create/update an IP-set group (declarative PUT — idempotent)."""
    body = {
        "display_name": display_name,
        "expression": [{
            "resource_type": "IPAddressExpression",
            "ip_addresses": ip_addresses,
        }],
    }
    return nsx.put(f"/policy/api/v1/infra/domains/{DOMAIN}/groups/{group_id}",
                   json=body).json()


def upsert_security_policy(nsx, policy_id, display_name, rules):
    body = {"display_name": display_name, "category": "Application", "rules": rules}
    return nsx.put(
        f"/policy/api/v1/infra/domains/{DOMAIN}/security-policies/{policy_id}",
        json=body).json()


def main():
    nsx = auth.nsx_rest()
    print("Connected to NSX Policy API.")

    groups = list_groups(nsx)
    print(f"\nExisting DFW groups ({len(groups)}):")
    for g in groups[:15]:
        print(f"  - {g.get('display_name','?'):30} {g.get('path','')}")

    if "--create-sample" in sys.argv:
        grp = upsert_group(nsx, "demo-app-web", "Demo App Web Tier",
                           ["192.168.114.50", "192.168.114.51"])
        print(f"\nupserted group: {grp['path']}")
        rule = {
            "display_name": "allow-web-in",
            "source_groups": ["ANY"],
            "destination_groups": [grp["path"]],
            "services": ["/infra/services/HTTPS"],
            "action": "ALLOW",
            "sequence_number": 10,
        }
        pol = upsert_security_policy(nsx, "demo-web-policy",
                                     "Demo Web Policy", [rule])
        print(f"upserted security policy: {pol['path']}")


if __name__ == "__main__":
    main()

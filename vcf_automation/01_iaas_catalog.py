"""VCF Automation (was vRA 8 / Aria Automation) — provider + tenant REST.

VERIFIED on VCFA 9.1 (home.lab). The big 8->9 changes (all real work items):

  1. Token endpoint changed. vRA8 used POST /iaas/api/login {refreshToken}; that
     returns invalid_grant on VCFA 9. VCFA 9 uses the OAuth endpoints:
        provider: POST /oauth/provider/token
        tenant:   POST /oauth/tenant/<org>/token
     body (form): grant_type=refresh_token&refresh_token=<api-token>
     -> { access_token (1h Bearer), refresh_token, token_type }
     (handled in common.auth.vcf_automation_rest; set vcf_automation.org for tenant)

  2. Multi-tenant, VCD-style. A *provider* (System) token reaches the provider
     /cloudapi/ APIs; the IaaS automation API (/iaas/api/) lives in a TENANT org
     and needs a tenant-scoped token (generate the API token inside that org).

  3. /cloudapi/ needs a VERSIONED Accept header: application/json;version=9.1.0
     (supported versions are returned in the 406 body if you omit it).

  4. Not part of the unified vcf-sdk (no automation samples there) — REST only.

This sample: authenticate (provider by default), list orgs via /cloudapi, and —
if vcf_automation.org is set (tenant token) — list the IaaS cloud accounts /
projects / catalog items.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import auth, config  # noqa: E402

CLOUDAPI = {"Accept": "application/json;version=9.1.0"}


def main():
    cfg = config.load("vcf_automation")
    vra = auth.vcf_automation_rest(cfg)
    scope = f"tenant '{cfg['org']}'" if cfg.get("org") else "provider (System)"
    print(f"Authenticated to VCF Automation 9 — {scope} token.")

    # Provider context (works with a provider/System token): orgs, roles, users.
    # All provider APIs live under /cloudapi and need the versioned Accept header.
    orgs = vra.get("/cloudapi/1.0.0/orgs", headers=CLOUDAPI).json().get("values", [])
    print(f"\nOrgs ({len(orgs)}):")
    for o in orgs:
        print(f"  - {o['name']:18} {o.get('displayName',''):24} "
              f"{'(provider)' if o['name'] == 'System' else '(tenant)'}")

    roles = vra.get("/cloudapi/1.0.0/roles", headers=CLOUDAPI).json().get("values", [])
    print(f"\nRoles ({len(roles)}):")
    for r in roles[:10]:
        print(f"  - {r.get('name','?')}")

    users = vra.get("/cloudapi/1.0.0/users", headers=CLOUDAPI).json().get("values", [])
    print(f"\nUsers ({len(users)}):")
    for u in users:
        print(f"  - {u.get('username','?'):18} {u.get('roleEntityRefs',[{}])[0].get('name','') if u.get('roleEntityRefs') else ''}")

    # Tenant context: IaaS API — needs a tenant-scoped token (vcf_automation.org)
    if not cfg.get("org"):
        tenants = [o["name"] for o in orgs if o["name"] != "System"]
        print(f"\n/iaas/api/ needs a TENANT token. Set vcf_automation.org to one of "
              f"{tenants} with an API token generated INSIDE that org "
              f"(a provider/System token cannot reach tenant IaaS — returns 500).")
        return

    accounts = vra.get("/iaas/api/cloud-accounts").json().get("content", [])
    print(f"\nCloud accounts ({len(accounts)}):")
    for a in accounts:
        print(f"  - {a.get('name','?'):28} {a.get('cloudAccountType','')}")
    projects = vra.get("/iaas/api/projects").json().get("content", [])
    print(f"\nProjects ({len(projects)}):")
    for p in projects:
        print(f"  - {p.get('name','?')}")
    items = vra.get("/catalog/api/items").json().get("content", [])
    print(f"\nCatalog items ({len(items)}):")
    for it in items[:15]:
        print(f"  - {it.get('name','?')}")


if __name__ == "__main__":
    main()

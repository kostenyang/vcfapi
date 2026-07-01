"""Migration — vRA 7 / vRA 8  ->  VCF Automation 9.

OLD (removed / changed in VCF 9.1):
    vRA 7:  /catalog-service/api/consumer/...   # API Sunset — GONE
            /identity/api/...                    # API Sunset — GONE
    vRA 8:  POST /csp/gateway/am/api/login       # GONE (backend 404)
            POST /iaas/api/login {refreshToken}  # 400 invalid_grant on 9.1

NEW — VCF Automation 9 (VCD-style multi-tenant, REST only; not in vcf-sdk):
    Login = OAuth refresh-token exchange:
        provider: POST /oauth/provider/token
        tenant:   POST /oauth/tenant/<org>/token
        body (form): grant_type=refresh_token&refresh_token=<api-token>
    Provider APIs:  /cloudapi/1.0.0/  (orgs, roles, users)  [Accept: ...;version=9.1.0]
    Tenant  APIs:   /iaas/api/, /catalog/api/   (needs a tenant-org token)
    UI: /provider/  and  /tenant/<org>/

Connect by FQDN (host-based ingress). Generate the API token in the VCFA UI.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import auth, config  # noqa: E402

CLOUDAPI = {"Accept": "application/json;version=9.1.0"}


def main():
    cfg = config.load("vcf_automation")
    vra = auth.vcf_automation_rest(cfg)   # OAuth /oauth/provider|tenant/token
    scope = f"tenant '{cfg['org']}'" if cfg.get("org") else "provider"
    print(f"Logged in to VCF Automation ({scope}) — replaces vRA7/vRA8 login.")

    orgs = vra.get("/cloudapi/1.0.0/orgs", headers=CLOUDAPI).json().get("values", [])
    print(f"\nOrgs (was vRA identity API): {len(orgs)}")
    for o in orgs:
        print(f"  - {o['name']:18} {o.get('displayName','')}")

    if cfg.get("org"):
        items = vra.get("/catalog/api/items").json().get("content", [])
        print(f"\nCatalog items (was vRA catalog-service): {len(items)}")
    else:
        print("\nFor /iaas/api & /catalog/api set vcf_automation.org + a tenant-org token.")


if __name__ == "__main__":
    main()

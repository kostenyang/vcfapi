"""vRA 8 SOURCE baseline — read the OLD estate before migrating to VCFA 9.

Run this against the environment you are migrating FROM (Aria Automation 8 /
vRA 8). It logs in the classic vRA8 way (username/password -> cspAuthToken
bearer) and inventories the objects that have to be re-created / re-mapped in
VCF Automation 9: projects, cloud accounts, zones, profiles, IaaS machines,
deployments, catalog items and blueprints.

Why it matters for the migration:
  * The login used here (POST /csp/gateway/am/api/login) is REMOVED in VCFA 9.
    In 9 you exchange an API token at /oauth/provider|tenant/<org>/token — see
    samples/vcf_automation/01_iaas_catalog.py and common.auth.vcf_automation_rest.
  * /iaas/api/* and /deployment/api/* still exist in 9 but move under the
    multi-tenant /cloudapi/1.0.0/* surface; blueprints become VCF Automation
    templates. Use the counts printed here as the "before" side of the diff.

    python samples/vcf_automation/00_vra8_source_baseline_rest.py

Endpoints + credentials come from config/lab.yaml (vra8 block).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


# (old vRA8 endpoint, label, new-in-VCFA-9 equivalent) — the migration mapping.
READS = [
    ("/iaas/api/projects",         "Projects",        "→ /cloudapi/1.0.0/orgs + IaaS projects (tenant-scoped)"),
    ("/iaas/api/cloud-accounts",   "Cloud accounts",  "→ /iaas/api/cloud-accounts (unchanged path; tenant token)"),
    ("/iaas/api/zones",            "Cloud zones",     "→ /iaas/api/zones"),
    ("/iaas/api/flavor-profiles",  "Flavor profiles", "→ /iaas/api/flavor-profiles"),
    ("/iaas/api/image-profiles",   "Image profiles",  "→ /iaas/api/image-profiles"),
    ("/iaas/api/network-profiles", "Network profiles","→ /iaas/api/network-profiles"),
    ("/iaas/api/fabric-networks",  "Fabric networks", "→ /iaas/api/fabric-networks"),
    ("/iaas/api/machines",         "IaaS machines",   "→ /iaas/api/machines"),
    ("/deployment/api/deployments","Deployments",     "→ /deployment/api/deployments (under /cloudapi tenant)"),
    ("/catalog/api/items",         "Catalog items",   "→ /catalog/api/items"),
    ("/catalog/api/types",         "Catalog types",   "→ /catalog/api/types"),
    ("/blueprint/api/blueprints",  "Blueprints",      "→ VCF Automation templates (Cloud Templates)"),
]


def _count(d):
    if isinstance(d, dict):
        return d.get("totalElements",
                     d.get("numberOfElements",
                            len(d.get("content", d.get("values", [])))))
    if isinstance(d, list):
        return len(d)
    return "?"


def main():
    print("vRA 8 SOURCE baseline (the environment being migrated FROM)")
    print("-" * 70)
    vra = auth.vra8_rest()          # POST /csp/gateway/am/api/login -> cspAuthToken

    about = vra.get("/iaas/api/about").json()
    print(f"  IaaS API version: {about.get('latestApiVersion')}  "
          f"(supported: {[a['apiVersion'] for a in about.get('supportedApis', [])]})")
    print("-" * 70)

    for path, label, newpath in READS:
        try:
            n = _count(vra.get(path).json())
            print(f"  {label:16s} {str(n):>4}   {path}")
            print(f"  {'':16s}      VCFA 9: {newpath}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {label:16s}  ERR  {path} — {type(exc).__name__}: {str(exc)[:50]}")

    print("-" * 70)
    print("These counts are the 'before' side. Re-run the VCFA 9 samples after "
          "cut-over and compare.")


if __name__ == "__main__":
    main()

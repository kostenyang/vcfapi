"""NSX 9 — Distributed Firewall via the VCF SDK (Policy API).

SDK counterpart of 01_dfw_policy_api.py (REST). Same NSX Policy API, but through
the typed SDK client (vcf.nsx.policy). Note: the migration strategy still rates
NSX as "REST-preferred" (Policy API is plain HTTP, no SDK version-binding), so
for NSX the REST sample is usually the better choice — this SDK version is here
for completeness / comparison.

    client.infra.domains.Groups.policy_list_group_for_domain("default")
    client.infra.domains.Groups.policy_read_group_for_domain(domain, group_id)
    client.infra.Services.list_0() / ...

Needs vcf-sdk on Python >= 3.10.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import auth  # noqa: E402

DOMAIN = "default"


def main():
    client = auth.nsx_policy_client()
    print("NSX Policy API via VCF SDK (vcf.nsx.policy).")

    result = client.infra.domains.Groups.policy_list_group_for_domain(DOMAIN)
    groups = result.results
    print(f"\nDFW groups ({len(groups)}):")
    for g in groups[:15]:
        print(f"  - {g.display_name:30} {g.path}")
    if len(groups) > 15:
        print(f"  ... and {len(groups) - 15} more")


if __name__ == "__main__":
    main()

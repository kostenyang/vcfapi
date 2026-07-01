"""Connectivity smoke test — authenticate to every VCF 9.1 component and report.

Run this first against the homelab to confirm config/lab.yaml + reachability
before running the per-component samples.

    python smoke_test.py            # test everything in config/lab.yaml
    python smoke_test.py vcenter    # test one component

Components: vcenter sddc_manager nsx vcf_operations log_management vcf_automation
Exit code is non-zero if any selected component fails.
"""
import sys

from common import auth

CHECKS = {
    "vcenter": lambda: auth.vcenter_rest().get(
        "/api/appliance/system/version").json().get("version"),
    "sddc_manager": lambda: f"{len(auth.sddc_manager_rest().get('/v1/domains').json().get('elements', []))} domain(s)",
    "nsx": lambda: f"{len(auth.nsx_rest().get('/policy/api/v1/infra/domains/default/groups').json().get('results', []))} DFW group(s)",
    "vcf_operations": lambda: f"{len(auth.vcf_operations_rest().get('/adapters').json().get('adapterInstancesInfoDto', []))} adapter(s)",
    "log_management": lambda: "ops-li JWT acquired" if auth.log_management_rest() else "no token",
    "vcf_automation": lambda: f"{len(auth.vcf_automation_rest().get('/cloudapi/1.0.0/orgs', headers={'Accept': 'application/json;version=9.1.0'}).json().get('values', []))} org(s)",
}


def main():
    selected = sys.argv[1:] or list(CHECKS)
    failures = 0
    for name in selected:
        if name not in CHECKS:
            print(f"  ?  {name}: unknown component")
            continue
        try:
            result = CHECKS[name]()
            print(f"  OK {name}: {result}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  XX {name}: {type(exc).__name__}: {exc}")
    print(f"\n{len(selected) - failures}/{len(selected)} components OK")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

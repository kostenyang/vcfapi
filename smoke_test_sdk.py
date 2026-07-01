"""Connectivity smoke test for the SDK clients (vcf-sdk, Python >= 3.10).

SDK counterpart of smoke_test.py. Run with a vcf-sdk environment:
    pip install vcf-sdk        # needs Python 3.10+
    python smoke_test_sdk.py [component ...]

Components: vcenter sddc_manager nsx vcf_operations
(VCF Automation is not part of vcf-sdk; Log Management uses the Operations API.)

8->9 NOTE: the vSphere SDK client (create_vsphere_client) authenticates via the
SAML **STS** flow, which is stricter than REST's basic-auth /api/session — under
heavy/rapid login load the SSO account can get throttled/locked on the STS path
while REST still works. If 'vcenter' here shows Unauthenticated/STS challenge but
REST smoke_test passes, wait out the SSO lockout (default ~15 min) and retry.
"""
import sys

from common import auth

CHECKS = {
    "vcenter": lambda: f"{len(auth.vsphere_automation_client().vcenter.VM.list())} VM(s)",
    "sddc_manager": lambda: f"{len(auth.sddc_manager_client().v1.Domains.get_domains().elements)} domain(s)",
    "nsx": lambda: f"{len(auth.nsx_policy_client().infra.domains.Groups.policy_list_group_for_domain('default').results)} DFW group(s)",
    "vcf_operations": lambda: f"{len(auth.vcf_operations_client().api.Adapters.enumerate_adapter_instances().adapter_instances_info_dto)} adapter(s)",
}


def main():
    selected = sys.argv[1:] or list(CHECKS)
    failures = 0
    for name in selected:
        if name not in CHECKS:
            print(f"  ?  {name}: unknown component")
            continue
        try:
            print(f"  OK {name}: {CHECKS[name]()}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  XX {name}: {type(exc).__name__}: {exc}")
    print(f"\n{len(selected) - failures}/{len(selected)} SDK clients OK")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

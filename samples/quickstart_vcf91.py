"""Quickstart — the vendor-supported path (Python 3.12+ + vcf-sdk).

This is the recommended starting point for VCF 9.1 automation: one file that
logs into every component the officially-supported way and reads one thing from
each, using the unified `vcf-sdk` SDK clients (plus VCF Automation's OAuth, which
is not part of vcf-sdk).

Vendor line: use Python 3.11 / 3.12 (SDK supports 3.10–3.14) + `pip install
vcf-sdk`. Python 3.8 is EOL / unsupported — do not target it for new work.

    python3.12 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt          # includes vcf-sdk
    python samples/quickstart_vcf91.py

Endpoints + credentials come from config/lab.yaml.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import auth, config  # noqa: E402


def main():
    print("VCF 9.1 quickstart — vendor-supported path (Python 3.12+ / vcf-sdk)")
    print("-" * 62)

    # vCenter — unified SDK: one client, typed objects
    try:
        vc = auth.vsphere_automation_client()          # create_vsphere_client
        print(f"  [vCenter]   vAPI SDK OK — {len(vc.vcenter.VM.list())} VM(s)")
    except Exception as exc:  # noqa: BLE001
        print(f"  [vCenter]   skipped — {type(exc).__name__}: {str(exc)[:70]}")

    # SDDC Manager — vmware.sddc_manager_client
    try:
        sm = auth.sddc_manager_client()
        print(f"  [SDDC Mgr]  SDK OK — {len(sm.v1.Domains.get_domains().elements)} domain(s)")
    except Exception as exc:  # noqa: BLE001
        print(f"  [SDDC Mgr]  skipped — {type(exc).__name__}: {str(exc)[:70]}")

    # NSX — vcf.nsx.policy
    try:
        nx = auth.nsx_policy_client()
        n = len(nx.infra.domains.Groups.policy_list_group_for_domain("default").results)
        print(f"  [NSX]       Policy SDK OK — {n} DFW group(s)")
    except Exception as exc:  # noqa: BLE001
        print(f"  [NSX]       skipped — {type(exc).__name__}: {str(exc)[:70]}")

    # VCF Operations — vcf.operations
    try:
        op = auth.vcf_operations_client()
        n = len(op.api.Adapters.enumerate_adapter_instances().adapter_instances_info_dto)
        print(f"  [Ops]       SDK OK — {n} adapter(s)")
    except Exception as exc:  # noqa: BLE001
        print(f"  [Ops]       skipped — {type(exc).__name__}: {str(exc)[:70]}")

    # VCF Automation — OAuth (not in vcf-sdk; standalone REST API)
    try:
        cfg = config.load("vcf_automation")
        if cfg.get("api_token") and cfg["api_token"] != "PASTE_VCFA_API_TOKEN_HERE":
            vra = auth.vcf_automation_rest(cfg)
            orgs = vra.get("/cloudapi/1.0.0/orgs",
                           headers={"Accept": "application/json;version=9.1.0"}).json().get("values", [])
            print(f"  [VCFA]      OAuth OK — {len(orgs)} org(s) (REST; not in vcf-sdk)")
        else:
            print("  [VCFA]      set vcf_automation.api_token to enable")
    except Exception as exc:  # noqa: BLE001
        print(f"  [VCFA]      skipped — {type(exc).__name__}: {str(exc)[:70]}")

    print("-" * 62)
    print("Next: see samples/<component>/ for REST + SDK examples per operation.")


if __name__ == "__main__":
    main()

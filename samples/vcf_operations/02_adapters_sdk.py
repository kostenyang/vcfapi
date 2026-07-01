"""VCF Operations (vROps) — adapters / resources via the VCF SDK.

SDK counterpart of 01_adapters_and_reports.py (REST). The official samples use
this SDK client (vcf.operations); services live under client.api.* — Adapters,
Resources, Reports, Alerts, etc. Auth is the same OpsToken acquired against
/suite-api/api (handled in common.auth.vcf_operations_client).

Needs vcf-sdk on Python >= 3.10.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


def main():
    client = auth.vcf_operations_client()
    print("VCF Operations SDK client (vcf.operations, OpsToken).")

    # client.api.Adapters.enumerate_adapter_instances() -> typed result
    result = client.api.Adapters.enumerate_adapter_instances()
    items = result.adapter_instances_info_dto
    print(f"\nAdapter instances ({len(items)}):")
    for a in items[:15]:
        rk = a.resource_key
        print(f"  - {rk.name:30} {rk.adapter_kind_key}")


if __name__ == "__main__":
    main()

"""SDDC Manager — domains / credentials via the VCF SDK.

SDK counterpart of 01_credentials_licenses_tasks.py (REST). Uses the real
unified-SDK module `vmware.sddc_manager_client.StubFactory`; services hang off
client.v1.*  and return typed PageOf<...> objects with .elements.

    client.v1.Domains.get_domains().elements
    client.v1.Credentials.get_credentials().elements

Needs vcf-sdk on Python >= 3.10.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import auth  # noqa: E402


def main():
    client = auth.sddc_manager_client()
    print("SDDC Manager SDK client (vmware.sddc_manager_client).")

    domains = client.v1.Domains.get_domains().elements
    print(f"\nWorkload domains ({len(domains)}):")
    for d in domains:
        print(f"  - {d.name:24} type={d.type:12} status={getattr(d, 'status', '')}")

    creds = client.v1.Credentials.get_credentials().elements
    print(f"\nManaged credentials ({len(creds)}):")
    for c in creds[:12]:
        res = c.resource
        print(f"  - {res.resource_type:16} {res.resource_name:28} "
              f"{c.username} ({c.credential_type})")


if __name__ == "__main__":
    main()

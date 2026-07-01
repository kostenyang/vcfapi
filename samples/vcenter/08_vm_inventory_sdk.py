"""vCenter — inventory via the VCF SDK (vSphere Automation client).

SDK counterpart of 02_vm_inventory_rest.py. Same result, idiomatic SDK:
the unified vcf-sdk provides create_vsphere_client; you get typed model
objects instead of raw JSON.

    client.vcenter.Cluster.list()
    client.vcenter.Host.list()
    client.vcenter.VM.list()

Needs vcf-sdk on Python >= 3.10.  Compare with 02_vm_inventory_rest.py to see
the REST vs SDK trade-off (the customer's 8->9 choice per operation).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


def main():
    client = auth.vsphere_automation_client()   # create_vsphere_client (vcf-sdk)

    clusters = client.vcenter.Cluster.list()
    print(f"Clusters ({len(clusters)}):")
    for c in clusters:
        print(f"  - {c.name:24} {c.cluster}")

    hosts = client.vcenter.Host.list()
    print(f"\nHosts ({len(hosts)}):")
    for h in hosts:
        print(f"  - {h.name:24} {h.connection_state}/{h.power_state}")

    vms = client.vcenter.VM.list()
    print(f"\nVMs ({len(vms)}):")
    for vm in vms[:25]:
        print(f"  - {vm.name:32} {str(vm.power_state):12} "
              f"cpu={vm.cpu_count} mem={vm.memory_size_mib}MiB  {vm.vm}")
    if len(vms) > 25:
        print(f"  ... and {len(vms) - 25} more")


if __name__ == "__main__":
    main()

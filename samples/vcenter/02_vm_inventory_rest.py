"""vCenter — inventory queries via vSphere REST API.

Replaces a cluster of customer "list" wrappers that used pyVmomi /
PropertyCollector. These are Unchanged endpoints — same operation, but the
recommended VCF 9.1 path is REST (≈60% less code, token auth, CI/CD-friendly).

Maps customer endpoints:
    GET /api/v1/vmware/vcenter/vm/list            -> GET /api/vcenter/vm
    GET /api/v1/vmware/vcenter/vm/list/name       -> GET /api/vcenter/vm (names)
    GET /api/v1/vmware/vcenter/host/list          -> GET /api/vcenter/host
    GET /api/v1/vmware/vcenter/cluster/list/name  -> GET /api/vcenter/cluster
Ref: https://developer.broadcom.com/xapis/vsphere-automation-api/latest/
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


def list_vms(vc):
    return vc.get("/api/vcenter/vm").json()


def list_hosts(vc):
    return vc.get("/api/vcenter/host").json()


def list_clusters(vc):
    return vc.get("/api/vcenter/cluster").json()


def main():
    vc = auth.vcenter_rest()

    clusters = list_clusters(vc)
    print(f"Clusters ({len(clusters)}):")
    for c in clusters:
        print(f"  - {c['name']:24} {c['cluster']}")

    hosts = list_hosts(vc)
    print(f"\nHosts ({len(hosts)}):")
    for h in hosts:
        print(f"  - {h['name']:24} {h['connection_state']}/{h['power_state']}")

    vms = list_vms(vc)
    print(f"\nVMs ({len(vms)}):")
    for vm in vms[:25]:
        print(f"  - {vm['name']:32} {vm['power_state']:12} "
              f"cpu={vm['cpu_count']} mem={vm['memory_size_MiB']}MiB  {vm['vm']}")
    if len(vms) > 25:
        print(f"  ... and {len(vms) - 25} more")


if __name__ == "__main__":
    main()

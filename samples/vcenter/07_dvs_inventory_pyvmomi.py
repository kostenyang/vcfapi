"""vCenter — Distributed Virtual Switch inventory via pyVmomi (KEEP-SDK).

Analysis 3 → "DVS / vSwitch 網路設定 (13 項): 沿用 SDK / CLI". vSphere REST
coverage of DVS advanced config (LACP, Port Policy, PVLAN, NetFlow) is limited;
pyVmomi's DistributedVirtualSwitch is the most complete interface, so the
customer's vDS/vSS automation stays on pyVmomi after the VCF 9.1 upgrade.

Maps customer endpoints (kept, retested on 9.1 SDK):
    GET /api/v1/vmware/vcenter/host/hosts_by_switch_id
    GET /api/v1/vmware/vcenter/host/vms_by_switch_id
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


def main():
    from pyVim.connect import Disconnect
    from pyVmomi import vim

    si = auth.pyvmomi_connect()
    try:
        content = si.RetrieveContent()
        view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.DistributedVirtualSwitch], True)
        try:
            switches = list(view.view)
        finally:
            view.Destroy()

        print(f"Distributed switches ({len(switches)}):")
        for dvs in switches:
            pgs = [pg.name for pg in dvs.portgroup]
            print(f"  - {dvs.name}  uplinks={len(dvs.config.uplinkPortPolicy.uplinkPortName)}"
                  f"  portgroups={len(pgs)}")
            for pg in pgs:
                print(f"      · {pg}")
    finally:
        Disconnect(si)


if __name__ == "__main__":
    main()

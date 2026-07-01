"""vCenter — VM power management via vSphere REST API.

Analysis 3 → "VM 電源管理 (19 項): 建議改用 REST API". The customer's
pyVmomi power ops (vim.VirtualMachine.PowerOn/Off/ShutdownGuest/Reboot) map
1:1 onto REST and lose the async-Task parsing.

    GET  /api/vcenter/vm/{vm}/power            -> current power state
    POST /api/vcenter/vm/{vm}/power?action=start
    POST /api/vcenter/vm/{vm}/power?action=stop        (hard)
    POST /api/vcenter/vm/{vm}/power?action=reset
    POST /api/vcenter/vm/{vm}/power?action=suspend
    POST /api/vcenter/vm/{vm}/guest/power?action=shutdown   (graceful, needs tools)
    POST /api/vcenter/vm/{vm}/guest/power?action=reboot

Usage:  python 03_vm_power_rest.py <vm-name> [start|stop|shutdown|reset|reboot|state]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


def find_vm(vc, name):
    vms = vc.get("/api/vcenter/vm", params={"names": name}).json()
    if not vms:
        raise SystemExit(f"VM '{name}' not found")
    return vms[0]["vm"]


def get_state(vc, vm_id):
    return vc.get(f"/api/vcenter/vm/{vm_id}/power").json()["state"]


def power(vc, vm_id, action):
    if action in ("shutdown", "reboot"):           # graceful — via guest/power
        vc.post(f"/api/vcenter/vm/{vm_id}/guest/power", params={"action": action})
    else:                                          # start | stop | reset | suspend
        vc.post(f"/api/vcenter/vm/{vm_id}/power", params={"action": action})


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    name = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "state"

    vc = auth.vcenter_rest()
    vm_id = find_vm(vc, name)

    if action == "state":
        print(f"{name} ({vm_id}): {get_state(vc, vm_id)}")
        return

    print(f"{name}: {get_state(vc, vm_id)} -> sending '{action}' ...")
    power(vc, vm_id, action)
    print(f"{name}: now {get_state(vc, vm_id)}")


if __name__ == "__main__":
    main()

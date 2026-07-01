"""vCenter — VM power via the VCF SDK (vSphere Automation client).

SDK counterpart of 03_vm_power_rest.py.

    client.vcenter.vm.Power.get(vm)     -> state
    client.vcenter.vm.Power.start(vm)
    client.vcenter.vm.Power.stop(vm)
    client.vcenter.vm.Power.suspend(vm)
    client.vcenter.vm.Power.reset(vm)
Graceful guest ops (need VMware Tools): client.vcenter.vm.guest.Power.shutdown/reboot(vm)

Usage:  python 09_vm_power_sdk.py <vm-name> [start|stop|reset|suspend|shutdown|reboot|state]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


def find_vm(client, name):
    from com.vmware.vcenter_client import VM
    vms = client.vcenter.VM.list(VM.FilterSpec(names={name}))
    if not vms:
        raise SystemExit(f"VM '{name}' not found")
    return vms[0].vm


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    name = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "state"

    client = auth.vsphere_automation_client()
    vm = find_vm(client, name)
    power = client.vcenter.vm.Power

    if action == "state":
        print(f"{name} ({vm}): {power.get(vm).state}")
        return

    print(f"{name}: {power.get(vm).state} -> '{action}' ...")
    if action in ("shutdown", "reboot"):
        getattr(client.vcenter.vm.guest.Power, action)(vm)
    else:
        getattr(power, action)(vm)              # start | stop | reset | suspend
    print(f"{name}: now {power.get(vm).state}")


if __name__ == "__main__":
    main()

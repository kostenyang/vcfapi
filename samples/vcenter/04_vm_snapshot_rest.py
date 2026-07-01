"""vCenter — VM snapshot CRUD.

8->9 FINDING (verified on vSphere 9.1, home.lab m02): the vSphere REST API does
NOT expose VM snapshots — GET/POST /api/vcenter/vm/{vm}/snapshots returns 404.
So the migration analysis' "VM Snapshot -> REST" does NOT hold on this build;
snapshot management stays on pyVmomi (SOAP) — which in VCF 9 ships INSIDE the
unified **VCF 9 SDK**, not as a standalone install:
    pip install vcf-sdk     # provides pyVmomi + vSphere Automation + vSAN bindings
Needs Python >= 3.10 (the 8->9 runtime bump; 3.8 is unsupported).

VERIFIED live on home.lab VCF 9.1 with vcf-sdk 9.1.0.0 on Python 3.12:
create -> list -> delete all succeeded.

    vim.VirtualMachine.CreateSnapshot_Task(name, description, memory, quiesce)
    vim.vm.Snapshot.RemoveSnapshot_Task(removeChildren)
    vim.vm.Snapshot.RevertToSnapshot_Task()

Usage:
    python 04_vm_snapshot_rest.py <vm-name> list
    python 04_vm_snapshot_rest.py <vm-name> create "pre-upgrade" "before VCF 9.1 test"
    python 04_vm_snapshot_rest.py <vm-name> delete "pre-upgrade"
    python 04_vm_snapshot_rest.py <vm-name> revert "pre-upgrade"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


def get_vm(content, name):
    from pyVmomi import vim
    view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True)
    try:
        return next((o for o in view.view if o.name == name), None)
    finally:
        view.Destroy()


def walk_snapshots(tree, depth=0):
    for node in tree:
        yield node, depth
        yield from walk_snapshots(node.childSnapshotList, depth + 1)


def find_snapshot(vm, name):
    if not vm.snapshot:
        return None
    for node, _ in walk_snapshots(vm.snapshot.rootSnapshotList):
        if node.name == name:
            return node.snapshot
    return None


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    name, op = sys.argv[1], sys.argv[2]

    from pyVim.connect import Disconnect
    from pyVim.task import WaitForTask

    si = auth.pyvmomi_connect()
    try:
        content = si.RetrieveContent()
        vm = get_vm(content, name)
        if vm is None:
            raise SystemExit(f"VM '{name}' not found")

        if op == "list":
            if not vm.snapshot:
                print("  (no snapshots)")
                return
            for node, depth in walk_snapshots(vm.snapshot.rootSnapshotList):
                print(f"  {'  ' * depth}- {node.name}: {node.description}")
        elif op == "create":
            desc = sys.argv[4] if len(sys.argv) > 4 else ""
            WaitForTask(vm.CreateSnapshot_Task(name=sys.argv[3], description=desc,
                                               memory=False, quiesce=False))
            print(f"created snapshot '{sys.argv[3]}'")
        elif op in ("delete", "revert"):
            snap = find_snapshot(vm, sys.argv[3])
            if snap is None:
                raise SystemExit(f"snapshot '{sys.argv[3]}' not found")
            if op == "delete":
                WaitForTask(snap.RemoveSnapshot_Task(removeChildren=False))
                print(f"deleted snapshot '{sys.argv[3]}'")
            else:
                WaitForTask(snap.RevertToSnapshot_Task())
                print(f"reverted to snapshot '{sys.argv[3]}'")
        else:
            raise SystemExit(__doc__)
    finally:
        Disconnect(si)


if __name__ == "__main__":
    main()

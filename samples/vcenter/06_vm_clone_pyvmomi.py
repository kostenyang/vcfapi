"""vCenter — VM clone via pyVmomi (HYBRID strategy).

Analysis 3 → "VM Clone / vMotion / Relocate (8 項): 混合策略". Basic clone has
a REST equivalent (POST /api/vcenter/vm?action=clone), but advanced
RelocateSpec / linked-clone / cross-vCenter vMotion are not fully covered by
REST, so pyVmomi is retained here. Import path is unchanged from vSphere 7/8 —
only the package source (vcf-sdk) and runtime (Python >= 3.10) change.

Maps customer endpoint:  POST /api/v1/vmware/vcenter/vm_clone  (Unchanged)

Usage:  python 06_vm_clone_pyvmomi.py <source-vm> <new-name>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


def get_obj(content, vimtype, name):
    view = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    try:
        return next((o for o in view.view if o.name == name), None)
    finally:
        view.Destroy()


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    src_name, new_name = sys.argv[1], sys.argv[2]

    from pyVim.connect import Disconnect
    from pyVim.task import WaitForTask
    from pyVmomi import vim

    si = auth.pyvmomi_connect()
    try:
        content = si.RetrieveContent()
        src = get_obj(content, [vim.VirtualMachine], src_name)
        if src is None:
            raise SystemExit(f"source VM '{src_name}' not found")

        # clone into the same host/datastore as the source (simplest sample)
        relocate = vim.vm.RelocateSpec(pool=src.resourcePool)
        clone_spec = vim.vm.CloneSpec(location=relocate, powerOn=False, template=False)

        print(f"cloning {src_name} -> {new_name} ...")
        task = src.Clone(folder=src.parent, name=new_name, spec=clone_spec)
        WaitForTask(task)
        print(f"done: {task.info.result}")
    finally:
        Disconnect(si)


if __name__ == "__main__":
    main()

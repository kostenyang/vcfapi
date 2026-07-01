"""vCenter — Tagging via the VCF SDK (vSphere Automation client).

SDK counterpart of 05_tagging_rest.py. Note how the SDK uses typed CreateSpec
objects instead of hand-built JSON (and there is no /rest/ vs /api/ wrapper
ambiguity — that is a REST-only concern).

    client.tagging.Category.create(Category.CreateSpec(...))
    client.tagging.Tag.create(Tag.CreateSpec(...))
    client.tagging.TagAssociation.attach(tag_id, DynamicID(...))
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import auth  # noqa: E402


def ensure_category(client, name):
    Category = __import__("com.vmware.cis.tagging_client", fromlist=["Category"]).Category
    for cid in client.tagging.Category.list():
        if client.tagging.Category.get(cid).name == name:
            return cid
    spec = Category.CreateSpec(name=name, description=f"{name} (sample)",
                              cardinality=Category.Cardinality.MULTIPLE,
                              associable_types=set())
    return client.tagging.Category.create(spec)


def ensure_tag(client, category_id, name):
    Tag = __import__("com.vmware.cis.tagging_client", fromlist=["Tag"]).Tag
    for tid in client.tagging.Tag.list_tags_for_category(category_id):
        if client.tagging.Tag.get(tid).name == name:
            return tid
    spec = Tag.CreateSpec(name=name, description=f"{name} (sample)",
                          category_id=category_id)
    return client.tagging.Tag.create(spec)


def main():
    from com.vmware.vapi.std_client import DynamicID
    from com.vmware.vcenter_client import VM

    client = auth.vsphere_automation_client()
    cat = ensure_category(client, "demo-env")
    tag = ensure_tag(client, cat, "vcf91-migrated")
    print(f"category=demo-env ({cat})  tag=vcf91-migrated ({tag})")

    if len(sys.argv) > 1:
        vms = client.vcenter.VM.list(VM.FilterSpec(names={sys.argv[1]}))
        if vms:
            client.tagging.TagAssociation.attach(
                tag, DynamicID(type="VirtualMachine", id=vms[0].vm))
            print(f"attached tag to {sys.argv[1]} ({vms[0].vm})")


if __name__ == "__main__":
    main()

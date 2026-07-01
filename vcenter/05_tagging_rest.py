"""vCenter — Tagging (Category / Tag / Association) via vSphere REST API.

Analysis 3 → "Tagging / Tag Association (10 項): 建議改用 REST API". The old
code used client.tagging.Tag/Category/TagAssociation.*; the vAPI REST path is
the official long-term route.

    GET/POST  /api/cis/tagging/category
    GET/POST  /api/cis/tagging/tag
    POST      /api/cis/tagging/tag-association/{tag}?action=attach   {object_id}
    POST      /api/cis/tagging/tag-association/{tag}?action=list-attached-objects
Ref: https://developer.broadcom.com/xapis/vsphere-automation-api/latest/cis/

8->9 NOTE (verified on vSphere 9.1): the new `/api/` JSON REST takes the spec
fields DIRECTLY in the body. The old `/rest/` API wrapped them as
{"create_spec": {...}} — that now fails with "unexpected field [create_spec]".
This sample uses the new (unwrapped) form.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import auth  # noqa: E402


def ensure_category(vc, name, cardinality="MULTIPLE", associable=()):
    for cid in vc.get("/api/cis/tagging/category").json():
        if vc.get(f"/api/cis/tagging/category/{cid}").json()["name"] == name:
            return cid
    # new /api/ form: spec fields directly, no {"create_spec": ...} wrapper
    body = {"name": name, "description": f"{name} (sample)",
            "cardinality": cardinality, "associable_types": list(associable)}
    return vc.post("/api/cis/tagging/category", json=body).json()


def ensure_tag(vc, category_id, name):
    existing = vc.post("/api/cis/tagging/tag",
                       params={"action": "list-tags-for-category"},
                       json={"category_id": category_id}).json()
    for tid in existing:
        if vc.get(f"/api/cis/tagging/tag/{tid}").json()["name"] == name:
            return tid
    body = {"name": name, "description": f"{name} (sample)",
            "category_id": category_id}
    return vc.post("/api/cis/tagging/tag", json=body).json()


def attach(vc, tag_id, vm_id):
    body = {"object_id": {"id": vm_id, "type": "VirtualMachine"}}
    vc.post(f"/api/cis/tagging/tag-association/{tag_id}",
            params={"action": "attach"}, json=body)


def main():
    vc = auth.vcenter_rest()
    cat = ensure_category(vc, "demo-env")
    tag = ensure_tag(vc, cat, "vcf91-migrated")
    print(f"category=demo-env ({cat})  tag=vcf91-migrated ({tag})")

    if len(sys.argv) > 1:                # optional: attach to a named VM
        vms = vc.get("/api/vcenter/vm", params={"names": sys.argv[1]}).json()
        if vms:
            attach(vc, tag, vms[0]["vm"])
            print(f"attached tag to {sys.argv[1]} ({vms[0]['vm']})")


if __name__ == "__main__":
    main()

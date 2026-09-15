"""把四個 client 串起來的日常巡檢腳本（示範用）。憑證全從環境變數來。"""
import os

from legacy_app import nsx_client, vra_client, vrops_client, vsphere_client


def run():
    vc = os.environ["VC_HOST"]
    sid = vsphere_client.login(vc, os.environ["VC_USER"], os.environ["VC_PASS"])
    print("VMs:", len(vsphere_client.list_vms(vc, sid)))

    ops = os.environ["OPS_HOST"]
    tok = vrops_client.acquire_token(ops, os.environ["OPS_USER"], os.environ["OPS_PASS"])
    print("resources:", len(vrops_client.get_resources(ops, tok)))

    nsx = os.environ["NSX_HOST"]
    print("segments:", len(nsx_client.list_segments(nsx, os.environ["NSX_USER"], os.environ["NSX_PASS"])))

    vra = os.environ["VRA_HOST"]
    t = vra_client.login(vra, os.environ["VRA_USER"], os.environ["VRA_PASS"])
    print("deployments:", len(vra_client.list_deployments(vra, t)))


if __name__ == "__main__":
    run()

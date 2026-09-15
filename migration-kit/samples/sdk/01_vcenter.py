"""vCenter / vSphere 9.1（base https://<vc>/api）— 列 cluster / host / VM，並讀版本。

    python sdk/01_vcenter.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import config                       # noqa: E402
from common.clients import vsphere_client       # noqa: E402

cfg, verify = config.get("vcenter")
client = vsphere_client(cfg["host"], cfg["user"], cfg["password"], verify)

print("GET /api/appliance/system/version →", client.appliance.system.Version.get().version)
for name, svc in (("cluster", client.vcenter.Cluster),
                  ("host", client.vcenter.Host),
                  ("VM", client.vcenter.VM)):
    items = svc.list()
    print("GET /api/vcenter/%-8s → %d 筆" % (name.lower(), len(items)))
    for i in items[:3]:
        print("   ", i)

"""SDDC Manager 9.1（base https://<sddcm>/）— domain / cluster / host / 版本。

    python sdk/02_sddc_manager.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import config                              # noqa: E402
from common.clients import sddc_manager_stub_config    # noqa: E402

from vmware.sddc_manager.v1_client import (Clusters, Domains, Hosts,  # noqa: E402
                                           SddcManagers)

cfg, verify = config.get("sddc_manager")
sc = sddc_manager_stub_config(cfg["host"], cfg["user"], cfg["password"], verify)

for label, svc, call in (("GET /v1/domains", Domains(sc), "get_domains"),
                         ("GET /v1/clusters", Clusters(sc), "get_clusters"),
                         ("GET /v1/hosts", Hosts(sc), "get_hosts"),
                         ("GET /v1/sddc-managers", SddcManagers(sc), "get_sddc_managers")):
    page = getattr(svc, call)()
    items = page.elements or []
    print("%-24s → %d 筆" % (label, len(items)))
    for e in items[:3]:
        print("   ", getattr(e, "name", None) or getattr(e, "fqdn", None) or getattr(e, "id", ""),
              getattr(e, "version", "") or getattr(e, "status", ""))

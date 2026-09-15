"""VCF Operations 9.1（base https://<ops>/suite-api）— 版本 / adapter kind / 資源。

vROps 的 /suite-api 介面在 VCF 9.1 沿用；認證改成 OpsToken。

    python sdk/05_vcf_operations.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import config                              # noqa: E402
from common.clients import vcf_operations_stub_config  # noqa: E402

from vcf.operations.api.versions_client import Current  # noqa: E402
from vcf.operations.api_client import (Adapterkinds,  # noqa: E402
                                       Resources)

cfg, verify = config.get("vcf_operations")
sc = vcf_operations_stub_config(cfg["host"], cfg["user"], cfg["password"], verify)

v = Current(sc).get_current_version_of_server()
print("GET /suite-api/api/versions/current →", v.release_name)
ak = Adapterkinds(sc).get_adapter_types()
print("GET /suite-api/api/adapterkinds  → %d 種 adapter" % len(ak.adapter_kind or []))
res = Resources(sc).get_resources(page_size=3)
print("GET /suite-api/api/resources     → 共 %s 個資源（取前 3 筆）" % res.page_info.total_count)
for r in (res.resource_list or [])[:3]:
    print("   ", r.resource_key.name, "/", r.resource_key.resource_kind_key)

"""NSX 9.1 Manager / MP（base https://<nsx>/api/v1）— transport zone / node / cluster。

保留這支是為了證明：VCF 9.1 的 MP 端點仍然可用（客戶舊腳本不會一夕全死），
但新開發請走 Policy（見 03_nsx_policy.py）。

    python sdk/04_nsx_manager_mp.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import config                    # noqa: E402
from common.clients import nsx_stub_config   # noqa: E402

from vcf.nsx.api.v1_client import TransportZones  # noqa: E402
from vcf.nsx.api.v1.cluster_client import Status  # noqa: E402

cfg, verify = config.get("nsx")
sc = nsx_stub_config(cfg["host"], cfg["user"], cfg["password"], verify)

tz = TransportZones(sc).list_transport_zones()
print("GET /api/v1/transport-zones     → %s 筆" % tz.result_count)
for z in (tz.results or [])[:3]:
    print("   ", z.display_name, z.transport_type)

st = Status(sc).read_cluster_status()
print("GET /api/v1/cluster/status      →", st.control_cluster_status.status)

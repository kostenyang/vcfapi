"""NSX 9.1 Policy（base https://<nsx>/policy/api/v1）— Tier-0/Tier-1/Segment。

VCF 9 建議一律走 Policy；MP (/api/v1) 端點雖仍在，但新功能只長在 Policy。

    python sdk/03_nsx_policy.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import config                    # noqa: E402
from common.clients import nsx_stub_config   # noqa: E402

from vcf.nsx.policy.api.v1.infra_client import (Segments, Tier0s,  # noqa: E402
                                                Tier1s)

cfg, verify = config.get("nsx")
sc = nsx_stub_config(cfg["host"], cfg["user"], cfg["password"], verify)

for label, svc, call in (("GET /policy/api/v1/infra/tier-0s", Tier0s(sc), "policy_lm_list_tier0s"),
                         ("GET /policy/api/v1/infra/tier-1s", Tier1s(sc), "policy_lm_list_tier1"),
                         ("GET /policy/api/v1/infra/segments", Segments(sc), "policy_lm_list_all_infra_segments")):
    res = getattr(svc, call)()
    print("%-38s → %s 筆" % (label, res.result_count))
    for r in (res.results or [])[:3]:
        print("   ", r.display_name, r.path)

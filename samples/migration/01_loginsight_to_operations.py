"""Migration — Log Insight  ->  VCF Operations.

OLD (removed in VCF 9.1, verified 404 live):
    POST /api/v1|v2/sessions          # Log Insight standalone login — GONE
    GET  /events                       # log query
    GET  /alerts                       # log-based alerts

NEW:
    Auth = VCF Operations OpsToken (POST /suite-api/api/auth/token/acquire).
    Alerts are unified into VCF Operations:  GET/POST /suite-api/api/alerts.
    Log query (if Log Management is deployed): exchange the OpsToken for an
        ops-li JWT, then POST /v2/logs/search.

This script demonstrates the alert path (works on any VCF Operations); log
search needs the Log Management component deployed in the instance.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


def main():
    ops = auth.vcf_operations_rest()      # OpsToken via /suite-api/api/
    print("Logged in to VCF Operations (replaces Log Insight login).")

    alerts = ops.get("/alerts").json()
    items = alerts.get("alerts", alerts if isinstance(alerts, list) else [])
    print(f"Active alerts (was Log Insight /alerts): {len(items)}")
    for a in items[:10]:
        print(f"  - {a.get('alertLevel','')}: {a.get('status','')}  {a.get('alertId','')}")

    print("\nLog search: OpsToken -> exchange(ops-li) -> POST /v2/logs/search "
          "(needs Log Management deployed; see common.auth.log_management_rest).")


if __name__ == "__main__":
    main()

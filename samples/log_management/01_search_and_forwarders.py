"""VCF Log Management (was vRealize Log Insight) — query + forwarders.

升級改寫對照表 — this is a "功能遷移" (function migrated), the biggest change
in the Operations family:

  * Standalone Log Insight login (POST /api/v1|v2/sessions) is REMOVED.
    Auth = OpsToken from VCF Operations, exchanged for an "ops-li" JWT, sent as
    X-JWT-Token. (common.auth.log_management_rest handles both steps.)

  NOTE (home.lab m02, 2026-06-26): the token/exchange endpoint exists but returns
  'Invalid service keys provided: ops-li' — i.e. Log Management / Log Insight is
  NOT deployed/registered in that VCF instance, so there is no ops-li service to
  exchange for. The flow here is correct for a build where Log Management IS
  deployed; confirm the service key for your instance.
  * Log query moved from  GET /events?<constraints>  to a structured
    POST /v2/logs/search  with a JSON body.  (NOTE: POST /v2/search is
    Deprecated — use /v2/logs/search.)
  * Email/SMTP notification -> Log Forwarders:  POST /v2/logs/forwarders
  * Log-based alerts moved OUT to VCF Operations  GET/POST /api/alerts/.

Endpoints used:
    POST /v2/logs/search
    GET  /v2/logs/forwarders
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common import auth  # noqa: E402


def search_logs(lm, query_text="", minutes=15, limit=50):
    now_ms = int(time.time() * 1000)
    body = {
        "logQuery": {
            "startTime": now_ms - minutes * 60 * 1000,
            "endTime": now_ms,
            "limit": limit,
            # structured constraints replace the old GET query-string params
            "constraints": ([{"field": "text", "operator": "CONTAINS",
                              "value": query_text}] if query_text else []),
        }
    }
    return lm.post("/v2/logs/search", json=body).json()


def list_forwarders(lm):
    return lm.get("/v2/logs/forwarders").json()


def main():
    lm = auth.log_management_rest()
    print("Authenticated to VCF Log Management (ops-li JWT via VCF Operations).")

    result = search_logs(lm, query_text="", minutes=15, limit=20)
    events = result.get("logs", result.get("results", []))
    print(f"\nLast-15-min events returned: {len(events)}")
    for e in events[:10]:
        text = e.get("text", e.get("message", ""))
        print(f"  · {text[:110]}")

    fwd = list_forwarders(lm)
    items = fwd.get("forwarders", fwd if isinstance(fwd, list) else [])
    print(f"\nLog forwarders ({len(items)}):")
    for f in items:
        print(f"  - {f.get('name','?')}  -> {f.get('host','')}")


if __name__ == "__main__":
    main()

"""VCF Automation 9 — get a TENANT token by API, two paths + the /iaas 3-state.

The one question every vRA8->VCFA9 migration hits: "how do I get a tenant-scoped
token programmatically, and why does /iaas 500/403?" This sample answers both,
live and reproducibly.

Two ways to obtain a tenant token (both are API, no browser):

  Path A — VCD session login (works with just a password):
    POST /cloudapi/1.0.0/sessions
    Authorization: Basic base64(user@org:password)
    Accept: application/json;version=9.1.0
    -> token is returned in the  X-VMWARE-VCLOUD-ACCESS-TOKEN  response header

  Path B — persistent API (refresh) token:
    The refresh token itself must be minted in the VCFA UI
    (My Account > API Tokens, while switched into the tenant org) — the
    POST /cloudapi/1.0.0/tokens API is system-gated (403/400) in this build.
    Once you have the refresh token, exchanging it IS pure API:
    POST /oauth/tenant/<org>/token   grant_type=refresh_token&refresh_token=...

The /iaas/api/* 3-state (same call, token scope decides):
    provider token                              -> 500 (gateway can't route)
    tenant token, no Cloud Assembly rights      -> 403 (reaches IaaS, denied)
    tenant token + rights + org onboarded       -> 200
  ...while /deployment, /catalog, /blueprint answer 200 with any tenant token.

Config: config/lab.yaml `vcfa_tenant` (org/user/password) and, optionally,
`vcf_automation.api_token` (a UI-minted refresh token) + `org`.

    python samples/vcf_automation/02_tenant_token_two_paths.py
"""
import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import requests  # noqa: E402
import urllib3  # noqa: E402

from common import config  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ACCEPT = "application/json;version=9.1.0"


def path_a_session(host, fqdn, org, user, password, verify):
    """Path A: VCD session login -> tenant access token (pure API)."""
    cred = base64.b64encode(f"{user}@{org}:{password}".encode()).decode()
    r = requests.post(f"https://{host}/cloudapi/1.0.0/sessions",
                      headers={"Host": fqdn, "Accept": ACCEPT,
                               "Authorization": f"Basic {cred}"},
                      verify=verify, timeout=20)
    r.raise_for_status()
    token = r.headers.get("X-VMWARE-VCLOUD-ACCESS-TOKEN")
    print(f"  Path A  POST /cloudapi/1.0.0/sessions -> {r.status_code}, "
          f"tenant token acquired ({len(token)} chars)")
    return token


def path_b_refresh(host, fqdn, org, refresh_token, verify):
    """Path B: exchange a UI-minted refresh token -> tenant access token."""
    r = requests.post(f"https://{host}/oauth/tenant/{org}/token",
                      data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                      headers={"Host": fqdn, "Accept": "application/*",
                               "Content-Type": "application/x-www-form-urlencoded"},
                      verify=verify, timeout=20)
    if r.status_code != 200:
        print(f"  Path B  /oauth/tenant/{org}/token -> {r.status_code} "
              f"({r.json().get('error_description', r.text[:60])})")
        return None
    print(f"  Path B  /oauth/tenant/{org}/token -> 200, tenant token acquired")
    return r.json()["access_token"]


def show_iaas_states(host, fqdn, token, verify):
    hdr = {"Host": fqdn, "Accept": ACCEPT, "Authorization": f"Bearer {token}"}
    print("  probing endpoints with this tenant token:")
    for ep in ("/iaas/api/projects", "/deployment/api/deployments",
               "/catalog/api/items", "/blueprint/api/blueprints"):
        try:
            code = requests.get(f"https://{host}{ep}", headers=hdr, verify=verify, timeout=15).status_code
        except Exception as exc:  # noqa: BLE001
            code = type(exc).__name__
        note = ""
        if ep.startswith("/iaas") and code == 403:
            note = "  <- reaches IaaS but needs Cloud Assembly rights + org onboarded"
        elif ep.startswith("/iaas") and code == 500:
            note = "  <- provider-scope token (not tenant); gateway can't route"
        print(f"    GET {ep:34s} {code}{note}")


def main():
    verify = config.verify_tls(config.load())
    t = config.load("vcfa_tenant")
    fqdn = t.get("fqdn", t["host"])

    print("VCF Automation 9 — tenant token, two API paths")
    print("-" * 62)
    token = path_a_session(t["host"], fqdn, t["org"], t["user"], t["password"], verify)
    show_iaas_states(t["host"], fqdn, token, verify)

    # Path B only if a UI-minted refresh token is configured for a tenant org.
    va = config.load("vcf_automation")
    org = va.get("org")
    rt = va.get("api_token")
    print("-" * 62)
    if org and rt and rt != "PASTE_VCFA_API_TOKEN_HERE":
        tok = path_b_refresh(va["host"], va.get("fqdn", va["host"]), org, rt, verify)
        if tok:
            show_iaas_states(va["host"], va.get("fqdn", va["host"]), tok, verify)
    else:
        print("  Path B skipped — set vcf_automation.org + a tenant-org API token "
              "(minted in the VCFA UI) to demo the persistent-token path.")


if __name__ == "__main__":
    main()

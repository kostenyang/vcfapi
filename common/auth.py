"""Authentication / connection helpers for every VCF 9.1 component used by the
IaaS automation samples.

One module, because in VCF 9 authentication is *unified*: a single VCF SDK
login yields a session shared across the SOAP (pyVmomi), REST (vSphere
Automation) and vSAN APIs, instead of logging in three separate times.
  Blog: https://blogs.vmware.com/cloud-foundation/2025/11/19/unified-authentication-in-vmware-cloud-foundation-sdk-9-0-seamless-authentication-across-vsphere-and-vsan-apis/

REST helpers below need only `requests`; the SDK helpers (pyVmomi / vSphere
Automation) import the unified `vcf-sdk` lazily so the REST samples run without
the SDK installed.
"""
from __future__ import annotations

import requests
import urllib3

from . import config

# Nested labs use self-signed certs. We disable the warning only — whether TLS
# is actually verified is controlled per-call by config.verify_tls().
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ---------------------------------------------------------------------------
# Generic REST client
# ---------------------------------------------------------------------------
class RestClient:
    """Thin wrapper over requests.Session that prepends a base URL and applies
    the lab's TLS verification setting. Returned by every *_rest() helper."""

    def __init__(self, base_url: str, session: requests.Session, verify):
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.verify = verify

    def request(self, method: str, path: str, **kw):
        kw.setdefault("verify", self.verify)
        kw.setdefault("timeout", 60)
        resp = self.session.request(method, self.base_url + path, **kw)
        resp.raise_for_status()
        return resp

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, **kw):
        return self.request("POST", path, **kw)

    def put(self, path, **kw):
        return self.request("PUT", path, **kw)

    def patch(self, path, **kw):
        return self.request("PATCH", path, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)


# ---------------------------------------------------------------------------
# vCenter / vSphere 9.1
# ---------------------------------------------------------------------------
def vcenter_rest(cfg: dict | None = None) -> RestClient:
    """vSphere REST API session.

    POST /api/session  (HTTP Basic) -> session id, sent thereafter as the
    `vmware-api-session-id` header. This is the modern replacement for many of
    the customer's pyVmomi SOAP calls (power, snapshot, tagging, ...).
    """
    cfg = cfg or config.load("vcenter")
    verify = config.verify_tls(config.load())
    base = f"https://{cfg['host']}"

    s = requests.Session()
    r = s.post(f"{base}/api/session", auth=(cfg["user"], cfg["password"]),
               verify=verify, timeout=60)
    r.raise_for_status()
    session_id = r.json()
    s.headers.update({"vmware-api-session-id": session_id,
                      "Content-Type": "application/json"})
    return RestClient(base, s, verify)


def pyvmomi_connect(cfg: dict | None = None):
    """SOAP connection via pyVmomi (now shipped inside vcf-sdk).

    Import path is unchanged from vSphere 7/8 — existing automation logic is
    largely reusable; only the install source (vcf-sdk) and the runtime
    (Python >= 3.10) change. Keep pyVmomi for what REST does not yet cover:
    DVS advanced config, AlarmManager, CustomSpecManager, PropertyCollector.
    """
    import ssl

    from pyVim.connect import SmartConnect          # provided by vcf-sdk in VCF 9
    cfg = cfg or config.load("vcenter")

    ctx = ssl.create_default_context()
    if not config.verify_tls(config.load()):
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return SmartConnect(host=cfg["host"], user=cfg["user"],
                        pwd=cfg["password"], sslContext=ctx)


def vsphere_automation_client(cfg: dict | None = None):
    """vSphere Automation (vAPI) client.

    Import path is identical to the old standalone SDK — only the package
    source changed (now bundled in vcf-sdk):
        from vmware.vapi.vsphere.client import create_vsphere_client
    """
    import requests as _rq
    from vmware.vapi.vsphere.client import create_vsphere_client

    cfg = cfg or config.load("vcenter")
    sess = _rq.Session()
    sess.verify = config.verify_tls(config.load())
    return create_vsphere_client(server=cfg["host"], username=cfg["user"],
                                 password=cfg["password"], session=sess)


# ---------------------------------------------------------------------------
# VCF Operations (was vRealize Operations / vROps)
#   NOTE (verified against VCF Operations 9.1 in the home.lab): this build still
#   serves the Suite API under /suite-api/api/ — it did NOT move to /api/ as the
#   migration analysis assumed. The auth header may be "OpsToken" OR the legacy
#   "vRealizeOpsToken" (both accepted). We keep OpsToken.
#   The RestClient base_url therefore includes /suite-api/api, so callers use
#   short paths like "/adapters", "/resources", "/reports".
# ---------------------------------------------------------------------------
OPS_API_BASE = "/suite-api/api"


def vcf_operations_rest(cfg: dict | None = None) -> RestClient:
    cfg = cfg or config.load("vcf_operations")
    verify = config.verify_tls(config.load())
    root = f"https://{cfg['host']}"

    body = {"username": cfg["user"], "password": cfg["password"]}
    if cfg.get("authSource"):
        body["authSource"] = cfg["authSource"]

    s = requests.Session()
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    r = s.post(f"{root}{OPS_API_BASE}/auth/token/acquire", json=body,
               verify=verify, timeout=60)
    r.raise_for_status()
    token = r.json()["token"]
    s.headers["Authorization"] = f"OpsToken {token}"   # or legacy vRealizeOpsToken
    return RestClient(root + OPS_API_BASE, s, verify)


# ---------------------------------------------------------------------------
# VCF Log Management (was vRealize Log Insight)
#   Standalone login removed. Get an OpsToken from VCF Operations, then
#   exchange it for an "ops-li" service JWT and send it as X-JWT-Token.
# ---------------------------------------------------------------------------
def log_management_rest(ops_cfg: dict | None = None,
                        lm_cfg: dict | None = None) -> RestClient:
    full = config.load()
    ops_cfg = ops_cfg or full["vcf_operations"]
    lm_cfg = lm_cfg or full["log_management"]
    verify = config.verify_tls(full)
    ops_base = f"https://{ops_cfg['host']}"

    s = requests.Session()
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    # 1) acquire OpsToken from VCF Operations (Suite API base, see note above)
    acq = s.post(f"{ops_base}{OPS_API_BASE}/auth/token/acquire",
                 json={"username": ops_cfg["user"], "password": ops_cfg["password"]},
                 verify=verify, timeout=60)
    acq.raise_for_status()
    ops_token = acq.json()["token"]

    # 2) exchange for the Log Management service token (serviceKeys: ["ops-li"])
    ex = s.post(f"{ops_base}{OPS_API_BASE}/auth/token/exchange",
                headers={"Authorization": f"OpsToken {ops_token}"},
                json={"serviceKeys": ["ops-li"]}, verify=verify, timeout=60)
    ex.raise_for_status()
    jwt = ex.json().get("token") or ex.json().get("access_token")

    s.headers["X-JWT-Token"] = jwt
    return RestClient(f"https://{lm_cfg['host']}", s, verify)


# ---------------------------------------------------------------------------
# SDDC Manager / SDDC Lifecycle (was vRealize Lifecycle Manager)
#   POST /v1/tokens -> { accessToken, refreshToken }, sent as Bearer.
# ---------------------------------------------------------------------------
def sddc_manager_rest(cfg: dict | None = None) -> RestClient:
    cfg = cfg or config.load("sddc_manager")
    verify = config.verify_tls(config.load())
    base = f"https://{cfg['host']}"

    s = requests.Session()
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    r = s.post(f"{base}/v1/tokens",
               json={"username": cfg["user"], "password": cfg["password"]},
               verify=verify, timeout=60)
    r.raise_for_status()
    s.headers["Authorization"] = f"Bearer {r.json()['accessToken']}"
    return RestClient(base, s, verify)


def _vapi_api_client(stub_factory_cls, session, url):
    """Wire a pre-authenticated requests session into a vAPI ApiClient.

    The SDK makes its REST calls through the session, so once the session
    carries the auth header (Bearer / OpsToken / basic), the stub factory needs
    no extra security-context filter. Keeps the SDK helpers small.
    """
    from vmware.vapi.bindings.stub import ApiClient
    from vmware.vapi.lib.connect import get_requests_connector
    from vmware.vapi.stdlib.client.factories import StubConfigurationFactory

    conn = StubConfigurationFactory.new_std_configuration(
        get_requests_connector(session=session, msg_protocol="rest", url=url))
    return ApiClient(stub_factory_cls(conn))


def sddc_manager_client(cfg: dict | None = None):
    """SDDC Manager SDK client — a NEW capability in VCF 9 (no vSphere 7/8
    equivalent). Real module is `vmware.sddc_manager_client.StubFactory`.
    Call e.g. client.v1.Domains.get_domains().elements,
              client.v1.Credentials.get_credentials().elements
    """
    from vmware.sddc_manager_client import StubFactory

    cfg = cfg or config.load("sddc_manager")
    verify = config.verify_tls(config.load())
    base = f"https://{cfg['host']}"
    s = requests.Session()
    s.verify = verify
    r = s.post(f"{base}/v1/tokens",
               json={"username": cfg["user"], "password": cfg["password"]},
               timeout=60)
    r.raise_for_status()
    s.headers["Authorization"] = f"Bearer {r.json()['accessToken']}"
    return _vapi_api_client(StubFactory, s, base)


def vcf_operations_client(cfg: dict | None = None):
    """VCF Operations (vROps) SDK client. Real module is
    `vcf.operations_client.StubFactory`; services live under client.api.*
    (Adapters, Resources, Reports, Alerts, ...). Mirrors the REST helper
    vcf_operations_rest but returns the typed SDK client.
    """
    from vcf.operations_client import StubFactory

    cfg = cfg or config.load("vcf_operations")
    verify = config.verify_tls(config.load())
    root = f"https://{cfg['host']}"
    body = {"username": cfg["user"], "password": cfg["password"]}
    if cfg.get("authSource"):
        body["authSource"] = cfg["authSource"]
    s = requests.Session()
    s.verify = verify
    s.headers["Accept"] = "application/json"
    r = s.post(f"{root}{OPS_API_BASE}/auth/token/acquire", json=body, timeout=60)
    r.raise_for_status()
    s.headers["Authorization"] = f"OpsToken {r.json()['token']}"
    return _vapi_api_client(StubFactory, s, f"{root}/suite-api")


# ---------------------------------------------------------------------------
# VCF Automation (was vRA 8 / Aria Automation)
#   VERIFIED against VCFA 9.1 (home.lab m02):
#     * VCFA 9 is Kubernetes-based with host-based ingress — you MUST connect by
#       FQDN (e.g. vcf-m02-auto-vip.home.lab), NOT by IP (IP returns 404). So the
#       FQDN must resolve (DNS or /etc/hosts).
#     * The IaaS API is live: GET /iaas/api/about -> 200.
#     * The vRA8 login path POST /csp/gateway/am/api/login is GONE (backend 404).
#       Login now goes through the VCF Identity Broker; the exact token endpoint
#       is build-specific — confirm against your release's API docs and use the
#       correct provider credential before wiring it in below.
#   The two-step below is the vRA8 shape, kept as a starting point / TODO.
# ---------------------------------------------------------------------------
def vcf_automation_rest(cfg: dict | None = None) -> RestClient:
    cfg = cfg or config.load("vcf_automation")
    verify = config.verify_tls(config.load())
    base = f"https://{cfg['host']}"

    s = requests.Session()
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    # VCFA 9 host-based ingress: if connecting by IP, force the vhost via Host hdr.
    if cfg.get("fqdn"):
        s.headers["Host"] = cfg["fqdn"]

    api_token = cfg.get("api_token")
    if not api_token:
        raise RuntimeError(
            "VCF Automation 9 no longer accepts vRA8 username/password API login "
            "(/csp/gateway/am/api/login is gone; auth is federated via VCF Identity "
            "Broker / OIDC). Generate an API token in the VCFA UI and set it as "
            "vcf_automation.api_token in config/lab.yaml.")

    # VCF Automation 9 token exchange (NOT vRA8's /iaas/api/login — that returns
    # invalid_grant on 9). The API token is a refresh token, exchanged at the
    # OAuth endpoint for a 1-hour Bearer access token:
    #   provider context: POST /oauth/provider/token
    #   tenant context:   POST /oauth/tenant/<org>/token
    # body: application/x-www-form-urlencoded  grant_type=refresh_token&refresh_token=...
    org = cfg.get("org")
    token_url = (f"{base}/oauth/tenant/{org}/token" if org
                 else f"{base}/oauth/provider/token")
    tok = s.post(token_url,
                 data={"grant_type": "refresh_token", "refresh_token": api_token},
                 headers={"Accept": "application/*",
                          "Content-Type": "application/x-www-form-urlencoded"},
                 verify=verify, timeout=60)
    if tok.status_code == 400 and "invalid_grant" in tok.text:
        raise RuntimeError(
            "VCFA rejected the API token (invalid_grant). Re-generate it in the "
            "VCFA UI; copy the FULL value; check it has not expired (90-day) or "
            "been superseded. For tenant-scoped tokens set vcf_automation.org.")
    tok.raise_for_status()
    s.headers["Authorization"] = f"Bearer {tok.json()['access_token']}"
    return RestClient(base, s, verify)


# ---------------------------------------------------------------------------
# vRA 8 / Aria Automation 8  —  SOURCE / "before" helper (migration baseline)
#
# This is the OLD product the customer is migrating FROM. It is included so the
# same script can read the source estate (projects, deployments, catalog,
# blueprints, IaaS machines) BEFORE cut-over and diff it against VCF Automation
# 9. The vRA8 login below (username/password -> cspAuthToken bearer) is exactly
# the flow that is REMOVED in VCFA 9 — see vcf_automation_rest() for the new
# OAuth/refresh-token path that replaces it.
#
#   vRA 8:  POST /csp/gateway/am/api/login {username,password} -> {cspAuthToken}
#           Authorization: Bearer <cspAuthToken>   (an OIDC id_token, ~1h)
#   VCFA 9: POST /oauth/provider|tenant/<org>/token  grant_type=refresh_token
#
# NOTE: /csp/gateway/am/api/login/access-token (the refresh-token variant used
# by vRA Cloud) is 404 on this on-prem 8.x appliance; the id_token from
# /csp/gateway/am/api/login works directly as a bearer, so we use that.
# ---------------------------------------------------------------------------
def vra8_rest(cfg: dict | None = None) -> RestClient:
    cfg = cfg or config.load("vra8")
    verify = config.verify_tls(config.load())
    base = f"https://{cfg['host']}"

    s = requests.Session()
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    # host-based ingress: when connecting by IP, force the vhost via Host header.
    if cfg.get("fqdn"):
        s.headers["Host"] = cfg["fqdn"]

    body = {"username": cfg["user"], "password": cfg["password"]}
    if cfg.get("domain"):                      # vIDM users need their domain
        body["domain"] = cfg["domain"]
    r = s.post(f"{base}/csp/gateway/am/api/login",
               json=body, verify=verify, timeout=60)
    if r.status_code == 404:
        raise RuntimeError(
            "vRA8 /csp/gateway/am/api/login returned 404 — this is NOT a vRA 8 "
            "host, or you are pointed at a VCF Automation 9 appliance (which "
            "removed this endpoint). Use vcf_automation_rest() for VCFA 9.")
    r.raise_for_status()
    token = r.json().get("cspAuthToken")
    if not token:
        raise RuntimeError(f"vRA8 login OK ({r.status_code}) but no cspAuthToken "
                           f"in response: {r.text[:160]}")
    s.headers["Authorization"] = f"Bearer {token}"
    return RestClient(base, s, verify)


# ---------------------------------------------------------------------------
# NSX 9 — Policy API (was NSX-T). Basic auth is the simplest path; switch to
# session auth (POST /api/session/create + X-XSRF-TOKEN) for high call volumes.
# ---------------------------------------------------------------------------
def nsx_rest(cfg: dict | None = None) -> RestClient:
    cfg = cfg or config.load("nsx")
    verify = config.verify_tls(config.load())
    s = requests.Session()
    s.auth = (cfg["user"], cfg["password"])
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    return RestClient(f"https://{cfg['host']}", s, verify)


def nsx_policy_client(cfg: dict | None = None):
    """NSX 9 Policy API via the VCF SDK.

    Real module is `vcf.nsx.policy.api.v1_client.StubFactory`. Services hang off
    client.infra.* — e.g. client.infra.domains.Groups.policy_list_group_for_domain("default").
    Auth is a user/password security context (not a pre-set header).
    Needs vcf-sdk on Python >= 3.10.
    """
    from vmware.vapi.bindings.stub import ApiClient
    from vmware.vapi.lib.connect import get_requests_connector
    from vmware.vapi.security.user_password import (
        create_user_password_security_context)
    from vmware.vapi.stdlib.client.factories import StubConfigurationFactory
    from vcf.nsx.policy.api.v1_client import StubFactory

    cfg = cfg or config.load("nsx")
    verify = config.verify_tls(config.load())
    s = requests.Session()
    s.verify = verify
    stub_config = StubConfigurationFactory.new_std_configuration(
        get_requests_connector(session=s, msg_protocol="rest",
                               url=f"https://{cfg['host']}"))
    stub_config.connector.set_security_context(
        create_user_password_security_context(cfg["user"], cfg["password"]))
    return ApiClient(StubFactory(stub_config))

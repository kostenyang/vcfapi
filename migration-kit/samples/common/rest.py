"""純 REST 認證 helper — 只依賴 requests，Python 3.8 也能跑。

VCF SDK 需要 Python 3.10+；客戶若還在 3.8，用這裡的寫法照樣打得到同一組 API。
"""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def session(verify=False):
    s = requests.Session()
    s.verify = verify
    return s


def vcenter_session_id(host, user, password, verify=False):
    """POST /api/session（Basic）→ session id，之後帶 vmware-api-session-id。"""
    r = session(verify).post("https://%s/api/session" % host, auth=(user, password), timeout=20)
    r.raise_for_status()
    return r.json()


def sddc_manager_token(host, user, password, verify=False):
    """POST /v1/tokens → accessToken（Bearer）。VCF Installer 同一支寫法。"""
    r = session(verify).post("https://%s/v1/tokens" % host,
                             json={"username": user, "password": password}, timeout=20)
    r.raise_for_status()
    return r.json()["accessToken"]


def operations_token(host, user, password, verify=False):
    """POST /suite-api/api/auth/token/acquire → token（Authorization: OpsToken ...）。"""
    r = session(verify).post("https://%s/suite-api/api/auth/token/acquire" % host,
                             json={"username": user, "password": password},
                             headers={"Accept": "application/json"}, timeout=20)
    r.raise_for_status()
    return r.json()["token"]


def operations_networks_token(host, user, password, domain_type="LOCAL", verify=False):
    """POST /api/ni/auth/token → token（Authorization: NetworkInsight ...）。"""
    r = session(verify).post("https://%s/api/ni/auth/token" % host,
                             json={"username": user, "password": password,
                                   "domain": {"domain_type": domain_type}}, timeout=20)
    r.raise_for_status()
    return r.json()["token"]


def vcfa_tenant_token(host, fqdn, org, user, password, verify=False):
    """VCFA 9：Basic user@org:pw → POST /cloudapi/1.0.0/sessions
    token 在回應標頭 X-VMWARE-VCLOUD-ACCESS-TOKEN。host 是 IP 時要帶 Host: fqdn。"""
    import base64
    cred = base64.b64encode(("%s@%s:%s" % (user, org, password)).encode()).decode()
    r = session(verify).post("https://%s/cloudapi/1.0.0/sessions" % host,
                             headers={"Host": fqdn or host,
                                      "Accept": "application/json;version=9.1.0",
                                      "Authorization": "Basic " + cred}, timeout=20)
    r.raise_for_status()
    return r.headers["X-VMWARE-VCLOUD-ACCESS-TOKEN"]

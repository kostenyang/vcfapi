"""vRealize Automation 8：csp 帳密登入 + IaaS/Deployment API。"""
import base64
import requests


def login(host, user, password, org="System", verify=False):
    cred = base64.b64encode(f"{user}@{org}:{password}".encode()).decode()
    r = requests.post("https://%s/cloudapi/1.0.0/sessions" % host,
                      headers={"Authorization": "Basic " + cred,
                               "Accept": "application/json;version=9.1.0"}, verify=verify, timeout=30)
    r.raise_for_status()
    return r.headers["X-VMWARE-VCLOUD-ACCESS-TOKEN"]


def list_deployments(host, token, verify=False):
    r = requests.get("https://%s/deployment/api/deployments" % host,
                     headers={"Authorization": "Bearer " + token}, verify=verify, timeout=30)
    r.raise_for_status()
    return r.json()["content"]


def list_projects(host, token, verify=False):
    r = requests.get("https://%s/iaas/api/projects" % host,
                     headers={"Authorization": "Bearer " + token}, verify=verify, timeout=30)
    r.raise_for_status()
    return r.json()["content"]

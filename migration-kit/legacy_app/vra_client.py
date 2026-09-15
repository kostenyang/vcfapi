"""vRealize Automation 8：csp 帳密登入 + IaaS/Deployment API。"""
import requests


def login(host, user, password, verify=False):
    r = requests.post("https://%s/csp/gateway/am/api/login?access_token" % host,
                      json={"username": user, "password": password}, verify=verify, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


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

"""vRealize Operations 8：suite-api + vRealizeOpsToken 標頭。"""
import requests


def acquire_token(host, user, password, verify=False):
    r = requests.post("https://%s/suite-api/api/auth/token/acquire" % host,
                      json={"username": user, "password": password},
                      headers={"Accept": "application/json"}, verify=verify, timeout=30)
    r.raise_for_status()
    return r.json()["token"]


def get_resources(host, token, page_size=10, verify=False):
    r = requests.get("https://%s/suite-api/api/resources" % host,
                     params={"pageSize": page_size},
                     headers={"Authorization": "vRealizeOpsToken " + token,
                              "Accept": "application/json"}, verify=verify, timeout=60)
    r.raise_for_status()
    return r.json()["resourceList"]


def get_adapter_kinds(host, token, verify=False):
    r = requests.get("https://%s/suite-api/api/adapterkinds" % host,
                     headers={"Authorization": "vRealizeOpsToken " + token,
                              "Accept": "application/json"}, verify=verify, timeout=30)
    r.raise_for_status()
    return r.json()["adapter-kind"]

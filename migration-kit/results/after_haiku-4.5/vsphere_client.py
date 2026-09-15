"""vSphere：舊的 /rest facade 寫法（vSphere 6.5–8 年代）。"""
import requests


def login(host, user, password, verify=False):
    r = requests.post("https://%s/api/session" % host,
                      auth=(user, password), verify=verify, timeout=30)
    r.raise_for_status()
    return r.json()


def list_vms(host, session_id, verify=False):
    r = requests.get("https://%s/api/vcenter/vm" % host,
                     headers={"vmware-api-session-id": session_id}, verify=verify, timeout=30)
    r.raise_for_status()
    return r.json()


def list_hosts(host, session_id, verify=False):
    r = requests.get("https://%s/api/vcenter/host" % host,
                     headers={"vmware-api-session-id": session_id}, verify=verify, timeout=30)
    r.raise_for_status()
    return r.json()

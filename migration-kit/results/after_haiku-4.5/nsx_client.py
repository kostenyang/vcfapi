"""NSX-T 2.x/3.x 年代的 Manager API 寫法（混雜了 NSX-V 世代已移除的端點）。"""
import requests


def list_transport_zones(host, user, password, verify=False):
    r = requests.get("https://%s/api/v1/transport-zones" % host,
                     auth=(user, password), verify=verify, timeout=30)
    r.raise_for_status()
    return r.json()["results"]


def list_segments(host, user, password, verify=False):
    r = requests.get("https://%s/policy/api/v1/infra/segments" % host,
                     auth=(user, password), verify=verify, timeout=30)
    r.raise_for_status()
    return r.json()["results"]


def list_firewall_sections(host, user, password, verify=False):
    r = requests.get("https://%s/policy/api/v1/infra/domains/default/security-policies" % host,
                     auth=(user, password), verify=verify, timeout=30)
    r.raise_for_status()
    return r.json()["results"]

"""vSphere：舊 /rest 與新 /api 都能通（9.1 兩者都 200），這組測試守「行為沒壞」，
「該不該改」由 tools/scan_legacy.py 判（/rest facade 已 deprecated）。"""
from legacy_app import vsphere_client as c

H, U, P = "vc.example.local", "user", "pw"


def test_login_returns_session_id():
    sid = c.login(H, U, P)
    assert isinstance(sid, str) and sid


def test_list_vms_returns_vm_records():
    vms = c.list_vms(H, c.login(H, U, P))
    assert isinstance(vms, list) and vms
    assert {"vm", "name", "power_state"} <= set(vms[0])


def test_list_hosts_returns_host_records():
    hosts = c.list_hosts(H, c.login(H, U, P))
    assert hosts and "connection_state" in hosts[0]

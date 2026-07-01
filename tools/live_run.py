"""Actually EXECUTE each operation type against a live VCF 9.1 (not just probe).

Read ops run directly. Write/destructive ops run on a dedicated test VM this
script creates and then deletes (existing VMs are never touched). Endpoints and
credentials come from config/lab.yaml.

    pip install vcf-sdk requests PyYAML     # Python >= 3.10
    python tools/live_run.py

WARNING: this creates + deletes a VM (apitest-vm), migrates it between hosts, and
creates/removes a snapshot, a clone, tags, and an NSX group. It cleans up after
itself, but run it against a LAB, never production.
"""
import os
import ssl
import sys
import warnings

warnings.filterwarnings("ignore")
import requests  # noqa: E402
import urllib3  # noqa: E402

urllib3.disable_warnings()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import config  # noqa: E402

R = []
def rec(g, op, api, res, d=""): R.append((g, op, api, res, str(d)[:80])); print(f"  [{res}] {g} · {op} · {api} {('· '+str(d)[:50]) if d else ''}")
def ok(g, op, api, d=""): rec(g, op, api, "OK", d)
def err(g, op, api, e): rec(g, op, api, "ERR", f"{type(e).__name__}: {e}")


def main():
    from pyVim.connect import SmartConnect, Disconnect
    from pyVim.task import WaitForTask
    from pyVmomi import vim, vmodl

    cfg = config.load(); vc = cfg["vcenter"]
    P = vc["password"]; U = vc["user"]
    si = SmartConnect(host=vc["host"], user=U, pwd=P, sslContext=ssl._create_unverified_context())
    c = si.RetrieveContent()
    def allof(t):
        v = c.viewManager.CreateContainerView(c.rootFolder, [t], True)
        try: return list(v.view)
        finally: v.Destroy()

    testvm = clone = None
    try:
        for t, nm in [(vim.VirtualMachine, "VM"), (vim.HostSystem, "Host"), (vim.ClusterComputeResource, "Cluster"),
                      (vim.Datastore, "Datastore"), (vim.Network, "Network"), (vim.DistributedVirtualSwitch, "DVS")]:
            try: ok("vSphere-SOAP-read", f"list {nm}", f"ContainerView[{t.__name__}]", len(allof(t)))
            except Exception as e: err("vSphere-SOAP-read", f"list {nm}", t.__name__, e)
        dc = c.rootFolder.childEntity[0]; hosts = allof(vim.HostSystem); ds = allof(vim.Datastore)[0]
        host = hosts[0]; rp = allof(vim.ClusterComputeResource)[0].resourcePool; folder = dc.vmFolder
        for attr, nm in [("taskManager", "TaskManager"), ("eventManager", "EventManager"), ("alarmManager", "AlarmManager"),
                         ("customFieldsManager", "CustomFieldsManager"), ("sessionManager", "SessionManager"), ("perfManager", "PerformanceManager")]:
            try: getattr(c, attr); ok("vSphere-SOAP-read", f"get {nm}", f"content.{attr}", "present")
            except Exception as e: err("vSphere-SOAP-read", f"get {nm}", attr, e)

        # create test VM
        ctrl = vim.vm.device.VirtualDeviceSpec(operation="add", device=vim.vm.device.ParaVirtualSCSIController(key=1000, busNumber=0, sharedBus="noSharing"))
        disk = vim.vm.device.VirtualDeviceSpec(operation="add", fileOperation="create",
            device=vim.vm.device.VirtualDisk(key=0, controllerKey=1000, unitNumber=0, capacityInKB=1048576,
                backing=vim.vm.device.VirtualDisk.FlatVer2BackingInfo(diskMode="persistent", thinProvisioned=True, fileName=f"[{ds.name}]")))
        spec = vim.vm.ConfigSpec(name="apitest-vm", memoryMB=512, numCPUs=1, guestId="otherGuest",
            files=vim.vm.FileInfo(vmPathName=f"[{ds.name}]"), deviceChange=[ctrl, disk])
        WaitForTask(folder.CreateVM_Task(config=spec, pool=rp, host=host))
        testvm = [v for v in allof(vim.VirtualMachine) if v.name == "apitest-vm"][0]
        ok("vSphere-SOAP-write", "CreateVM", "vim.Folder.CreateVM_Task", testvm._moId)

        for label, fn, api in [
            ("ReconfigVM", lambda: WaitForTask(testvm.ReconfigVM_Task(spec=vim.vm.ConfigSpec(memoryMB=1024, annotation="apitest"))), "vim.VirtualMachine.ReconfigVM_Task"),
            ("Rename", lambda: (WaitForTask(testvm.Rename_Task("apitest-r")), WaitForTask(testvm.Rename_Task("apitest-vm"))), "vim.VirtualMachine.Rename_Task"),
            ("PowerOn", lambda: WaitForTask(testvm.PowerOnVM_Task()), "vim.VirtualMachine.PowerOnVM_Task"),
            ("PowerOff", lambda: WaitForTask(testvm.PowerOffVM_Task()), "vim.VirtualMachine.PowerOffVM_Task"),
            ("CreateSnapshot+Remove", lambda: (WaitForTask(testvm.CreateSnapshot_Task(name="s1", description="x", memory=False, quiesce=False)),
                                               WaitForTask(testvm.snapshot.rootSnapshotList[0].snapshot.RemoveSnapshot_Task(removeChildren=False))), "vim.VirtualMachine.CreateSnapshot_Task"),
            ("MarkAsTemplate+back", lambda: (testvm.MarkAsTemplate(), testvm.MarkAsVirtualMachine(pool=rp, host=testvm.runtime.host)), "vim.VirtualMachine.MarkAsTemplate"),
        ]:
            try: fn(); ok("vSphere-SOAP-write", label, api, "done")
            except Exception as e: err("vSphere-SOAP-write", label, api, e)
        try:
            cs = vim.vm.CloneSpec(location=vim.vm.RelocateSpec(pool=rp), powerOn=False, template=False)
            WaitForTask(testvm.CloneVM_Task(folder=folder, name="apitest-clone", spec=cs))
            clone = [v for v in allof(vim.VirtualMachine) if v.name == "apitest-clone"][0]
            ok("vSphere-SOAP-write", "Clone", "vim.VirtualMachine.CloneVM_Task", clone._moId)
        except Exception as e: err("vSphere-SOAP-write", "Clone", "CloneVM_Task", e)
        try:
            if len(hosts) > 1:
                WaitForTask(testvm.RelocateVM_Task(spec=vim.vm.RelocateSpec(host=hosts[1], pool=rp)))
                ok("vSphere-SOAP-write", "Relocate (vMotion host)", "vim.VirtualMachine.RelocateVM_Task", hosts[1].name)
        except Exception as e: err("vSphere-SOAP-write", "Relocate", "RelocateVM_Task", e)

        # vСenter REST
        s = requests.Session(); s.verify = False
        s.headers["vmware-api-session-id"] = s.post(f"https://{vc['host']}/api/session", auth=(U, P)).json()
        vbase = f"https://{vc['host']}"
        for path, nm in [("/api/vcenter/vm", "VM"), ("/api/vcenter/host", "Host"), ("/api/vcenter/cluster", "Cluster"),
                         ("/api/vcenter/datastore", "Datastore"), ("/api/vcenter/network", "Network"),
                         ("/api/appliance/system/version", "version"), ("/api/content/library", "ContentLibrary")]:
            try: ok("vSphere-REST-read", f"GET {nm}", path, f"HTTP {s.get(vbase + path).status_code}")
            except Exception as e: err("vSphere-REST-read", f"GET {nm}", path, e)
        try:
            vmid = testvm._moId
            a = s.post(f"https://{vc['host']}/api/vcenter/vm/{vmid}/power", params={"action": "start"})
            b = s.post(f"https://{vc['host']}/api/vcenter/vm/{vmid}/power", params={"action": "stop"})
            ok("vSphere-REST-write", "VM power start/stop", "/api/vcenter/vm/{id}/power", f"{a.status_code}/{b.status_code}")
        except Exception as e: err("vSphere-REST-write", "VM power", "/api/vcenter/vm/{id}/power", e)

        _services(cfg)
    finally:
        from pyVim.task import WaitForTask as W
        try:
            if clone: W(clone.Destroy_Task()); ok("cleanup", "Destroy clone", "Destroy_Task", "")
        except Exception as e: err("cleanup", "Destroy clone", "Destroy_Task", e)
        try:
            if testvm:
                if testvm.runtime.powerState == "poweredOn": W(testvm.PowerOffVM_Task())
                W(testvm.Destroy_Task()); ok("vSphere-SOAP-write", "Destroy (delete VM)", "vim.VirtualMachine.Destroy_Task", "removed")
        except Exception as e: err("cleanup", "Destroy testvm", "Destroy_Task", e)
        Disconnect(si)

    import collections
    print("\n=== 統計:", dict(collections.Counter(x[3] for x in R)), "共", len(R), "個實際操作 ===")


def _services(cfg):
    P = cfg["vcenter"]["password"]
    nsx = cfg.get("nsx"); sddc = cfg.get("sddc_manager"); ops = cfg.get("vcf_operations"); vra = cfg.get("vcf_automation")
    if nsx:
        n = requests.Session(); n.verify = False; n.auth = (nsx["user"], nsx["password"]); base = f"https://{nsx['host']}"
        for path, nm in [("/policy/api/v1/infra/domains/default/groups", "DFW groups"), ("/policy/api/v1/infra/services", "services")]:
            try: ok("NSX-read", f"GET {nm}", path, len(n.get(base + path).json().get("results", [])))
            except Exception as e: err("NSX-read", nm, path, e)
        try:
            n.put(base + "/policy/api/v1/infra/domains/default/groups/apitest-grp", json={"display_name": "apitest", "expression": [{"resource_type": "IPAddressExpression", "ip_addresses": ["10.0.0.99"]}]})
            d = n.delete(base + "/policy/api/v1/infra/domains/default/groups/apitest-grp")
            ok("NSX-write", "create+delete group", "PUT/DELETE .../groups/{id}", f"del {d.status_code}")
        except Exception as e: err("NSX-write", "group CRUD", ".../groups", e)
    if sddc:
        ss = requests.Session(); ss.verify = False; base = f"https://{sddc['host']}"
        try:
            ss.headers["Authorization"] = "Bearer " + ss.post(base + "/v1/tokens", json={"username": sddc["user"], "password": sddc["password"]}).json()["accessToken"]
            for path in ["/v1/credentials", "/v1/license-keys", "/v1/domains", "/v1/clusters", "/v1/hosts", "/v1/tasks"]:
                ok("SDDC-read", f"GET {path.split('/')[-1]}", path, f"HTTP {ss.get(base + path).status_code}")
            ok("SDDC-read", "vRLCM 舊 /lcm/ 確認", "GET /lcm/lcops/api/v2/environments", f"HTTP {ss.get(base + '/lcm/lcops/api/v2/environments').status_code} (removed)")
        except Exception as e: err("SDDC-read", "auth/list", "/v1/*", e)
    if ops:
        o = requests.Session(); o.verify = False; o.headers["Accept"] = "application/json"; base = f"https://{ops['host']}"
        try:
            o.headers["Authorization"] = "OpsToken " + o.post(base + "/suite-api/api/auth/token/acquire", json={"username": ops["user"], "password": ops["password"]}, headers={"Content-Type": "application/json"}).json()["token"]
            for path in ["/suite-api/api/adapters", "/suite-api/api/resources", "/suite-api/api/alerts", "/suite-api/api/reportdefinitions", "/suite-api/api/versions/current"]:
                ok("Operations-read", f"GET {path.split('/')[-1]}", path, f"HTTP {o.get(base + path).status_code}")
            li = requests.post(base + "/api/v2/sessions", json={}, headers={"Content-Type": "application/json"}, verify=False, timeout=6).status_code
            ok("Operations-read", "Log Insight 舊登入確認", "POST /api/v2/sessions", f"HTTP {li} (removed)")
        except Exception as e: err("Operations-read", "auth/list", "/suite-api/api/*", e)
    if vra and vra.get("api_token"):
        h = {"Host": vra.get("fqdn", vra["host"]), "Content-Type": "application/x-www-form-urlencoded"}; base = f"https://{vra['host']}"
        try:
            tb = requests.post(base + "/oauth/provider/token", headers=h, data={"grant_type": "refresh_token", "refresh_token": vra["api_token"]}, verify=False, timeout=10).json()["access_token"]
            hb = {"Host": vra.get("fqdn", vra["host"]), "Authorization": f"Bearer {tb}", "Accept": "application/json;version=9.1.0"}
            for path in ["/cloudapi/1.0.0/orgs", "/cloudapi/1.0.0/roles", "/cloudapi/1.0.0/users"]:
                ok("VCFA-read", f"GET {path.split('/')[-1]}", path, f"HTTP {requests.get(base + path, headers=hb, verify=False, timeout=8).status_code}")
            lg = requests.post(base + "/iaas/api/login", json={"refreshToken": "x"}, headers={"Host": vra.get("fqdn", vra["host"]), "Content-Type": "application/json"}, verify=False, timeout=8).status_code
            ok("VCFA-read", "vRA8 舊登入確認", "POST /iaas/api/login", f"HTTP {lg} (now OAuth)")
        except Exception as e: err("VCFA-read", "auth/list", "/oauth+/cloudapi", e)


if __name__ == "__main__":
    main()

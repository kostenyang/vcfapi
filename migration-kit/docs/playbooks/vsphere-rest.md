# Playbook：vSphere `/rest` facade → `/api`

**判斷**：看到 `/rest/com/vmware/cis/`、`/rest/vcenter/`、`/rest/appliance/`、`/rest/content/` → 改。
pyVmomi（SOAP）呼叫 → 不動。

**改法**：
1. 路徑 `/rest/com/vmware/cis/session` → `/api/session`；`/rest/vcenter/X` → `/api/vcenter/X`。
2. 回應少一層 `value`：`r.json()["value"]` → `r.json()`。
3. 登入回 201，`raise_for_status()` 不會因此失敗，但不要寫死 `== 200`。

```python
# before
r = requests.post(f"https://{h}/rest/com/vmware/cis/session", auth=(u, p), verify=False)
sid = r.json()["value"]
vms = requests.get(f"https://{h}/rest/vcenter/vm", headers={"vmware-api-session-id": sid}, verify=False).json()["value"]

# after
r = requests.post(f"https://{h}/api/session", auth=(u, p), verify=False)   # 201
sid = r.json()                                                              # 裸字串
vms = requests.get(f"https://{h}/api/vcenter/vm", headers={"vmware-api-session-id": sid}, verify=False).json()  # 裸 list
```

**保留**：函式簽章、回傳型別（list of dict）。呼叫端不用改。

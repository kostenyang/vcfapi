# Playbook：NSX Manager (MP) → Policy — 只改會 404 的

**判斷樹**
1. `/api/v1/transport-zones`、`/api/v1/node`、`/api/v1/cluster/*`、`/api/v1/fabric/*`、`/api/v1/licenses`、`/api/v1/trust-management/*` → **9.1 仍 200，不改**。
2. `/api/v1/logical-switches` → `/policy/api/v1/infra/segments`
3. `/api/v1/logical-routers` → `/policy/api/v1/infra/tier-0s` 或 `/tier-1s`
4. `/api/v1/firewall/sections` → `/policy/api/v1/infra/domains/default/security-policies`
5. `/api/v1/ns-groups` → `/policy/api/v1/infra/domains/default/groups`；`/api/v1/ns-services` → `/policy/api/v1/infra/services`
6. 已經是 `/policy/api/v1/` 的 → 不動。

認證不變（Basic 或 session cookie）。Policy list 回應也是 `{"results": [...], "result_count": n}`，欄位多了 `path`、`resource_type`。

```python
# before
r = requests.get(f"https://{h}/api/v1/logical-switches", auth=(u, p), verify=False)
# after
r = requests.get(f"https://{h}/policy/api/v1/infra/segments", auth=(u, p), verify=False)
return r.json()["results"]        # 形狀相同
```

**注意**：不要把第 1 類也改掉 —— 改越少越好，而且 Policy 沒有一對一的 node / cluster 端點。

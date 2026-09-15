# Playbook：vRA 8 → VCF Automation 9（唯一硬斷點）

**判斷**：`/csp/gateway/am/api/login`、`/iaas/api/login`、`cspAuthToken` → 必改。
`/deployment/api/*`、`/catalog/api/*`、`/blueprint/api/*` 路徑本身不變，只是 token 來源變了。

**登入改法（主路徑：VCD session 登入，只要帳密）**
```python
# before
r = requests.post(f"https://{h}/csp/gateway/am/api/login?access_token",
                  json={"username": u, "password": p}, verify=False)     # VCFA 9 → 404
token = r.json()["access_token"]

# after
import base64
cred = base64.b64encode(f"{u}@{org}:{p}".encode()).decode()
r = requests.post(f"https://{h}/cloudapi/1.0.0/sessions",
                  headers={"Authorization": "Basic " + cred,
                           "Accept": "application/json;version=9.1.0"}, verify=False)
r.raise_for_status()
token = r.headers["X-VMWARE-VCLOUD-ACCESS-TOKEN"]      # token 在標頭，不在 body
```
- 登入函式要多一個 `org` 參數。用 keyword 加預設值以免呼叫端全壞；建議 `org="System"`（provider org 的固定名稱），租戶呼叫時明確傳 org。
- `host` 是 IP 時要帶 `Host: <fqdn>`（host-based ingress），否則 404。

**替代路徑**：UI 產的 refresh token → `POST /oauth/tenant/{org}/token`（`grant_type=refresh_token`）→ `access_token`。
`POST /cloudapi/1.0.0/tokens` 在目前 build 被系統層擋（403/400），別走。

**之後的呼叫**：`Authorization: Bearer <token>` 不變。
- `/deployment/api/deployments` → 200
- `/iaas/api/*` → 租戶沒 Cloud Assembly 權限 403、provider token 500、org 未 onboarding 也拿不到 200。
  程式面只要 token 對；剩下是 VCFA 端的組態，寫進交接說明，不要在程式裡繞。

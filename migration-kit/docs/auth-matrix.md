# 認證對照（舊 → 新，皆實測）

| 系統 | 舊寫法 | VCF 9.1 寫法 | 變更 |
|---|---|---|---|
| vSphere REST | `POST /rest/com/vmware/cis/session`（Basic）→ `{"value": sid}` | `POST /api/session`（Basic）→ 201, `"sid"`；之後 `vmware-api-session-id: sid` | 🟡 路徑 + 回應形狀 |
| vSphere SOAP | pyVmomi `SmartConnect` | 同 | 🟢 不變 |
| vROps → VCF Operations | `POST /suite-api/api/auth/token/acquire` → `Authorization: vRealizeOpsToken t` | 同端點 → `Authorization: OpsToken t` | 🟡 只改 scheme（舊 scheme 9.1 仍收） |
| NSX | Basic 或 `POST /api/session/create` | 同 | 🟢 不變 |
| vRA 8 → VCFA 9 | `POST /csp/gateway/am/api/login` → `cspAuthToken`；`POST /iaas/api/login` refreshToken → access_token | `POST /cloudapi/1.0.0/sessions`（Basic `user@org:pw`）→ 標頭 `X-VMWARE-VCLOUD-ACCESS-TOKEN`；或 `POST /oauth/tenant/{org}/token`（refresh_token） | 🔴 硬斷點 |
| vRLCM → SDDC Manager | `/lcm/lcops/api/v2/login` | `POST /v1/tokens` → `accessToken`（Bearer） | 🔴 產品換了 |
| Log Insight → Log Mgmt | `POST /api/v1/sessions` | Bearer（VCF Operations 發） | 🔴 未實測 |

VCFA 走 host-based ingress：`host` 給 IP 時要另帶 `Host: <fqdn>` 標頭，否則一律 404。

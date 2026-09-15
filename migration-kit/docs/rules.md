# 遷移規則（每條都附 lab 實測依據）

實測環境：vCenter 9.1.1.0、SDDC Manager 9.1.1.0、NSX 9.1.x、VCF Operations 9.1.1.0、VCFA 9.1（2026-07 / 08 / 09 三輪）。
狀態碼是真的打出來的；沒打到的會寫「未實測」。

| # | 規則 | 依據（實測） |
|---|---|---|
| 1 | vSphere `/rest/` facade → `/api/`；回應拿掉 `{"value": …}` 一層 | `/rest/com/vmware/cis/session` 200、`/rest/vcenter/vm` 200（deprecated 但沒移除） |
| 2 | `POST /api/session` 回 201 + 裸字串 | 實測 201 |
| 3 | pyVmomi 8.x 舊碼直連 9.1 可用，不用改 | apiVersion 8.0.3.0 → 9.1.0.0，22/22 物件 OK |
| 4 | vROps `vRealizeOpsToken` → `OpsToken`（相容，建議改） | 兩種 scheme 都 200；`Bearer` 401 |
| 5 | NSX MP `/api/v1/*` 大多仍可用（node / cluster / transport-zones / fabric / licenses …） | 36 條 MP 端點全 200 |
| 6 | NSX-V 世代端點 404：`logical-switches`、`logical-routers`、`firewall/sections`、`ns-groups`、`ns-services` → Policy | 實測 404 |
| 7 | NSX 無認證 → 403（不是 401） | 實測 403 |
| 8 | vRA 8 `/csp/gateway/am/api/login` → 404；`/iaas/api/login` → 400 invalid_grant | 兩輪實測一致 |
| 9 | VCFA 租戶 token：`POST /cloudapi/1.0.0/sessions`（Basic `user@org:pw`）→ 標頭 `X-VMWARE-VCLOUD-ACCESS-TOKEN`；或 `/oauth/tenant/{org}/token` | 200 |
| 10 | `/iaas/api/*` 三態：provider token 500 / 租戶無權 403 / 租戶有權 + org onboarded 200 | 前兩態實測；第三態需 onboarding，本 lab 未達 |
| 11 | SDDC Manager `POST /v1/tokens` → Bearer；無 token 401 | 200 / 401 |
| 12 | SDK（vcf-sdk 9.1.0.0）只支援 Python 3.10–3.14 → 3.8 環境走純 REST | 官方 README |
| 13 | <a name="log-insight"></a>Log Insight `/api/v1/*` → Log Management `/api/v2/logs/search` | **未實測**（lab 未部署 Operations for Logs） |
| 14 | <a name="vrlcm"></a>vRLCM `/lcm/lcops/api/*` 已移除 → SDDC Manager `/v1/*` / Fleet LCM | SDDC Manager 上該路徑 401（無此服務） |

## 不要過度遷移

規則 3、5 的意思是：**能跑的不要為了「新」而改**。scanner 只標會壞的（`break`）和已棄用的（`deprecated`）；
沒被標的就放著。改越少，客戶審 diff 越快。

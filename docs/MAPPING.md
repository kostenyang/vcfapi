# 對照表 — 兩份 Excel → 本 repo 範例

把 `IaaS API Summary 24 repo - VCF9 Analysis 3.xlsx` 與
兩份 API 遷移盤點文件的結論，落到每一支範例程式。

## 1. 302 API 基線分類 (盤點文件 · 分頁 8)

| 分類 | 筆數 | 優先級 | 本 repo 處理方式 |
|------|------|--------|------------------|
| Unchanged (可沿用) | 151 | P2 測試/升級 | 邏輯沿用，示範改用 REST 或保留 pyVmomi (`vcenter/`) |
| Rewrite-Different (部分改寫) | 80 | P1 adapter | 端點/認證改寫 (`vcf_operations/`, `log_management/`, `sddc_manager/`, `vcf_automation/`) |
| Rewrite-Removed (重寫/退役) | 2 | P0 | vRA 7 catalog/identity API 已 Sunset，改 VCF Automation REST |
| Customer-Own (客戶自有) | 69 | P3 | wrapper 本身不重寫，只需檢查後端 VMware call |

## 2. 遷移策略 → 範例 (Analysis 3 · 遷移策略比較)

| 功能群 | 筆數 | 建議 | 範例 |
|--------|------|------|------|
| VM 電源管理 | 19 | REST | `vcenter/03_vm_power_rest.py` |
| VM Snapshot | 6 | REST | `vcenter/04_vm_snapshot_rest.py` |
| Tagging / Association | 10 | REST | `vcenter/05_tagging_rest.py` |
| VM 清單/查詢 | — | REST | `vcenter/02_vm_inventory_rest.py` |
| VM Clone / Relocate | 8 | 混合 | `vcenter/06_vm_clone_pyvmomi.py` |
| DVS / vSwitch | 13 | 沿用 SDK | `vcenter/07_dvs_inventory_pyvmomi.py` |
| NSX DFW (Policy API) | 90 | REST | `nsx/01_dfw_policy_api.py` |
| NSX 內部 wrapper | 9 | 不可行 | 改直連 Policy API (見上) |
| VCF Operations (vROps) | 33 | REST | `vcf_operations/01_adapters_and_reports.py` |
| Log Management (Log Insight) | 32 | REST | `log_management/01_search_and_forwarders.py` |
| SDDC Lifecycle (vRLCM) | 11 | REST | `sddc_manager/01_credentials_licenses_tasks.py` |
| vRA 8 / VCF Automation | 87 | 需注意 | `vcf_automation/01_iaas_catalog.py` |

## 3. 升級改寫對照表 (Analysis 3) — 端點對應

### vROps → VCF Operations
| 舊 (`/suite-api/api/`) | 新 (`/api/`) | 變更 |
|------|------|------|
| `POST /suite-api/api/auth/token/acquire` | `POST /api/auth/token/acquire` | header `vRealizeOpsToken`→`OpsToken` |
| `GET/POST/PATCH /suite-api/api/adapters` | `GET/POST/PATCH /api/adapters` | base path 調整 |
| `GET /suite-api/api/resources` | `GET /api/resources` | 新增 `POST /api/resources/query` |
| `POST /suite-api/api/reports` | `POST /api/reports` | schema 相同 |

> ⚠️ **實測修正 (home.lab VCF Operations 9.1, 2026-06-26)**:此 build **仍服務
> `/suite-api/api/`,並未改成 `/api/`**;`OpsToken` 與舊 `vRealizeOpsToken` header
> 皆可用。上表的 `/api/` 是依文件的推論,實際以該 release 為準。程式碼採已驗證的
> `/suite-api/api/`。

### Log Insight → VCF Log Management
| 舊 | 新 | 變更 |
|------|------|------|
| `POST /api/v1\|v2/sessions` | (移除) → VCF Operations `token/acquire` + `token/exchange` (`ops-li`) | 改 JWT，X-JWT-Token |
| `GET /events?<params>` | `POST /v2/logs/search` (JSON body) | 結構化查詢；`/v2/search` 已 Deprecated |
| `PUT /api/v2/notification/email` | `POST /v2/logs/forwarders` | 改 Log Forwarder |
| `GET/POST /alerts` | VCF Operations `GET/POST /api/alerts/` | 告警統一到 Operations |

### vRLCM → SDDC Lifecycle + SDDC Manager
| 舊 (`/lcm/`) | 新 | 變更 |
|------|------|------|
| `…/locker/passwords` | `GET/PATCH /v1/credentials` | Password Locker → Credentials |
| `…/locker/licenses` | `GET/POST /v1/license-keys` | License Locker → License Keys |
| `…/locker/certificates` | `/v1/domains/{id}/resource-certificates` | 與 domain 綁定 |
| `…/v2/environments` | `GET /sddc-lcm/v1/components` | environments → components |
| `…/request/api/v2/requests/{id}` | `GET /sddc-lcm/v1/tasks/{id}` | request → task |
| `…/v2/health` | `GET /sddc-lcm/v1/health` | 直接對應 |

## 4. 統一 SDK / 認證 (盤點文件 · 分頁 2,3)

| 用途 | 舊 (vSphere 7/8) | 新 (VCF 9.1) | 範例 |
|------|------------------|--------------|------|
| 安裝 | `pip install pyvmomi` + vsphere-automation + vsan | `pip install vcf-sdk` | `requirements.txt` |
| SOAP | `from pyVim.connect import SmartConnect` | 同 (隨 vcf-sdk 提供) | `common/auth.pyvmomi_connect` |
| REST/vAPI | `from vmware.vapi.vsphere.client import create_vsphere_client` | 同 (套件來源改變) | `common/auth.vsphere_automation_client` |
| SDDC Manager | (無) | `from vmware.vapi.sddc_manager.client import create_sddc_manager_client` | `common/auth.sddc_manager_client` |
| 認證 | SOAP/REST 各自登入 | 單次登入 session 共用 | `common/auth.py` |

## 5. 實機驗證發現 (home.lab VCF 9.1, 2026-06-26)

對真實 VCF 9.1 跑過後,以下與 Excel 推論不同,程式已依實機修正:

| 項目 | Excel 推論 | 實機 (9.1) | 程式處理 |
|------|-----------|-----------|----------|
| VCF Operations base | `/suite-api/api/`→`/api/` | 仍為 `/suite-api/api/`;`OpsToken`/`vRealizeOpsToken` 皆可 | 用 `/suite-api/api/` |
| vCenter Tagging body | (沿用) | `/api/` 不再包 `{"create_spec":...}` | 欄位直接放 body |
| vCenter Snapshot | 改用 REST | REST `/api/vcenter/vm/{id}/snapshots` → 404 | 改用 **VCF 9 SDK** (`vcf-sdk` 內含 pyVmomi);已實測 create/list/delete |
| VCF Automation 登入 | 認證需確認 | vRA8 `/iaas/api/login` 回 invalid_grant;VCFA 9 改 OAuth `/oauth/provider/token` 或 `/oauth/tenant/<org>/token`(form `grant_type=refresh_token`);多租戶(provider vs tenant);`/cloudapi/` 需版本化 Accept `application/json;version=9.1.0`;須走 FQDN | 用 OAuth token flow + org 切換 |
| pyVmomi 執行環境 | Python ≥3.10 | 確認:pyVmomi 9.x 拒絕 3.9 | 文件標註需 3.10+ |

## 官方依據 (節錄)

- vcf-sdk-python: https://github.com/vmware/vcf-sdk-python
- Unified VCF SDK 9.0 (Python 3.9–3.13, OpenSSL 3.0+): https://blogs.vmware.com/cloud-foundation/2025/06/24/introducing-a-unified-vcf-sdk-9-0-for-python-and-java/
- Unified Authentication in VCF SDK 9.0: https://blogs.vmware.com/cloud-foundation/2025/11/19/unified-authentication-in-vmware-cloud-foundation-sdk-9-0-seamless-authentication-across-vsphere-and-vsan-apis/
- VCF 9.1 Programmable Infrastructure (Python 3.10–3.14): https://blogs.vmware.com/cloud-foundation/2026/05/25/unlocking-the-full-potential-of-programmable-infrastructure-with-vmware-cloud-foundation-9-1-new-features-and-capabilities/
- vSphere Automation API: https://developer.broadcom.com/xapis/vsphere-automation-api/latest/
- NSX Policy API: https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/

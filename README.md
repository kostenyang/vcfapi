# vcfapi — VCF 9.1 API 範例 + 舊 API 差異

VMware Cloud Foundation (VCF) **9.1** 的 API / SDK 範例程式碼，示範從
**Python 3.8 + vSphere 8 + vRA 8**（及 VCF 5.2.1 / vROps / Log Insight / vRLCM / NSX）
的 IaaS 自動化改寫到 **VCF 9.1 + VCF Automation (VCFA)**。每一支範例都對真實
VCF 9.1 實測，並以註解標出「舊 API」與「VCF 9.1 新做法」。

> Sample code for the **new VCF 9.1 API**, designed to be tested against a live lab.

## API vs SDK 對照表

每個操作的 **API（REST）** 與 **SDK（vcf-sdk）** 兩種做法對照，含對應的 `samples/` 範例檔，見 [`docs/VCF9_API_vs_SDK_對照表_v1.xlsx`](docs/VCF9_API_vs_SDK_對照表_v1.xlsx)。範例程式全部集中在 **`samples/`** 資料夾。

## 舊 API vs VCF 9 差異總表

各產品（vSphere 8 / VCF 5.2.1 / Aria Automation 8 / vROps / Log Insight / vRLCM /
NSX / vSAN）的舊 API 對 VCF 9 差異，整理在
[`docs/VCF9_API_差異總表_v1.1.xlsx`](docs/VCF9_API_差異總表_v1.1.xlsx)（5 分頁：產品差異總覽、
端點對照、SDK 套件對照、認證對照、live 實測+來源）。

## 來源文件 (Source of truth)

| 文件 | 內容 | 本 repo 如何使用 |
|------|------|------------------|
| `IaaS API Summary 24 repo - VCF9 Analysis 3.xlsx` | 544 端點分析、遷移策略 (REST vs SDK vs CLI)、vROps/Log Insight/vRLCM 升級改寫對照表 | 決定每個 bucket 用 REST 還是保留 pyVmomi；端點路徑對應 |
| `客戶 API 遷移盤點文件` | 302 支 API 基線分類 (Unchanged 151 / Rewrite-Different 80 / Rewrite-Removed 2 / Customer-Own 69)、統一 `vcf-sdk`、Python 版本矩陣 | 認證/連線方式 (`common/auth.py`)、安裝與執行環境需求 |

完整對照見 [`docs/MAPPING.md`](docs/MAPPING.md)。

## 核心觀念 (來自文件結論)

1. **統一 SDK** — 原本分開安裝的 `pyVmomi`、vSphere Automation SDK、vSAN SDK，
   自 VCF 9 起整併為單一套件 `pip install vcf-sdk`。單次登入，session 共用於
   SOAP / REST / vSAN。
2. **REST 優先** — vCenter 的電源、快照、Tag、Content Library、CPU/Mem 調整等
   建議改用 vSphere REST API；DVS 進階、AlarmManager、CustomSpecManager、vSAN
   完整健康診斷則保留 pyVmomi (混合策略)。
3. **Operations 家族路徑重構** — vROps → **VCF Operations** (`/suite-api/api/`→`/api/`、
   `OpsToken`)；Log Insight → **VCF Log Management** (JWT 交換、`POST /v2/logs/search`)；
   vRLCM → **SDDC Lifecycle + SDDC Manager** (`/lcm/`→`/sddc-lcm/v1/`、Locker→Credentials)。
4. **Python ≥ 3.10** (VCF 9.1)、**OpenSSL 3.0+**；hard-coded endpoint / token / cert
   一律外部化 (本 repo 用 `config/lab.yaml` + 環境變數)。

## 目錄結構

```
vcfapi/
├── common/                 共用：設定載入 + 統一認證
│   ├── config.py           讀取 config/lab.yaml + 環境變數覆寫
│   └── auth.py             vCenter / SDDC / NSX / Operations / Log / Automation 連線
├── config/
│   └── lab.example.yaml    連線設定範本 (複製成 lab.yaml 後填入)
├── vcenter/                vSphere/vCenter (151 Unchanged + REST 優先)
│   ├── 01_connect_unified_sdk.py    統一 vcf-sdk 三種存取方式
│   ├── 02_vm_inventory_rest.py      VM/Host/Cluster 清單 (REST)
│   ├── 03_vm_power_rest.py          電源管理 (REST)
│   ├── 04_vm_snapshot_rest.py       快照 CRUD (REST)
│   ├── 05_tagging_rest.py           Tag/Category/Association (REST)
│   ├── 06_vm_clone_pyvmomi.py       Clone (混合策略，保留 pyVmomi)
│   └── 07_dvs_inventory_pyvmomi.py  DVS (沿用 SDK)
├── vcf_operations/         vROps → VCF Operations
├── log_management/         Log Insight → VCF Log Management
├── sddc_manager/           vRLCM → SDDC Lifecycle + SDDC Manager
├── vcf_automation/         vRA 8 / Aria → VCF Automation
├── nsx/                    NSX-T → NSX 9 Policy API
├── esxcli/                 ESXi 主機層 esxcli (Ansible，第三條路：REST/SDK 皆無對應)
├── examples/               login_example.py — VCF 9.1 統一登入示範
├── migration/              改寫範例：舊做法(已移除) → 新做法
├── tools/                  test_inventory.py — 逐筆測舊 API 清單對 9.1 可用性
├── smoke_test.py           對 homelab 做連線健檢
└── requirements.txt
```

> `tools/test_inventory.py <inventory.xlsx>` — 讀一份舊 API 清單（欄位 Service /
> Category / Method / API Endpoint / Purpose），對 config 裡的 VCF 9.1 逐筆判定
> 「可用 / 已移除 / 需更換 / CLI」並輸出結果 Excel（pyVmomi binding 檢查 + live 探測）。

## 安裝

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 跑 SDK 範例 (pyVmomi / vSphere Automation / SDDC Manager) 時再加裝：
# pip install vcf-sdk
```

> Python 3.11 或 3.12 建議 (同時受 VCF 9.0/9.1 支援)。3.8 不再受支援。

### 客戶還在 Python 3.8?(升 / 不升 都能連 9.1)

**不用升也能用 VCF 9.1 —— 走 REST 即可。** 實測:Python **3.8.20** + 只裝
`requests`/`PyYAML`,`smoke_test.py` = **4/4**(vCenter/NSX/Operations/SDDC)。

```bash
# Path A(不升,維持 3.8):REST-only,所有 *_rest.py 可跑
python3.8 -m venv .venv && . .venv/bin/activate
pip install -r requirements-rest.txt        # 只有 requests + PyYAML,無 vcf-sdk
```
SOAP-only 操作(snapshot/DVS)在 3.8 上維持既有 **pyVmomi 7.0**(9.1 vCenter 仍支援
7.0.x SOAP,向後相容,屬末期支援)。

```bash
# Path B(升 ≥3.10):REST + SDK 全部
pip install -r requirements.txt             # 含 vcf-sdk;snapshot/clone/dvs/*_sdk.py 可跑
```
完整對策(怎麼做、限制、建議)見 [`docs/PYTHON_38_STRATEGY.md`](docs/PYTHON_38_STRATEGY.md)。

## 設定 (連 homelab)

預設指向 **rtolab** 的 VCF 9.1 (見 [kostenyang/lab-info](https://github.com/kostenyang/lab-info))。

```bash
cp config/lab.example.yaml config/lab.yaml   # lab.yaml 已被 .gitignore
# 編輯 config/lab.yaml 填入端點與密碼，或用環境變數覆寫：
export VCF_VCENTER_HOST=192.168.114.11
export VCF_PASSWORD='VMware1!VMware1!'
```

| 元件 | rtolab VCF 9.1 | FQDN |
|------|----------------|------|
| inner vCenter | 192.168.114.11 | kosten-vcf91-vc.rtolab.local |
| SDDC Manager | 192.168.114.10 | kosten-vcf91-sddc.rtolab.local |
| NSX Manager VIP | 192.168.114.13 | kosten-vcf91-nsx.rtolab.local |
| VCF Operations | 192.168.114.75 | kosten-vcf91-ops.rtolab.local |
| VCF Automation VIP | 192.168.114.87 | kosten-vcf91-vcfa-platform.rtolab.local |

> 自動化主機 (172.16.10.32) 是 Windows Server 2022，請用 `pwsh`/Python 3。
> 另一個 lab `vcf9.1-lab` (domain `lab.com`) 的對應值見 lab.example.yaml 註解。

## 執行

```bash
# 1) 先做連線健檢
python smoke_test.py
python smoke_test.py vcenter            # 只測一個元件

# 2) 跑個別範例
python samples/vcenter/02_vm_inventory_rest.py
python samples/vcenter/03_vm_power_rest.py my-vm state
python samples/vcf_operations/01_adapters_and_reports.py
python samples/sddc_manager/01_credentials_licenses_tasks.py
python samples/nsx/01_dfw_policy_api.py
```

## 實測結果 (against real VCF 9.1)

對 home lab 的 **VCF 9.1 (home.lab, m02 instance)** 實際跑過 `smoke_test.py` + 範例
(2026-06-26),回傳真實資料:

| 元件 | 結果 | 實測重點 / 與文件差異 |
|------|------|----------------------|
| vCenter (REST) | ✅ | 9.1.0.0;1 cluster / 4 ESXi / 12 VM,`POST /api/session` 正常 |
| SDDC Manager | ✅ | 1 workload domain、16 筆 managed credentials(Bearer token) |
| NSX (Policy API) | ✅ | 258 個 DFW group,basic auth + `/policy/api/v1/infra/` |
| VCF Operations | ✅ | OpsToken 認證、20 個 adapter。**注意**:此 build 仍走 `/suite-api/api/`,**並未**如文件假設改成 `/api/`;`OpsToken` 與舊 `vRealizeOpsToken` header 都收 |
| Log Management | ⚠️ | token/exchange 端點存在但回 `Invalid service keys: ops-li` → 此 instance 未部署 Log Management(環境因素,非程式問題) |
| VCF Automation | ✅ | OAuth token flow:`/oauth/provider/token`(或 `/oauth/tenant/<org>/token`)`grant_type=refresh_token`。實測列出 2 orgs(`lab-vmapps` tenant + `System`)。多租戶:`/iaas/api/` 需 tenant token;`/cloudapi/` 需版本化 Accept。須走 FQDN |

**vCenter 進階範例實測(8→9 重要差異):**

| 範例 | 結果 | 8→9 發現 |
|------|------|----------|
| Tagging (`05_tagging_rest.py`) | ✅ 實測通過 | 新 `/api/` JSON REST **不再包 `create_spec`**,欄位直接放 body(舊 `/rest/` 會包)。已建 category+tag 並掛到 VM 驗證 |
| Snapshot (`04_vm_snapshot_rest.py`) | ✅ 用 vcf-sdk 實測 | vSphere 9.1 REST **沒有** `/api/vcenter/vm/{id}/snapshots`(404)→ 快照走 **VCF 9 SDK (`vcf-sdk`)** 內含的 pyVmomi。已 create→list→delete 全程實測 |
| 統一 SDK 連線 (`01_connect_unified_sdk.py`) | ✅ 用 vcf-sdk 實測 | 一次安裝 `vcf-sdk`、一組帳密,REST + SOAP(pyVmomi)+ vAPI 三種存取全通(文件核心論點實證) |
| Clone / DVS (`06`,`07`) | ✅ 用 vcf-sdk 實測 | DVS inventory 實測通過;clone 連線/邏輯驗證。`vcf-sdk` 需 Python ≥3.10(本驗證用 3.12)— 正好印證 8→9 必須升 Python |

> 上述 SDK 範例以 `pip install vcf-sdk`(9.1.0.0,內含 `vmware-vcenter` / pyVmomi /
> vAPI / `vmware-sddc-manager` / vSAN 綁定)在 Python 3.12 實機驗證,**不是**單獨的
> `pyvmomi`。

> 教訓:**端點/認證務必對真實環境驗證**,Excel 的升級對照是依據官方文件的推論,
> 個別 build 可能不同 — 實測已抓到三處:VCF Operations base path 未改、tagging
> 去 `create_spec`、snapshot 無 REST、VCFA 改 API token。

## REST vs SDK 雙版本 (每個操作兩種寫法)

每個關鍵操作都提供 **REST 版**(只需 `requests`)與 **SDK 版**(`vcf-sdk`,Python ≥3.10),
讓客戶在 8→9 時直接比較兩種寫法、按操作選擇。全部已對 home.lab VCF 9.1 (m02) 實測。

| 操作 | REST 版 | SDK 版 (`vcf-sdk`) | 實測 |
|------|---------|-------------------|------|
| vCenter 連線 | `01_connect_unified_sdk.py`(同檔含 REST+SOAP+vAPI) | 同左 | ✅ |
| VM inventory | `samples/vcenter/02_vm_inventory_rest.py` | `samples/vcenter/08_vm_inventory_sdk.py` | ✅ |
| VM power | `samples/vcenter/03_vm_power_rest.py` | `samples/vcenter/09_vm_power_sdk.py` | ✅ |
| Tagging | `samples/vcenter/05_tagging_rest.py` | `samples/vcenter/10_tagging_sdk.py` | ✅ |
| VM snapshot | (REST 無此端點,404) | `samples/vcenter/04_vm_snapshot_rest.py`(pyVmomi) | ✅ |
| VM clone | (REST 部分覆蓋) | `samples/vcenter/06_vm_clone_pyvmomi.py` | ⏸️ |
| DVS inventory | (REST 覆蓋有限) | `samples/vcenter/07_dvs_inventory_pyvmomi.py` | ✅ |
| SDDC Manager | `samples/sddc_manager/01_credentials_licenses_tasks.py` | `samples/sddc_manager/02_credentials_licenses_sdk.py` | ✅ |
| VCF Operations | `samples/vcf_operations/01_adapters_and_reports.py` | `samples/vcf_operations/02_adapters_sdk.py` | ✅ |
| NSX DFW | `samples/nsx/01_dfw_policy_api.py` | `samples/nsx/02_dfw_policy_sdk.py` | ✅ |
| VCF Automation | `samples/vcf_automation/01_iaas_catalog.py` | (不在 vcf-sdk,REST only) | ✅ provider+tenant |
| Log Management | `samples/log_management/01_search_and_forwarders.py` | (整合於 Operations) | ⚠️ 未部署 |
| ESXi host esxcli | `samples/esxcli/configure_esxi_host.yml`(Ansible，第三條路) | — | CLI/Ansible |

跑法:REST 版用 `.venv`(requests/PyYAML);SDK 版用 Python ≥3.10 + `pip install vcf-sdk`。
連線健檢:`python smoke_test.py`(REST)、`python smoke_test_sdk.py`(SDK)。

## 對照官方 SDK 範例 (cross-checked)

本 repo 已對照 Broadcom 官方 **VCF SDK for Python 9.1.0.0 樣本**
(`vcf-sdk-python-samples-9.1.0.0`,Apache-2.0)交叉驗證。官方樣本分五大區
(非本 repo 內容,屬權威參考):

| 區域 | 官方樣本數 | 對應本 repo |
|------|-----------|-------------|
| vsphere-samples | 380 | `samples/vcenter/`(REST + pyVmomi) |
| vcf-operations-samples | 65 | `samples/vcf_operations/`、`samples/log_management/` |
| vcf-installer-samples | 28 | (本 repo 未涵蓋) |
| sddc-manager-samples | 20 | `samples/sddc_manager/` |
| nsx-samples | 9 | `samples/nsx/` |

交叉驗證重點:
- **Snapshot 用 pyVmomi 是對的** — 官方 `samples/vcenter/compute/vm/snapshot_operations.py`
  也是 `pyVmomi` + `CreateSnapshot_Task`(SOAP),非 REST,印證本 repo `04`。
- **VCF Automation 不在此 SDK** — 官方樣本完全沒有 vra/iaas/automation 區;VCFA 是
  獨立 REST API(自有 token 認證),所以本 repo `samples/vcf_automation/` 用 REST 是唯一途徑。
- vSphere/SDDC 的 SDK client 工廠(`create_vsphere_client`/`create_sddc_manager_client`)
  與官方一致;VCF Operations 官方用 `create_vcf_operations_client`,本 repo 用等效的
  `/suite-api/api/` REST(兩者皆可)。
- SDK 相容性:pyVmomi/vCenter **8.0 + 9.0 + 9.1** 同一套 — 對「8 轉 9」極友善。

## 注意事項

- 範例以「可讀、可對照」為主；正式環境請依 Broadcom Developer Portal / TechDocs
  官方最新 spec 再確認端點與欄位 (尤其 VCF Automation 的認證端點)。
- TLS：nested lab 用 self-signed，`config/lab.yaml` 預設 `verify_tls: false`；
  正式環境請設 `true` 並指定 `ca_bundle`。
- **本 repo 不存放任何真實密碼**；`config/lab.yaml` 與 `.env` 已被忽略。

---
版本 v1.0.0 · 對應 VCF SDK 9.1.0.0 · 2026-06

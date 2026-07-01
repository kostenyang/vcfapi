# Python 3.8 對策 — 升 / 不升 都能連 VCF 9.1

客戶現況是 **Python 3.8 + pyVmomi 7.0**。VCF 9.1 的統一 SDK（`vcf-sdk`）與
pyVmomi 9.x **需要 Python ≥ 3.10**，所以「要不要升 Python」是個決策點。
兩條路都可行,且都已對真實 VCF 9.1 實機驗證。

> **關鍵結論:不升 Python 也能用 VCF 9.1** —— 只要走 REST。
> 實測:Python **3.8.20** + 只裝 `requests`/`PyYAML`,`smoke_test.py` = **4/4**
> （vCenter 9.1.0.0 / NSX 258 群組 / VCF Operations 20 adapters / SDDC 1 domain）。

---

## Path A — 不升（維持 Python 3.8）

**核心策略:REST-first。** 所有有 REST 端點的操作改用純 HTTP（`requests`），
完全不裝 `vcf-sdk`。

**怎麼做**
```bash
python3.8 -m venv .venv
. .venv/bin/activate
pip install -r requirements-rest.txt      # 只有 requests + PyYAML
python smoke_test.py                       # vCenter/NSX/Operations/SDDC/VCFA 全走 REST
python vcenter/02_vm_inventory_rest.py
```

**涵蓋範圍（3.8 可用,全部實測過）**
- vCenter:`/api/session`、VM/Host/Cluster 清單、電源、Tagging
- NSX 9:Policy API `/policy/api/v1/infra/`
- SDDC Manager:`/v1/...`
- VCF Operations:`/suite-api/api/`（OpsToken）
- VCF Automation:OAuth `/oauth/provider|tenant/token`

**SOAP-only 操作（snapshot / DVS 進階 / CustomSpec 等,REST 無對應）**
- 維持既有 **pyVmomi 7.0**（3.8 可用），對 vCenter 9.1 以「版本協商 SOAP」連線。
- 9.1 vCenter 仍宣告支援舊版 SOAP（實測 `vimServiceVersions.xml` 含 8.0.x / **7.0.x**），
  所以舊 client 連得上 —— 但屬**末期支援**,部分新功能拿不到。

**不能用:** `vcf-sdk`、pyVmomi 9.x（皆需 ≥3.10）。

**限制 / 風險:** pyVmomi 7.0 EOL、無原廠支援;部分 9.1 新綁定/功能缺;
執行環境仍需 **OpenSSL 3.0+**;長期仍建議升。

**適用:** 短期過渡、無法立即升 Python 的主機 —— 先讓自動化「在 9.1 上能動」。

---

## Path B — 升級（Python 3.11 / 3.12）

**怎麼做（不要動系統 3.8,OS 依賴它）—— 用獨立 runtime:**
```bash
# 任一方式取得新版 Python(不覆蓋系統 3.8):
#   uv venv --python 3.12 .venv-sdk          # 本專案實測用法
#   或 pyenv install 3.12 / 官方 installer / 容器映像 python:3.12
. .venv-sdk/bin/activate
pip install -r requirements.txt              # 含 vcf-sdk (9.1.0.0)
python smoke_test_sdk.py                      # SDK client 連線健檢
python vcenter/08_vm_inventory_sdk.py
```

**涵蓋範圍:** 全部 —— REST 版 + SDK 版;SOAP-only（snapshot/DVS）走
`vcf-sdk` 內含的 **pyVmomi 9.x**（原廠支援、功能完整）。

**策略:** 新舊並行 runtime + adapter layer,分階段切換;新 VCF adapter 採新
Python/SDK,舊腳本逐步遷移（與基線盤點文件建議一致）。

**風險 / 注意:** 需逐台升 runtime / 映像 + 回歸測試;SDK 走 **SAML STS**,
高頻登入易被 SSO 暫鎖（大量自動化建議改用 REST session）。

**適用:** 中長期正式路線、需原廠支援與完整 9.1 能力。

---

## 建議:兩段式

1. **先 Path A** —— 用 REST 讓自動化在 VCF 9.1 上跑起來。風險低、不卡 Python 升級窗口,
   涵蓋絕大多數操作(302 支裡多數是 vCenter/NSX/Ops,都有 REST)。
2. **再 Path B** —— 逐台升 3.11/3.12 + `vcf-sdk`,把 SOAP-only 與需原廠支援的部分
   收斂到支援路線。

> Customer-Own wrapper（69 支）不直接呼叫 VMware API,不受 Python 版本影響。

| | Path A（不升 3.8） | Path B（升 ≥3.10） |
|---|---|---|
| 安裝 | `requirements-rest.txt`（requests/PyYAML） | `requirements.txt`（+ `vcf-sdk`） |
| REST 範例 `*_rest.py` | ✅ | ✅ |
| SDK 範例 `*_sdk.py` / snapshot / DVS | ❌（改用舊 pyVmomi 7.0 SOAP） | ✅ |
| 原廠支援 | 末期 | ✅ |
| 實測 | Python 3.8.20 smoke 4/4 | Python 3.12 + vcf-sdk 全通 |

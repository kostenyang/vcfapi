# migration — 舊做法已移除 → 新做法（改寫範例）

針對在 VCF 9.1 **已移除 / 已改變、不能直接沿用**的舊 API,每支範例標出
「舊做法(已移除)→ 新做法」,並以可執行程式示範新做法。全部對 VCF 9.1 實測。

| 範例 | 舊做法（已移除/已變） | 新做法 | API/SDK |
|------|----------------------|--------|---------|
| `01_loginsight_to_operations.py` | Log Insight `POST /api/v2/sessions`(404 移除) | VCF Operations OpsToken;告警 `/suite-api/api/alerts`;查詢 exchange→`/v2/logs/search` | API（SDK: vcf.operations） |
| `02_vrlcm_to_sddc_manager.py` | vRLCM `/lcm/`(產品下架) | SDDC Manager `/v1/credentials`·`/v1/license-keys`·`/v1/domains` | API（SDK: vmware.sddc_manager_client） |
| `03_vra_to_vcf_automation.py` | vRA7 catalog/identity(Sunset)、vRA8 `/iaas/api/login`(invalid_grant) | OAuth `/oauth/provider\|tenant/<org>/token` + `/cloudapi/`·`/iaas/api/` | API only（不在 vcf-sdk） |
| `04_nsx_wrapper_to_policy.py` | 客戶內部 wrapper `/api/v1/vmware/nsx-t/`(非官方) | NSX Policy API `/policy/api/v1/infra/` | API（SDK: vcf.nsx.policy） |

> 對應的 SDK 版寫法見 `sddc_manager/02_*_sdk.py`、`nsx/02_*_sdk.py`、`vcf_operations/02_*_sdk.py`。
> 可沿用(未移除)的舊 API（vCenter pyVmomi、vROps `/suite-api/api/` 等）不在此資料夾。

```bash
cp config/lab.example.yaml config/lab.yaml   # 填入端點/帳密/VCFA token
python migration/02_vrlcm_to_sddc_manager.py
```

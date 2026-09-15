# AGENTS.md — 給任何 AI coding agent 的工作說明

你在一個「vSphere 8 / vRA 8 / vROps / NSX-T 舊程式 → VMware Cloud Foundation 9.1」的遷移 repo 裡。
這份檔案不綁定任何一家模型或工具；Claude Code 讀 `CLAUDE.md`（指到這裡），Codex / Cursor / 內部 LLM 直接讀本檔。

## 目標（機器可判定）

`python tools/verify.py` 印出 `VERIFY: PASS`：
1. `tools/scan_legacy.py` 掃 `legacy_app/` 是 **0 hits**（沒有舊寫法）
2. `pytest tests/` **全綠**（用 lab 錄好的 cassette 離線回放，不需要帳密）

兩個條件缺一不可：測試綠只代表「沒壞」，scanner 0 才代表「遷完」。

## 你可以做 / 不可以做

- 只改 `legacy_app/` 下的檔案。`tests/`、`tools/`、`data/`、`docs/` 唯讀。
- 不要為了讓測試過而改測試或 cassette。
- 不要把任何帳密、token、IP 寫進程式；憑證一律用參數或環境變數。
- 不要連真實環境（`--live` 只有人會跑）。
- 不要引入新的第三方套件；`requests` 是唯一依賴。目標執行環境是 **Python 3.8**，不能用 vcf-sdk（它要 3.10+）。

## 怎麼做（每條舊呼叫都走同一個迴圈）

1. `python tools/scan_legacy.py` — 看哪些行被標出來、屬於哪個 pattern、對應哪份 playbook。
2. 讀對應的 `docs/playbooks/*.md` — 那裡有「判斷樹 + before/after」。
3. 不確定新端點長什麼樣：`python tools/lookup.py "<關鍵字>"`（查逐條對照表）或
   `python tools/lookup.py --catalog "<路徑片段>"`（查 VCF 9.1 全部 9,768 條 API）。
4. 改一個檔案 → `python tools/verify.py` → 綠了才碰下一個檔。
5. 全部 PASS 後，用 `python tools/progress.py` 產一份 JSON 摘要放進你的回報。

## 十條規則（完整版在 docs/rules.md，每條都有 lab 實測依據）

1. vSphere `/rest/` facade 在 9.1 仍可用但 deprecated → 改 `/api/`；回應少一層 `{"value": ...}`。
2. `/api/session` 回 **201** 且 body 是裸字串 session id。
3. vROps `Authorization: vRealizeOpsToken` 在 9.1 相容，但改成 `OpsToken`；base 仍是 `/suite-api`。
4. NSX MP `/api/v1/transport-zones`、`/api/v1/node` 等在 9.1 **仍 200，不要動**。
5. NSX `/api/v1/logical-switches`、`logical-routers`、`firewall/sections`、`ns-groups` 在 9.1 **404** → 走 `/policy/api/v1/infra/...`。Policy 的 list 回 `{"results": [...], "result_count": n}`。
6. vRA 8 `/csp/gateway/am/api/login` 在 VCFA 9 **404**（唯一硬斷點）→ `POST /cloudapi/1.0.0/sessions`（Basic `user@org:pw`，token 在回應標頭 `X-VMWARE-VCLOUD-ACCESS-TOKEN`）。登入函式要多一個 `org` 參數。
7. VCFA `/deployment`、`/catalog`、`/blueprint` 用租戶 Bearer token 直接可用；`/iaas/api/*` 另需 Cloud Assembly 權限 + org onboarding（沒有就 403）。
8. SDDC Manager：`POST /v1/tokens` → `accessToken`（Bearer）。vRLCM `/lcm/lcops/` 已移除，改 SDDC Manager `/v1/*`。
9. Log Insight `/api/v1/events|sessions` 已移除，改 Log Management `/api/v2/logs/search`（本 kit 未實測，無 cassette）。
10. 保留原函式簽章與回傳型別（list / str），呼叫端不用改；需要新參數時用 keyword 且給預設值。

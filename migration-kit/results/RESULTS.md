# 實測結果 — 兩個模型各跑一份 kit 複本（2026-09-14）

環境：Claude Code subagent，只給 `AGENTS.md` 與 Python 3.8 interpreter；不給 lab、不給網路；目標「讓 `tools/verify.py` 回 PASS，只改 legacy_app/」。
起點：scanner 9 hits（3 break / 6 deprecated）、pytest 4 failed / 7 passed。

| 模型 | 結果 | verify 次數 | 工具呼叫 | 耗時 | tokens | 改動檔 | 越界改動 |
|---|---|---|---|---|---|---|---|
| Haiku 4.5（簡單模型） | **PASS**（0 hits / 11 passed） | 2 | 24 | 102 s | 68k | 4 | 無 |
| Sonnet 5（對照） | **PASS**（0 hits / 11 passed） | 2 | 18 | 119 s | 95k | 4 | 無 |

兩者的最終程式碼**功能上相同**（只差 docstring 措辭與換行，見 `diff_*.patch`）；都把 NSX MP `transport-zones` 留著沒動（不過度遷移），
都用 keyword + 預設值加 `org` 參數保住舊呼叫端，都從回應標頭取 VCFA token。
獨立用 Python 3.12 重跑 verify 也 PASS。

## 它們回報「不清楚」的地方
- `org` 的預設值 playbook 沒指定（兩者都選 `"System"`）→ 已補進 playbook 建議寫法。
- 其餘規則、路徑、回應形狀都說「playbook 與 cassette 直接對得上，不用猜」。

## 這個實測能證明什麼、不能證明什麼
- **能**：四層設計（知識 / 指令 / 驗證 / 工具）讓一個小模型在 2 輪內完成正確遷移，且沒有越界、沒有過度遷移。
- **不能**：這是 4 個檔 / 9 條 pattern 的合成樣本，playbook 例子與目標高度相似；544 條真實碼會有 playbook 沒覆蓋的變體，
  要靠 `lookup.py` 與更多 cassette。也**沒有**用內部 LLM 實跑 `agent_loop.py`（本機無 endpoint），那條路只做到語法檢查。

---

# 第二階段：小模型 / 內部 LLM 實測（2026-09-15）

用 kit 自帶的 `tools/agent_loop.py` 接 **Ollama 的 OpenAI-compatible `/v1` 端點**，不經任何 Claude API。
每輪都從乾淨的 kit 複本開始；起點同樣是 scanner 9 hits（3 break / 6 deprecated）、pytest 4 failed / 7 passed。
`--max-steps` 為步數上限；「verify」= 呼叫 `tools/verify.py` 的次數。

## 環境

| 環境 | 硬體 | qwen2.5 7B/14B 速度 |
|---|---|---|
| lab `ollama-14b` VM | 12 vCPU / 32 GB，無 GPU | 14b：prompt 1.5 tok/s、生成 **0.21 tok/s** — 一步可達一小時，不可用 |
| 本機 MacBook Air M4 / 24 GB | Apple Silicon | 7b：prompt 91 tok/s、生成 22 tok/s |

## 結果總表

| 模型 | 環境 | 迴圈版本 | 結果 | hits 9→ | tests 4紅→ | 步數 / verify | 耗時 | 觀察 |
|---|---|---|---|---|---|---|---|---|
| Haiku 4.5 | Claude Code | — | **PASS** | 0 | 0 | 24 tool / 2 | 102 s | 對照基線 |
| Sonnet 5 | Claude Code | — | **PASS** | 0 | 0 | 18 tool / 2 | 119 s | 對照基線 |
| llama3.2:3b | lab, 4k ctx | v1 | 停（30 分停掉） | 9 | 4 | 8 / 3 | 1716 s | 第 1 步只講話；把檔案覆寫成 28 bytes 垃圾；用 markdown 模仿 tool call |
| llama3.2:3b | lab, 16k ctx | v2（語法檢查） | timeout | 9 | 4 | 3 / 2 | 1272 s | 行為同上，垃圾寫入被擋；寫整檔超過 10 分鐘斷線 |
| qwen2.5:14b | lab, 16k | — | 未跑 | — | — | — | — | 0.2 tok/s，放棄 |
| qwen2.5-coder:7b | 本機 | v2（無 text fallback） | 停 | 9 | 4 | 4 / 0 | 22 s | Ollama 對此模型不產原生 tool_calls，呼叫寫在文字裡 |
| qwen2.5-coder:7b | 本機 | v3（text fallback） | 停 | 9 | 4 | 6 / 2 | 330 s | verify 會了；之後用文字寫「計畫」、貼程式碼、端點自己猜 |
| qwen2.5-coder:7b | 本機 | v4（五步程序、精簡輸出） | 停 | 9 | 4 | 15 / 0 | 86 s | 完全照程序走；整檔重送時 JSON 轉義弄壞三引號，語法檢查全擋 |
| qwen2.5-coder:7b | 本機 | v5（edit_file） | 停 | **8** | **3** | 13 / 1 | 43 s | **第一次做對一處**（logical-switches → infra/segments）；之後回空回覆 |
| qwen2.5-coder:7b | 本機 | v6（連續提醒歸零） | 停 | 8 | 3 | 17 / 2 | 50 s | 同上；重放對話發現它拿到工具結果後會轉成閒聊（非 agent 模型） |
| llama3.2:3b | 本機, 16k | v6 | 停（60 步用完） | 9 | 4 | 60 / 60 | 4112 s | 只會反覆 run verify，一個字沒改 — 明確下限 |
| **qwen2.5:7b**（instruct，原生 tools） | 本機 | v6 | 停 | **6** | **6**（退步） | 38 / 2 | 302 s | 做對 3 處；但 vSphere 沒拿掉 `["value"]`、security-policies 留著字面 `{domain}` → **測試抓到退步**；vRA 的 old 抄 playbook 不抄檔案，重複 6 次 |
| **qwen2.5:7b** | 本機 | v7（最接近行提示、進退步差異） | timeout | **3** | 5 | 22 / 6 | 1215 s | 做對 4 處（含 vRA 登入路徑）；但 write_file **把 login 函式刪掉**、vRA 其他路徑改成幻想的 `/cloudapi/1.0.0/deployments`；第 22 步 LLM 回應超過 15 分鐘 |

## 每一輪逼出來的 kit 改動（都是通用的，不針對特定模型）

| 觸發 | 改動（`tools/agent_loop.py`） |
|---|---|
| 3B 把檔案寫成垃圾 | `write_file` 先 `ast.parse`，過短片段拒收 |
| 3B 下 `python tools/...` 被白名單拒 | 容忍 `python` 前綴 |
| coder-7B 把 tool call 寫在文字裡 | 從 content 解析 JSON 形式的呼叫（`arguments` / `parameters` 都吃） |
| coder-7B 用文字寫計畫、temperature 0 原句重複 | 起手改成固定五步程序；提醒訊息具體且逐次升級；提醒時 temperature 0.3 |
| coder-7B 被 pytest traceback 淹沒 | verify 用 `--tb=line`，工具輸出上限 3500 字 |
| coder-7B 整檔重送轉義壞三引號 | 新增 `edit_file`（old 唯一出現、改完語法檢查） |
| coder-7B 空回覆把提醒次數用光 | 提醒只算連續次數，成功呼叫即歸零 |
| qwen-7B 的 old 抄 playbook 不抄檔案 | `edit_file` 找不到時回檔案裡最接近的幾行 |
| qwen-7B 改壞測試卻沒察覺 | verify / scan 輸出附「hits 9→6（進步）/ REGRESSION: 失敗測試 4→6」 |
| qwen-7B 用 write_file 把函式刪掉 | `write_file` 比對 AST，丟失既有函式即拒收 |

## 結論

1. **kit 的機制成立**：小模型每一步的錯都被 scanner / 語法檢查 / 測試 / 退步差異抓到，沒有一次壞檔落地到讓 verify 誤判為 PASS。
2. **模型有下限**：3B 完全做不到；7B coder 不是 agent 模型（拿到工具結果會轉閒聊）；7B instruct 能做對 4/9 但會幻想端點、刪函式 —— 每一輪都需要人審 diff。
3. **能力門檻大約在「原生 tool calling + 會照程序 + 不幻想」**：Haiku 4.5 是這次最小的一次過模型。客戶要用內部 LLM，建議至少 14B–32B 級、有 tool 模板的 instruct 模型，跑在 GPU 上；CPU 推論（0.2 tok/s）不可行。
4. **lab 那台 `ollama-14b` VM 不適合做這件事**：沒有 GPU，14B 一步可達一小時。

原始紀錄：`results/small-models/*.jsonl|log`（每步計時、每次工具呼叫與回覆）。

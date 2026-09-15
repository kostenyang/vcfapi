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

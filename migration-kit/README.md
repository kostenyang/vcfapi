# VCF 9.1 Migration Kit — 讓任何 AI agent 幫你把舊程式遷到 VCF 9.1

給「想用自家 LLM / 任一 coding agent 改寫舊 vSphere 8 / vRA 8 / vROps / NSX-T 程式」的團隊。
kit 本身不含模型、不綁工具；模型是可換的，**repo 裡的知識 + 驗證迴圈**才是不變的部分。

```
AGENTS.md            ← agent 第一個讀的檔（Codex / Cursor / OpenHands / 內部 LLM 通用；CLAUDE.md 指到這裡）
docs/rules.md        ← 14 條規則，每條附 lab 實測狀態碼
docs/auth-matrix.md  ← 認證舊→新
docs/playbooks/      ← 4 份「判斷樹 + before/after」
data/mapping_544.json        ← 逐條對照（舊碼 / 建議碼 / 兩端實測）— 公開版只附 mapping_example.json，完整版隨客戶交付
data/vcf91_api_catalog.json  ← VCF 9.1 全部 9,768 條 REST API（從官方 SDK 機械抽出）
data/legacy_patterns.json    ← scanner 的 pattern 表
tools/scan_legacy.py  ← 找舊寫法；0 hits = 遷完
tools/lookup.py       ← 查對照表 / API 目錄（不用把 JSON 塞 prompt）
tools/verify.py       ← scan + pytest 一鍵驗證（離線）
tools/progress.py     ← 進度 JSON
tools/agent_loop.py   ← 最小 agent 迴圈骨架（OpenAI-compatible endpoint 用）
tests/                ← pytest + lab 錄的 cassette（離線回放，不需要帳密）
legacy_app/           ← 示範用舊程式（agent 的練習目標，合成，非客戶碼）
samples/              ← 可跑範例：rest/（Python 3.8）與 sdk/（3.10+）
```

## 三分鐘看懂

```bash
pip install -r requirements.txt
python tools/verify.py          # 現況：scanner 8 hits、tests 有紅 → 這就是 agent 的起點
python tools/scan_legacy.py     # 哪幾行、為什麼、改成什麼、看哪份 playbook
python tools/lookup.py "logical-switches"
```

把 repo 丟給 agent，指令只要一句：「讓 `python tools/verify.py` 回 PASS，只改 legacy_app/」。

## 為什麼這樣設計

| 層 | 東西 | 為什麼 |
|---|---|---|
| 知識 | JSON + Markdown | 任何模型都讀得懂；用 `lookup.py` 按需查，小 context 模型也撐得住 |
| 指令 | `AGENTS.md` + playbooks | 開放慣例；規則寫短、例子寫多，弱模型靠 pattern 就能做對 |
| 驗證 | scanner + cassette tests | 給 agent **確定的回饋**：綠/紅、0/非 0。不需要 lab，也不會誤打生產 |
| 工具 | CLI（可再包 MCP） | 有 shell 的 agent 都能用；沒有現成 agent 就用 `agent_loop.py` 接自家 endpoint |

## 接到自家 LLM

```bash
export LLM_BASE_URL=http://llm.internal/v1   # vLLM / Ollama / LiteLLM 都是 OpenAI-compatible
export LLM_MODEL=qwen2.5-coder-32b
python tools/agent_loop.py --max-steps 40
```

## 真實專案怎麼用

1. 把 `legacy_app/` 換成你的 repo（或把 kit 的 `tools/ tests/ docs/ data/ AGENTS.md` 複製進你的 repo）。
2. `data/legacy_patterns.json` 補你自己的 pattern；`tests/cassettes/` 用 `--live` 對你的環境重錄。
3. 每個 PR 一批（一個 playbook 類別），人只審 diff + `progress.py` 的 JSON。

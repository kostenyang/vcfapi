"""最小 agent 迴圈 — 給「沒有現成 coding agent、只有一個內部 LLM endpoint」的情境。

任何 OpenAI-compatible chat API 都能接（vLLM / Ollama / LiteLLM / 內部閘道）：

    export LLM_BASE_URL=http://llm.internal/v1
    export LLM_API_KEY=...            # 沒有就留空
    export LLM_MODEL=qwen2.5-coder-32b
    python tools/agent_loop.py --max-steps 40

迴圈：讀 AGENTS.md → 呼叫 verify → 讓模型用 tools 改檔 → 再 verify → 直到 PASS 或步數用完。
模型只拿得到四個工具：list_files / read_file / write_file / run（限 tools/ 下的指令）。
本檔只示範骨架；沒有連任何 LLM 的環境下無法實跑，請自行接上 endpoint 後驗證。
"""
import argparse
import json
import os
import subprocess
import sys

import requests

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "qwen2.5-coder")
ALLOWED_CMDS = ("tools/verify.py", "tools/scan_legacy.py", "tools/lookup.py", "tools/progress.py")

TOOLS = [
    {"type": "function", "function": {"name": "list_files", "description": "列出 legacy_app/ 下的檔案",
                                      "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "read_file", "description": "讀一個檔案（相對 kit 根目錄）",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "整檔覆寫 legacy_app/ 下的一個檔案",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "run", "description": "執行 tools/ 下的驗證或查詢指令，例如 'tools/verify.py' 或 'tools/lookup.py logical-switches'",
                                      "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}}, "required": ["cmd"]}}},
]


def _safe(path):
    p = os.path.normpath(os.path.join(HERE, path))
    if not p.startswith(HERE):
        raise ValueError("path escapes kit")
    return p


def tool_call(name, args):
    if name == "list_files":
        out = []
        for d, _, fs in os.walk(os.path.join(HERE, "legacy_app")):
            out += [os.path.relpath(os.path.join(d, f), HERE) for f in fs if f.endswith(".py")]
        return "\n".join(sorted(out))
    if name == "read_file":
        return open(_safe(args["path"]), encoding="utf-8").read()[:20000]
    if name == "write_file":
        p = _safe(args["path"])
        if not os.path.relpath(p, HERE).startswith("legacy_app"):
            return "refused: only legacy_app/ is writable"
        open(p, "w", encoding="utf-8").write(args["content"])
        return "written %d bytes" % len(args["content"])
    if name == "run":
        parts = args["cmd"].split()
        if not parts or parts[0] not in ALLOWED_CMDS:
            return "refused: allowed = " + ", ".join(ALLOWED_CMDS)
        r = subprocess.run([sys.executable] + parts, cwd=HERE, capture_output=True, text=True, timeout=300)
        return (r.stdout + r.stderr)[-8000:] + "\n[exit %d]" % r.returncode
    return "unknown tool"


def chat(messages):
    h = {"Content-Type": "application/json"}
    if KEY:
        h["Authorization"] = "Bearer " + KEY
    r = requests.post(BASE.rstrip("/") + "/chat/completions", headers=h, timeout=600,
                      json={"model": MODEL, "messages": messages, "tools": TOOLS, "temperature": 0})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-steps", type=int, default=40)
    a = ap.parse_args()
    system = open(os.path.join(HERE, "AGENTS.md"), encoding="utf-8").read()
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": "目標：讓 `tools/verify.py` 回 PASS（scanner 0 hits、測試全綠）。"
                                            "先 run tools/verify.py 看現況，再逐檔改 legacy_app/。每改一個檔就重跑 verify。"}]
    for step in range(a.max_steps):
        msg = chat(messages)
        messages.append(msg)
        if not msg.get("tool_calls"):
            print("[assistant]", (msg.get("content") or "")[:500])
            break
        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"] or "{}")
            out = tool_call(name, args)
            print("[%02d] %s %s → %s" % (step, name, json.dumps(args, ensure_ascii=False)[:80], out[:120].replace("\n", " ")))
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
            if name == "run" and "VERIFY: PASS" in out:
                print("DONE at step", step)
                return
    print("stopped without PASS")


if __name__ == "__main__":
    main()

"""最小 agent 迴圈 — 給「沒有現成 coding agent、只有一個內部 LLM endpoint」的情境。

任何 OpenAI-compatible chat API 都能接（vLLM / Ollama / LiteLLM / 內部閘道）：

    export LLM_BASE_URL=http://llm.internal/v1
    export LLM_API_KEY=...            # 沒有就留空
    export LLM_MODEL=qwen2.5-coder-32b
    export LLM_TIMEOUT=1800           # CPU 推論時每次回應可能超過 10 分鐘
    python tools/agent_loop.py --max-steps 40

迴圈：讀 AGENTS.md → 呼叫 verify → 讓模型用 tools 改檔 → 再 verify → 直到 PASS 或步數用完。
模型只拿得到四個工具：list_files / read_file / write_file / run（限 tools/ 下的指令）。
本檔只示範骨架；沒有連任何 LLM 的環境下無法實跑，請自行接上 endpoint 後驗證。
"""
import argparse
import json
import os
import re
import subprocess
import sys

import requests

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "qwen2.5-coder")
TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "600"))   # CPU 推論的大模型要放大，例如 1800
_STATE = {}
ALLOWED_CMDS = ("tools/verify.py", "tools/scan_legacy.py", "tools/lookup.py", "tools/progress.py")

TOOLS = [
    {"type": "function", "function": {"name": "list_files", "description": "列出 legacy_app/ 下的檔案",
                                      "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "read_file", "description": "讀一個檔案（相對 kit 根目錄）",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "整檔覆寫 legacy_app/ 下的一個檔案",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "edit_file", "description": "在 legacy_app/ 的檔案裡把一段唯一出現的文字換成新文字（小改建議用這個，不必整檔重送）",
                                      "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string", "description": "要被取代的原文，必須在檔案中剛好出現一次"}, "new": {"type": "string"}}, "required": ["path", "old", "new"]}}},
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
        if p.endswith(".py"):
            import ast
            try:
                ast.parse(args["content"])
            except SyntaxError as e:
                return "refused: content is not valid Python (%s). File unchanged. Tip: use edit_file with a small unique 'old' snippet instead of rewriting the whole file." % e
            if len(args["content"]) < 200:
                return "refused: content too short to be the whole module. Send the complete file, not a fragment."
            if os.path.exists(p):
                old_funcs = {n.name for n in ast.parse(open(p, encoding="utf-8").read()).body if isinstance(n, ast.FunctionDef)}
                new_funcs = {n.name for n in ast.parse(args["content"]).body if isinstance(n, ast.FunctionDef)}
                dropped = sorted(old_funcs - new_funcs)
                if dropped:
                    return ("refused: your content drops function(s) %s that callers depend on. "
                            "Send the complete file with every function kept, or use edit_file for a small change." % ", ".join(dropped))
        open(p, "w", encoding="utf-8").write(args["content"])
        return "written %d bytes" % len(args["content"])
    if name == "edit_file":
        p = _safe(args["path"])
        if not os.path.relpath(p, HERE).startswith("legacy_app"):
            return "refused: only legacy_app/ is writable"
        src = open(p, encoding="utf-8").read()
        n = src.count(args["old"])
        if n != 1:
            hint = ""
            if n == 0:
                import difflib
                lines = src.splitlines()
                key = args["old"].strip().splitlines()[0] if args["old"].strip() else ""
                close = difflib.get_close_matches(key, lines, n=3, cutoff=0.3) if key else []
                if not close:
                    toks = [t for t in re.split(r"[^A-Za-z0-9_./-]+", key) if len(t) > 5]
                    close = [l for l in lines if any(t in l for t in toks)][:3]
                if close:
                    hint = " Closest lines in the file:\n" + "\n".join("  " + l.strip() for l in close)
            return "refused: 'old' occurs %d times (must be exactly 1). Copy the exact text from read_file.%s" % (n, hint)
        new_src = src.replace(args["old"], args["new"])
        if p.endswith(".py"):
            import ast
            try:
                ast.parse(new_src)
            except SyntaxError as e:
                return "refused: result is not valid Python (%s). File unchanged." % e
        open(p, "w", encoding="utf-8").write(new_src)
        return "edited: replaced 1 occurrence (%d -> %d bytes)" % (len(src), len(new_src))
    if name == "run":
        parts = args["cmd"].split()
        if parts and parts[0] in ("python", "python3"):
            parts = parts[1:]
        if not parts or parts[0] not in ALLOWED_CMDS:
            return "refused: allowed = " + ", ".join(ALLOWED_CMDS)
        r = subprocess.run([sys.executable] + parts, cwd=HERE, capture_output=True, text=True, timeout=300)
        out = (r.stdout + r.stderr)[-3500:] + "\n[exit %d]" % r.returncode
        m_h = re.search(r"(\d+) hits", out); m_f = re.search(r"(\d+) failed", out); m_p = re.search(r"(\d+) passed", out)
        if parts[0] in ("tools/verify.py", "tools/scan_legacy.py") and m_h:
            hits = int(m_h.group(1)); failed = int(m_f.group(1)) if m_f else (0 if m_p else None)
            prev = _STATE.get("last")
            if prev:
                d = []
                if hits < prev[0]: d.append("legacy hits %d -> %d (progress)" % (prev[0], hits))
                if hits > prev[0]: d.append("legacy hits %d -> %d (WORSE)" % (prev[0], hits))
                if failed is not None and prev[1] is not None:
                    if failed > prev[1]: d.append("REGRESSION: failing tests %d -> %d — your last edit broke behaviour; read the failing test names above and fix that file (e.g. response shape changed)" % (prev[1], failed))
                    if failed < prev[1]: d.append("failing tests %d -> %d (progress)" % (prev[1], failed))
                if d: out += "\n[delta] " + "; ".join(d)
            _STATE["last"] = (hits, failed)
        return out
    return "unknown tool"


def extract_tool_calls(msg):
    """沒有原生 tool_calls 時，從 content 裡撈 JSON 形式的呼叫。
    很多內部部署（或 Ollama 上沒有 tools 模板的模型，例如 qwen2.5-coder）會把
    {"name": ..., "arguments": {...}} 直接寫在文字裡；這裡把它當成正式呼叫。"""
    import re
    if msg.get("tool_calls"):
        return msg["tool_calls"]
    text = msg.get("content") or ""
    calls, i = [], 0
    for cand in re.findall(r"\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}", text):
        try:
            obj = json.loads(cand)
        except ValueError:
            continue
        if isinstance(obj, dict) and "name" in obj:
            args = obj.get("arguments", obj.get("parameters", {}))
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            calls.append({"id": "parsed_%d" % i, "type": "function",
                          "function": {"name": obj["name"], "arguments": json.dumps(args, ensure_ascii=False)}})
            i += 1
    if calls:
        msg["tool_calls"] = calls          # 讓後面流程與原生格式一致
        msg["content"] = ""
    return calls


def chat(messages, temperature=0):
    h = {"Content-Type": "application/json"}
    if KEY:
        h["Authorization"] = "Bearer " + KEY
    r = requests.post(BASE.rstrip("/") + "/chat/completions", headers=h, timeout=TIMEOUT,
                      json={"model": MODEL, "messages": messages, "tools": TOOLS, "temperature": temperature})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]


TASK = """目標：讓 `tools/verify.py` 印出 VERIFY: PASS（scanner 0 hits、測試全綠）。
你只能透過工具做事；不要用文字描述計畫、不要在文字裡貼程式碼。每一輪回覆就是一個工具呼叫。
固定流程，照順序做：
1. run  "tools/scan_legacy.py"            → 看被標出的檔案、pattern 與 playbook
2. read_file 該 pattern 對應的 playbook（例如 "docs/playbooks/nsx-mp-to-policy.md"）
3. read_file 被標出的檔案（例如 "legacy_app/nsx_client.py"）
4. edit_file 該檔：old = 從 read_file 原文複製的那一行（例如 "/api/v1/logical-switches"），new = playbook 給的新路徑。
   一次改一處；需要整檔重寫才用 write_file（內容必須是完整、可執行的 Python）
5. run  "tools/verify.py"                 → 還有 hits 或紅字就回到 1 處理下一個檔
規則：不改 legacy_app/ 以外的檔；保留函式簽章與回傳型別；新端點以 playbook 為準，不要自己猜路徑。"""

NUDGES = [
    "你剛才用文字回覆，沒有呼叫工具。請直接呼叫工具。現在就做第 1 步：run，cmd 是 \"tools/scan_legacy.py\"。",
    "還是沒有工具呼叫。請只輸出一個工具呼叫、不要任何解說。格式：{\"name\": \"read_file\", \"arguments\": {\"path\": \"legacy_app/nsx_client.py\"}}",
    "最後一次提醒：回覆必須是工具呼叫。例如 {\"name\": \"edit_file\", \"arguments\": {\"path\": \"legacy_app/nsx_client.py\", \"old\": \"/api/v1/logical-switches\", \"new\": \"/policy/api/v1/infra/segments\"}}",
]


def main():
    import time
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-steps", type=int, default=40)
    ap.add_argument("--log", default="agent_loop.jsonl")
    a = ap.parse_args()
    log = open(os.path.join(HERE, a.log), "a")
    t0 = time.time(); nudges = 0; total_nudges = 0; verify_runs = 0
    def rec(**kw):
        kw["t"] = round(time.time() - t0, 1); log.write(json.dumps(kw, ensure_ascii=False) + "\n"); log.flush()
    system = open(os.path.join(HERE, "AGENTS.md"), encoding="utf-8").read()
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": TASK}]
    for step in range(a.max_steps):
        ts = time.time()
        try:
            msg = chat(messages, temperature=0 if nudges == 0 else 0.3)
        except Exception as e:
            print("[%02d] LLM error: %s" % (step, e)); rec(step=step, error=str(e)[:300]); break
        raw = (msg.get("content") or "")[:300]
        parsed = not msg.get("tool_calls") and bool(extract_tool_calls(msg))
        messages.append(msg)
        rec(step=step, llm_s=round(time.time() - ts, 1), content=raw, parsed_from_text=parsed,
            tool_calls=[tc["function"]["name"] for tc in (msg.get("tool_calls") or [])])
        if not msg.get("tool_calls"):
            print("[%02d] assistant(no tool): %s" % (step, ((msg.get("content") or "").strip() or "<empty>")[:200].replace("\n", " ")))
            nudges += 1; total_nudges += 1
            if nudges > len(NUDGES) or total_nudges > 12:
                print("model keeps replying without tools; stop"); break
            empty = not (msg.get("content") or "").strip()
            text = ("你的回覆是空的。請繼續流程：先 run \"tools/scan_legacy.py\" 看還剩哪些，然後處理下一個檔。"
                    if empty and nudges == 1 else NUDGES[nudges - 1])
            messages.append({"role": "user", "content": text})
            continue
        nudges = 0   # 有工具呼叫就重置連續提醒計數
        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
                if not isinstance(args, dict): raise ValueError("arguments not an object")
                out = tool_call(name, args)
            except Exception as e:
                out = "tool error: %s" % e
            if name == "run" and "verify" in json.dumps(args): verify_runs += 1
            print("[%02d] %s %s → %s" % (step, name, json.dumps(args, ensure_ascii=False)[:80], out[:120].replace("\n", " ")), flush=True)
            rec(step=step, tool=name, args=json.dumps(args, ensure_ascii=False)[:300], out=out[-600:])
            messages.append({"role": "tool", "tool_call_id": tc.get("id", "call_%d" % step), "name": name, "content": out})
            if name == "run" and "VERIFY: PASS" in out:
                print("DONE at step %d — verify runs %d, %.0fs" % (step, verify_runs, time.time() - t0))
                rec(done=True, verify_runs=verify_runs); return
    print("stopped without PASS — verify runs %d, %.0fs" % (verify_runs, time.time() - t0))
    rec(done=False, verify_runs=verify_runs)


if __name__ == "__main__":
    main()

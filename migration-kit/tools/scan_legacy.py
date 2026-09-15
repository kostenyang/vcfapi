"""找出程式裡的舊寫法，列成待辦。「掃出 0 條」= 遷移完成的機器可判定訊號。

    python tools/scan_legacy.py [path ...]      # 預設掃 legacy_app/
    python tools/scan_legacy.py --json          # 給 agent 讀
    exit code 0 = 乾淨；1 = 還有 break；2 = 只剩 deprecated
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATTERNS = json.load(open(os.path.join(HERE, "data", "legacy_patterns.json")))["patterns"]
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "data", "docs", "tests", "tools", "samples"}
EXT = (".py", ".sh", ".ps1", ".yml", ".yaml", ".json", ".j2", ".md")


def scan_path(root):
    hits = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in files:
            if not fn.endswith(EXT):
                continue
            p = os.path.join(dirpath, fn)
            try:
                lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                for pat in PATTERNS:
                    if re.search(pat["regex"], line):
                        hits.append(dict(file=os.path.relpath(p, HERE), line=i, code=line.strip()[:120],
                                         pattern=pat["id"], severity=pat["severity"],
                                         component=pat["component"], why=pat["why"],
                                         target=pat["target"], playbook=pat["playbook"]))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", default=[os.path.join(HERE, "legacy_app")])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    hits = []
    for p in a.paths:
        hits += scan_path(p)
    if a.json:
        print(json.dumps(hits, ensure_ascii=False, indent=1))
    else:
        if not hits:
            print("scan_legacy: 0 hits — 沒有舊寫法了。")
        for h in hits:
            print("[%-10s] %s:%d  %s\n             → %s  (%s)" % (
                h["severity"], h["file"], h["line"], h["code"], h["target"], h["playbook"]))
        print("\n%d hits (%d break, %d deprecated)" % (
            len(hits), sum(h["severity"] == "break" for h in hits),
            sum(h["severity"] == "deprecated" for h in hits)))
    if any(h["severity"] == "break" for h in hits):
        sys.exit(1)
    sys.exit(2 if hits else 0)


if __name__ == "__main__":
    main()

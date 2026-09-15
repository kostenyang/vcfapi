"""查對照表 / API 目錄。給 agent 用的查詢工具，避免把 5MB JSON 整份塞進 prompt。

    python tools/lookup.py "logical-switches"          # 查 544 條對照（endpoint/method/舊碼）
    python tools/lookup.py --catalog "infra/segments"  # 查 VCF 9.1 全 API 目錄（9,768 條）
    python tools/lookup.py --id 123                    # 看第 123 條完整內容
"""
import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = os.path.join(HERE, "data", "mapping_544.json")
if not os.path.exists(MAP):  # 公開版只附通用範例；完整 544 條在客戶交付版
    MAP = os.path.join(HERE, "data", "mapping_example.json")
CAT = os.path.join(HERE, "data", "vcf91_api_catalog.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--catalog", action="store_true", help="查 9,768 條 API 目錄而不是對照表")
    ap.add_argument("--id", type=int)
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.id is not None:
        rows = [r for r in json.load(open(MAP)) if r["id"] == a.id]
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return

    rx = re.compile(re.escape(a.query), re.I)
    if a.catalog:
        rows = [r for r in json.load(open(CAT))
                if rx.search(r["url_template"]) or rx.search(r["summary"]) or rx.search(r["method"])]
        rows = rows[: a.limit]
        if a.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
        else:
            for r in rows:
                print("%-6s %s\n       %s.%s(%s)  %s" % (r["http_method"], r["url_template"],
                                                          r["module"], r["cls"], r["required"],
                                                          r["summary"][:90]))
        return

    rows = [r for r in json.load(open(MAP))
            if rx.search(r["endpoint"]) or rx.search(r["method"]) or rx.search(r.get("legacy_code", ""))
            or rx.search(r.get("purpose", ""))]
    rows = rows[: a.limit]
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        for r in rows:
            print("#%d %s | %s | %s %s | %s\n   舊: %s\n   新: %s\n   實測: %s\n" % (
                r["id"], r.get("urgency",""), r["service"], r["method"], r["endpoint"], r.get("change",""),
                r.get("legacy_code", "")[:160].replace("\n", " ⏎ "),
                r.get("recommended_code", "")[:160].replace("\n", " ⏎ "),
                (r.get("verified_evidence") or r.get("verified", ""))[:120]))


if __name__ == "__main__":
    main()

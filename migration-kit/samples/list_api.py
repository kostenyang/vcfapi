"""從已安裝的 vcf-sdk 反查 VCF 9.1 全部 REST API，輸出 CSV/JSON。

Excel 全清單就是這支程式產生的 —— 你可以在自己的環境重跑一次驗證，
或在下一版 SDK 出來時直接重產。

    pip install vcf-sdk           # 需要 Python 3.10+
    python tools/list_api.py --out api.csv

原理：SDK 的 vAPI binding 是自動產生的，每個 operation 都帶
OperationRestMetadata(http_method=..., url_template=...)，用 ast 靜態解析即可，
不需要連任何一台機器。
"""
import argparse
import ast
import csv
import json
import os
import re
import sys

PACKAGES = ["vmware/vcenter", "vmware/sddc_manager", "vmware/vcf_installer",
            "vmware/vapi", "vcf/nsx", "vcf/operations", "vcf/operations_networks",
            "vcf/log_mgmt", "vcf/fleet_lcm", "vcf/sddc_lcm",
            "com/vmware"]


def site_dirs():
    out = []
    for p in sys.path:
        if p.endswith(("site-packages", "dist-packages")) and os.path.isdir(p):
            out.append(p)
    return out


def const(node):
    return node.value if isinstance(node, ast.Constant) else None


def dict_keys(node):
    if isinstance(node, ast.Call) and node.args:
        node = node.args[0]
    return [const(k) for k in node.keys] if isinstance(node, ast.Dict) else []


def first_line(doc):
    for ln in (doc or "").splitlines():
        s = ln.strip()
        if s and not s.startswith(":"):
            return s
    return ""


def scan_file(path, root):
    src = open(path, encoding="utf-8").read()
    if "OperationRestMetadata" not in src:
        return []
    tree = ast.parse(src)
    module = re.sub(r"_client$", "",
                    os.path.relpath(path, root)[:-3].replace(os.sep, "."))
    iface, stubs, rows = {}, {}, []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name.startswith("_") and node.name.endswith("Stub"):
            metas = {}
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                        and isinstance(sub.targets[0], ast.Name)
                        and sub.targets[0].id.endswith("_rest_metadata")
                        and isinstance(sub.value, ast.Call)):
                    m = {}
                    for kw in sub.value.keywords:
                        if kw.arg in ("http_method", "url_template", "request_body_parameter"):
                            m[kw.arg] = const(kw.value)
                        elif kw.arg in ("path_variables", "query_parameters"):
                            m[kw.arg] = [k for k in dict_keys(kw.value) if k]
                    metas[sub.targets[0].id[: -len("_rest_metadata")]] = m
            stubs[node.name[1:-4]] = metas
        else:
            svc, methods = None, {}
            for sub in node.body:
                if (isinstance(sub, ast.Assign) and isinstance(sub.targets[0], ast.Name)
                        and sub.targets[0].id == "_VAPI_SERVICE_ID"):
                    svc = const(sub.value)
                if isinstance(sub, ast.FunctionDef) and not sub.name.startswith("_"):
                    args = [a.arg for a in sub.args.args[1:]]
                    nd = len(sub.args.defaults)
                    methods[sub.name] = (args[: len(args) - nd] if nd else args,
                                         ast.get_docstring(sub) or "")
            iface[node.name] = (svc, methods)
    for cls, metas in stubs.items():
        svc, methods = iface.get(cls, (None, {}))
        for op, m in sorted(metas.items()):
            req, doc = methods.get(op, ([], ""))
            rows.append(dict(module=module + "_client", cls=cls, method=op,
                             service_id=svc or "",
                             http_method=m.get("http_method", ""),
                             url_template=m.get("url_template", ""),
                             path_params=",".join(m.get("path_variables", []) or []),
                             query_params=",".join(m.get("query_parameters", []) or []),
                             body=m.get("request_body_parameter") or "",
                             required=",".join(req),
                             summary=first_line(doc)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="vcf91_api.csv")
    args = ap.parse_args()

    rows, seen = [], set()
    for root in site_dirs():
        for pkg in PACKAGES:
            base = os.path.join(root, pkg)
            top = base + "_client.py"          # 例：vcf/operations_networks_client.py
            if os.path.isfile(top) and top not in seen:
                seen.add(top)
                try:
                    rows.extend(scan_file(top, root))
                except SyntaxError:
                    pass
            if not os.path.isdir(base):
                continue
            for dirpath, _, files in os.walk(base):
                for fn in files:
                    if not fn.endswith("_client.py"):
                        continue
                    p = os.path.join(dirpath, fn)
                    if p in seen:
                        continue
                    seen.add(p)
                    try:
                        rows.extend(scan_file(p, root))
                    except SyntaxError:
                        pass
    rows.sort(key=lambda r: (r["url_template"], r["http_method"]))
    if args.out.endswith(".json"):
        json.dump(rows, open(args.out, "w"), ensure_ascii=False, indent=1)
    else:
        with open(args.out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print("%d operations → %s" % (len(rows), args.out))


if __name__ == "__main__":
    main()

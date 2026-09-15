"""一鍵驗證：scan_legacy → pytest（cassette 離線）→（可選）--live 打真環境。

    python tools/verify.py            # 離線，agent 迴圈用這個
    python tools/verify.py --live     # 需要 VCF_API_CONFIG 指到 lab 組態
    exit 0 = 全過（scanner 0 hits 且測試全綠）
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd, **kw):
    print("$ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=HERE, **kw).returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    py = sys.executable
    scan = run([py, "tools/scan_legacy.py"])
    tests = run([py, "-m", "pytest", "-q", "tests"])
    live = 0
    if a.live:
        for s in ("01_vcenter", "02_sddc_manager", "03_nsx", "04_vcf_operations"):
            live |= run([py, "samples/rest/%s.py" % s])
    ok = scan == 0 and tests == 0 and live == 0
    print("\nVERIFY:", "PASS" if ok else "FAIL",
          "(scan=%s, tests=%s%s)" % (scan, tests, ", live=%s" % live if a.live else ""))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

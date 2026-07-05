# Migration experiments — reproducible live proofs

Each script here reproduces one of the live experiments behind the migration
workbooks and the "Current vs. Redesigned" deck. All are **read-only** against
the lab and take endpoints/credentials from `config/lab.yaml` (git-ignored;
see `config/lab.example.yaml`).

| Script | Proves | Key result (home.lab, 2026-07-03) |
|---|---|---|
| `exp1_same_code_8_vs_9.py` | vSphere has NO hard break: same pyVmomi-8.0.3 SOAP + old `/rest` + new `/api` code runs on vSphere 8 **and** VCF 9.1 | SOAP OK on both (apiVersion 8.0.3.0 / 9.1.0.0); `/rest` still answers 200 on 9.1 (deprecated, not removed) |
| `exp2_login_cross_test.py` | The ONE hard break: vRA8 login vs VCFA9 OAuth, cross-tested 2×2 | old→8=200, old→9=**404**; new→9=OK, new→8=**404** |
| `exp3_sddc_centralized.py` | SDDC Manager as the single management plane + zero-secret bootstrap | credentials=16, bundles=199, releases=18; store→vCenter session→VM list with no local passwords |
| `legacy_flow.py` | The customer's ORIGINAL way, runnable end-to-end: 6 ops tasks with per-component logins (SOAP + /rest CIS + NSX + vRA8 password login) | all 6 tasks pass on the real old estate (vSphere 8.0.3: 123 VM; vRA8: 74 machines); 26 calls / 6.7s; ESXi creds + version compare = manual |
| `redesigned_flow.py` | The SAME 6 tasks the VCF 9.1 way (unified vcf-sdk + SDDC Manager + VCF Ops + VCFA OAuth) | all 6 pass; 12 calls / 5.1s; SLOC 149→122, imports 10→6, NSX-specific lines 34→0, zero manual steps |
| `workflow_compare.py` | Redesigned workflows need fewer calls — measured, not estimated | six workflows: **48 → 13 calls (−73%)** |

Config blocks used: `vsphere8` (old outer vCenter), `vra8`, `vcenter`, `nsx`,
`sddc_manager`, `vcf_operations`, `vcf_automation`, `log_management`.

Honest caveats baked into the scripts/output:
- workflow 5's old side (vRLCM) cannot run — the product is removed in VCF 9;
  its call count comes from the customer raw-data rows.
- workflow 6's saving is credential elimination, not call count.

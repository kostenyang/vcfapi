# esxcli / Ansible — 第三條路（ESXi 主機層）

有一類操作 **REST 與 SDK 都沒有對應端點** —— ESXi 主機層的 `esxcli` 設定。
客戶現行就是用 **Ansible**（`community.vmware` collection 或 SSH + `esxcli`）做這些事:

- Standard vSwitch / Port Group / VMkernel
- DNS / NTP / SNMP
- Firewall ruleset / Service 管理
- Software component / VIB

**遷移建議:沿用 CLI / Ansible。** VCF 9 的 ESXi 持續支援 `esxcli` 與 Ansible
`community.vmware`,所以這條路**不需要改寫**,與 Python 版本無關(Ansible 自帶
執行環境)。

> ⚠️ **VCF 9 ESXi 預設關閉 SSH**（KB 86230）。走 SSH + raw `esxcli` 前需先開啟
> SSH 服務(或改用 `community.vmware` 走 vCenter API 的 host 模組,免 SSH)。

## 兩種做法

| 做法 | 走法 | 適用 |
|------|------|------|
| `community.vmware` 模組 | 經 vCenter API（免 SSH） | 有對應模組的操作（NTP/DNS/firewall/service 等） |
| SSH + raw `esxcli` | 直連 ESXi shell | 無對應模組的 host CLI 操作 |

## 範例

- `configure_esxi_host.yml` — 用 `community.vmware` 設定 NTP / DNS / 防火牆 / 服務（免 SSH）
- 同檔末段示範 SSH + raw `esxcli` 的 fallback 寫法

```bash
ansible-galaxy collection install community.vmware
pip install pyvmomi          # community.vmware 經 vCenter API 時需要（Ansible 控制端）
ansible-playbook esxcli/configure_esxi_host.yml -e @config/lab.yaml
```

> 這條路不在 apisample 的 Python REST/SDK 範圍內,但放這裡讓「API / SDK / CLI
> 三條路」在同一個 repo 完整呈現（對應 Excel 的決策流程圖）。

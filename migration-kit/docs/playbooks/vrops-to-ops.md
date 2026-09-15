# Playbook：vROps 8 → VCF Operations 9.1

**判斷**：`Authorization: vRealizeOpsToken …` → 改成 `OpsToken`。其他不動。

- base 仍是 `https://<ops>/suite-api`
- token 端點仍是 `POST /suite-api/api/auth/token/acquire`（JSON `{username, password}`，`Accept: application/json`）
- 9.1 對 `vRealizeOpsToken` 仍相容（實測 200），所以這是「建議改」不是「壞了」；`Bearer` 反而 401。

```python
# before
headers = {"Authorization": "vRealizeOpsToken " + token}
# after
headers = {"Authorization": "OpsToken " + token}
```

回應 JSON 形狀沒變（`resourceList`、`pageInfo`、`adapter-kind`）。

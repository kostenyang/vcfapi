"""vROps → VCF Operations：suite-api 不變；9.1 同時接受 OpsToken 與舊的 vRealizeOpsToken。
測試守行為；改 header 是 scanner 驅動的「建議改」，不是「壞了才改」。"""
from legacy_app import vrops_client as c

H, U, P = "ops.example.local", "admin", "pw"


def test_acquire_token():
    assert c.acquire_token(H, U, P)


def test_get_resources():
    res = c.get_resources(H, c.acquire_token(H, U, P))
    assert res and "resourceKey" in res[0]


def test_get_adapter_kinds():
    kinds = c.get_adapter_kinds(H, c.acquire_token(H, U, P))
    assert any(k["key"] == "VMWARE" for k in kinds)

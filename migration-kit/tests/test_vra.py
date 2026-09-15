"""vRA 8 → VCFA 9：唯一硬斷點。csp 登入 404；要改成 VCD session 或 /oauth/tenant。"""
from legacy_app import vra_client as c

H = "vcfa.example.local"


def test_login_returns_token():
    # 新寫法需要 org；舊簽章沒有這個參數 → 允許用 keyword 方式相容
    try:
        tok = c.login(H, "user", "pw", org="my-org")
    except TypeError:
        tok = c.login(H, "user", "pw")
    assert isinstance(tok, str) and tok


def test_list_deployments_with_tenant_token():
    try:
        tok = c.login(H, "user", "pw", org="my-org")
    except TypeError:
        tok = c.login(H, "user", "pw")
    deployments = c.list_deployments(H, tok)
    assert isinstance(deployments, list)

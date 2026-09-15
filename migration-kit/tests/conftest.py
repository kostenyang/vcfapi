"""Cassette 回放器：把 requests 的 HTTP 呼叫攔下來，用 lab 錄好的真實回應回答。

目的：agent 改程式後可以「離線」跑測試，不需要 lab 帳密，也不會誤打生產環境。
cassette 的格式與來源見 tests/cassettes/README.md。
"""
import json
import os
import re
from urllib.parse import urlsplit

import pytest
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CASSETTE_DIR = os.path.join(HERE, "cassettes")


def _load():
    rules = []
    for fn in sorted(os.listdir(CASSETTE_DIR)):
        if fn.endswith(".json"):
            with open(os.path.join(CASSETTE_DIR, fn)) as fh:
                rules.extend(json.load(fh)["rules"])
    return rules


def _header_ok(cond, headers):
    """cond: {"Authorization": "^OpsToken "} — 每個 key 的 regex 都要對到。"""
    low = {k.lower(): v for k, v in headers.items()}
    for k, pat in (cond or {}).items():
        v = low.get(k.lower())
        if v is None or not re.search(pat, str(v)):
            return False
    return True


def _match(rule, method, path, headers, auth):
    m = rule["match"]
    if m.get("method", method).upper() != method.upper():
        return False
    if not re.fullmatch(m["path"], path):
        return False
    if m.get("basic_auth") is True and not auth:
        return False
    if m.get("basic_auth") is False and auth:
        return False
    return _header_ok(m.get("headers"), headers)


def _build(rule, url):
    resp = requests.Response()
    r = rule["response"]
    resp.status_code = r["status"]
    body = r.get("json")
    resp._content = json.dumps(body).encode() if body is not None else r.get("text", "").encode()
    resp.headers.update(r.get("headers", {}))
    resp.headers.setdefault("Content-Type", "application/json")
    resp.url = url
    resp.reason = {200: "OK", 201: "Created", 401: "Unauthorized", 403: "Forbidden",
                   404: "Not Found", 500: "Internal Server Error"}.get(r["status"], "")
    return resp


@pytest.fixture(autouse=True)
def cassette_player(monkeypatch):
    rules = _load()

    def fake_request(self, method, url, **kw):
        parts = urlsplit(url)
        headers = dict(self.headers)
        headers.update(kw.get("headers") or {})
        auth = kw.get("auth") or self.auth
        if not auth and "authorization" in {k.lower() for k in headers} \
                and str([v for k, v in headers.items() if k.lower() == "authorization"][0]).startswith("Basic "):
            auth = True
        for rule in rules:
            if _match(rule, method, parts.path, headers, auth):
                return _build(rule, url)
        resp = requests.Response()
        resp.status_code = 404
        resp._content = json.dumps({"cassette": "no rule matched", "method": method,
                                    "path": parts.path}).encode()
        resp.url = url
        resp.reason = "Not Found (no cassette)"
        return resp

    monkeypatch.setattr(requests.Session, "request", fake_request)
    yield

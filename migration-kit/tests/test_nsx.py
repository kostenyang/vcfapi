"""NSX：MP /api/v1 的 transport-zones 在 9.1 還在（不用改）；
logical-switches / firewall/sections 是 NSX-V 世代端點，9.1 回 404 → 必須改走 Policy。"""
import pytest
import requests

from legacy_app import nsx_client as c

H, U, P = "nsx.example.local", "admin", "pw"


def test_transport_zones_still_work_on_mp_api():
    tz = c.list_transport_zones(H, U, P)
    assert tz and tz[0]["transport_type"] in ("OVERLAY", "VLAN")


def test_list_segments():
    segs = c.list_segments(H, U, P)
    assert segs and segs[0]["display_name"]


def test_list_firewall_sections_or_policies():
    rules = c.list_firewall_sections(H, U, P)
    assert rules and rules[0]["display_name"]

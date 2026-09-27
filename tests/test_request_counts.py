from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from buy_vs_rent.api import app
from buy_vs_rent.request_counts import (
    counts_path,
    recent_days,
    record_compare_ok,
    record_page_load,
    today_key,
    zahlen_allowed,
)

Berlin = ZoneInfo("Europe/Berlin")


def test_today_key_uses_berlin():
    when = datetime(2026, 9, 27, 23, 30, tzinfo=Berlin)
    assert today_key(when) == "2026-09-27"


def test_daily_totals_accumulate(tmp_path, monkeypatch):
    monkeypatch.setenv("BUY_VS_RENT_COUNTS_FILE", str(tmp_path / "counts.json"))
    when = datetime(2026, 9, 27, 12, 0, tzinfo=Berlin)
    record_page_load(when)
    record_page_load(when)
    record_compare_ok(when)
    rows = recent_days(last=1, anchor=when.date())
    assert rows[0][1]["page"] == 2
    assert rows[0][1]["compare_ok"] == 1
    assert rows[0][1]["compare_reject"] == 0


def test_zahlen_host_gate():
    assert not zahlen_allowed("kauf-oder-mieten.de")
    assert not zahlen_allowed("www.kauf-oder-mieten.de:443")
    assert zahlen_allowed("192.168.178.10:8000")
    assert zahlen_allowed("127.0.0.1:8000")


def test_zahlen_404_on_public_host(tmp_path, monkeypatch):
    monkeypatch.setenv("BUY_VS_RENT_COUNTS_FILE", str(tmp_path / "counts.json"))
    client = TestClient(app)
    response = client.get("/zahlen", headers={"Host": "kauf-oder-mieten.de"})
    assert response.status_code == 404


def test_zahlen_ok_on_lan_host(tmp_path, monkeypatch):
    monkeypatch.setenv("BUY_VS_RENT_COUNTS_FILE", str(tmp_path / "counts.json"))
    client = TestClient(app)
    response = client.get("/zahlen", headers={"Host": "192.168.178.10:8000"})
    assert response.status_code == 200
    assert "Tageszahlen" in response.text
    assert "<table" in response.text

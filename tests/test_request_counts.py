from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from buy_vs_rent.api import app
from buy_vs_rent.request_counts import (
    COMPARE_COUNT_HEADER,
    compare_counts_as_rechnen,
    counts_path,
    public_site_host,
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


def test_public_site_host_gate():
    assert public_site_host("kauf-oder-mieten.de")
    assert public_site_host("www.kauf-oder-mieten.de:443")
    assert not public_site_host("192.168.178.10:8000")
    assert not public_site_host("127.0.0.1:8000")


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


def test_zahlen_404_when_caddy_forwards_public_name(tmp_path, monkeypatch):
    monkeypatch.setenv("BUY_VS_RENT_COUNTS_FILE", str(tmp_path / "counts.json"))
    client = TestClient(app)
    response = client.get(
        "/zahlen",
        headers={
            "Host": "127.0.0.1:8000",
            "X-Forwarded-Host": "kauf-oder-mieten.de",
        },
    )
    assert response.status_code == 404


def test_compare_counts_as_rechnen_header():
    assert compare_counts_as_rechnen("chat")
    assert not compare_counts_as_rechnen("slider")
    assert not compare_counts_as_rechnen(None)


def _minimal_compare_body():
    return {
        "version": 1,
        "as_of": "2026-09-01",
        "adults": [
            {
                "id": "ada",
                "label": "Ada",
                "birth": "1990-09-01",
                "gross_salary": 0,
                "salary_growth": 0,
                "depot": 0,
                "sparrate": 0,
                "kaltmiete": 0,
                "pension_gross_today": 0,
            }
        ],
        "horizon": {"adult_id": "ada", "age": 38},
        "dwelling": {
            "purchase_price": 500_000,
            "bundesland": "Hessen",
            "min_equity": False,
            "owner_costs": 0,
        },
        "beliefs": {
            "household_rate": False,
            "etf_return": 0,
            "inflation": 0,
            "rent_growth": 0,
            "basiszins": 0,
            "sollzins": 0.03,
            "anschlusszins": 0.03,
        },
    }


def test_compare_ok_only_when_chat_header(tmp_path, monkeypatch):
    monkeypatch.setenv("BUY_VS_RENT_COUNTS_FILE", str(tmp_path / "counts.json"))
    client = TestClient(app)
    body = _minimal_compare_body()
    assert client.post("/api/compare", json=body).status_code == 200
    assert recent_days(last=1)[0][1]["compare_ok"] == 0
    assert (
        client.post("/api/compare", json=body, headers={COMPARE_COUNT_HEADER: "chat"}).status_code == 200
    )
    assert recent_days(last=1)[0][1]["compare_ok"] == 1


def test_zahlen_ok_on_lan_host(tmp_path, monkeypatch):
    monkeypatch.setenv("BUY_VS_RENT_COUNTS_FILE", str(tmp_path / "counts.json"))
    client = TestClient(app)
    response = client.get("/zahlen", headers={"Host": "192.168.178.10:8000"})
    assert response.status_code == 200
    assert "Tageszahlen" in response.text
    assert "<table" in response.text

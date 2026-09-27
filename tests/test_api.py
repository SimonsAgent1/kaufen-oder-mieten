import base64
import json
import logging
from datetime import date

import pytest
from fastapi.testclient import TestClient

from buy_vs_rent.api import app
from buy_vs_rent.rates import MarketRate
from buy_vs_rent.scenario import Scenario

client = TestClient(app)


def _body(**beliefs):
    base_beliefs = {
        "household_rate": False,
        "etf_return": 0,
        "inflation": 0,
        "rent_growth": 0,
        "basiszins": 0,
        "sollzins": 0.03,
        "anschlusszins": 0.03,
    }
    base_beliefs.update(beliefs)
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
        "beliefs": base_beliefs,
    }


def test_invalid_purchase_price_is_422():
    body = _body()
    body["dwelling"]["purchase_price"] = -1
    response = client.post("/api/compare", json=body)
    assert response.status_code == 422
    assert response.json()["detail"]


def test_a_third_adult_is_rejected():
    body = _body()
    body["adults"] = body["adults"] * 3
    for index, adult in enumerate(body["adults"]):
        adult["id"] = f"p{index}"
    response = client.post("/api/compare", json=body)
    assert response.status_code == 422


def test_stated_sollzins_stays_and_anschlusszins_follows(monkeypatch):
    monkeypatch.setattr(
        "buy_vs_rent.api.fetch_market_rate",
        lambda years: MarketRate(0.04, "2026-08", "series", "bundesbank"),
    )
    body = _body(sollzins=0.01, anschlusszins=None)
    body["horizon"] = {"adult_id": "ada", "age": 37}
    response = client.post("/api/compare", json=body)
    payload = response.json()
    assert response.status_code == 200
    assert payload["sollzins_used"] == 0.01
    assert payload["anschlusszins_used"] == 0.01


def test_open_rate_applies_beleihung_spread(monkeypatch):
    monkeypatch.setattr(
        "buy_vs_rent.api.fetch_market_rate",
        lambda years: MarketRate(0.04, "2026-08", "series", "bundesbank"),
    )
    body = _body(sollzins=None, anschlusszins=None, household_rate=False)
    body["adults"][0]["depot"] = 400_000
    body["equity_cash"] = 0
    body["dwelling"]["purchase_price"] = 200_000
    body["dwelling"]["notary_rate"] = 0
    body["dwelling"]["broker_rate"] = 0
    body["dwelling"]["transfer_tax"] = 0
    response = client.post("/api/compare", json=body)
    payload = response.json()
    assert response.status_code == 200
    assert payload["loan_at_purchase"] == 0
    assert payload["sollzins_used"] == pytest.approx(0.04 - 0.0015)
    assert payload["anschlusszins_used"] == payload["sollzins_used"]
    assert payload["market_period"] == "2026-08"


def test_household_toggle_discounts_two_adults_more_than_one(monkeypatch):
    monkeypatch.setattr(
        "buy_vs_rent.api.fetch_market_rate",
        lambda years: MarketRate(0.04, "2026-08", "series", "bundesbank"),
    )

    def priced(adults):
        body = _body(sollzins=None, anschlusszins=None, household_rate=True)
        body["adults"] = adults
        body["adults"][0]["depot"] = 400_000
        body["dwelling"].update(
            {"purchase_price": 200_000, "notary_rate": 0, "broker_rate": 0, "transfer_tax": 0}
        )
        if len(adults) == 2:
            body["together_from"] = "2020-01-01"
            body["horizon"] = {"adult_id": "ada", "age": 37}
        return client.post("/api/compare", json=body).json()

    one = _body()["adults"]
    two = [
        one[0],
        {
            "id": "ben",
            "label": "Ben",
            "birth": "1992-09-01",
            "gross_salary": 0,
            "depot": 0,
            "sparrate": 0,
            "kaltmiete": 0,
            "pension_gross_today": 0,
            "salary_growth": 0,
        },
    ]
    couple = priced(two)
    solo = priced(one)
    assert couple["sollzins_used"] == pytest.approx(0.04 - 0.0015 - 0.0010)
    assert solo["sollzins_used"] == pytest.approx(0.04 - 0.0015 - 0.0005)
    assert "Geschlecht" in " ".join(couple["rate_steps"])


def test_property_link_drops_income():
    payload = {
        "purchase_price": 350_000,
        "bundesland": "Bayern",
        "notary_rate": 0.02,
        "broker_rate": 0.0357,
        "owner_costs": 180,
        "gross_salary": 200_000,
        "birth": "1980-01-01",
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    response = client.get("/api/wohnung", params={"data": encoded})
    assert response.status_code == 200
    body = response.json()
    assert body["purchase_price"] == 350_000
    assert body["bundesland"] == "Bayern"
    assert body["notary_rate"] == 0.02
    assert body["broker_rate"] == 0.0357
    assert body["owner_costs"] == 180
    assert "gross_salary" not in body
    assert "birth" not in body
    assert "move_in_cost_2026" not in body


def test_property_link_drops_move_in_cost():
    payload = {
        "purchase_price": 350_000,
        "bundesland": "Bayern",
        "move_in_cost_2026": 40_000,
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    response = client.get("/api/wohnung", params={"data": encoded})
    assert response.status_code == 200
    assert response.json().get("move_in_cost_2026") is None


def test_profile_is_unread_when_the_env_var_is_unset(monkeypatch):
    monkeypatch.delenv("BUY_VS_RENT_PROFILE", raising=False)
    response = client.get("/api/profile")
    assert response.status_code == 404


def test_profile_loads_only_the_env_path(monkeypatch, tmp_path):
    path = tmp_path / "own.yaml"
    path.write_text(
        """
version: 1
as_of: 2026-09-01
adults:
  - id: ada
    label: Ada
    birth: 1990-03-01
    gross_salary: 42000
    depot: 1000
    sparrate: 100
    kaltmiete: 600
dwelling:
  purchase_price: 250000
  bundesland: Bayern
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("BUY_VS_RENT_PROFILE", str(path))
    response = client.get("/api/profile")
    assert response.status_code == 200
    assert response.json()["adults"][0]["gross_salary"] == 42000
    assert date.fromisoformat(response.json()["as_of"])


def test_version_endpoint_matches_installed_package():
    from importlib.metadata import version

    response = client.get("/api/version")
    assert response.status_code == 200
    assert response.json()["version"] == version("buy-vs-rent")


def test_impressum_page_is_served():
    response = client.get("/impressum")
    assert response.status_code == 200
    assert "Impressum" in response.text
    assert "HTTPS" in response.text


def test_church_tax_without_consent_is_422():
    body = _body()
    body["adults"][0]["church_tax"] = True
    body["adults"][0]["church_tax_consent"] = False
    response = client.post("/api/compare", json=body)
    assert response.status_code == 422
    assert "Einwilligung" in response.json()["detail"]


def test_compare_log_line_omits_scenario_body(monkeypatch, caplog):
    monkeypatch.setattr(
        "buy_vs_rent.api.fetch_market_rate",
        lambda years: MarketRate(0.03, "2026-08", "series", "bundesbank"),
    )
    body = _body()
    body["adults"][0]["label"] = "Fiktiv"
    body["adults"][0]["gross_salary"] = 65_000
    with caplog.at_level(logging.INFO, logger="buy_vs_rent.access"):
        response = client.post("/api/compare", json=body)
    assert response.status_code == 200
    compare_logs = [r for r in caplog.records if r.name == "buy_vs_rent.access"]
    assert len(compare_logs) == 1
    message = compare_logs[0].getMessage()
    assert "compare status=200" in message
    assert "Fiktiv" not in message
    assert "1990" not in message
    assert "65000" not in message
    assert "gross_salary" not in message
    assert json.dumps(body) not in message

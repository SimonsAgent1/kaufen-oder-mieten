import pytest

from buy_vs_rent.gifts import (
    gift_tax_parents,
    parent_loan_interest_monthly,
    parent_loan_interest_remaining,
    parent_loan_principal_monthly,
    parent_support_cash,
)
from buy_vs_rent.scenario import Scenario
from buy_vs_rent.simulate import compare


def test_gift_tax_20_000_is_zero():
    assert gift_tax_parents(20_000) == 0


def test_gift_tax_900_000_is_7_000():
    assert gift_tax_parents(900_000) == 7_000


def test_parent_loan_adds_cash_without_tax():
    scenario = Scenario.model_validate(
        {
            "as_of": "2026-09-01",
            "adults": [
                {
                    "id": "ada",
                    "label": "Ada",
                    "birth": "1990-09-01",
                    "gross_salary": 0,
                    "depot": 0,
                    "sparrate": 0,
                    "kaltmiete": 0,
                }
            ],
            "equity_cash": 0,
            "parent_loan": True,
            "parent_loan_amount": 50_000,
            "dwelling": {"purchase_price": 400_000, "bundesland": "Hessen"},
        }
    )
    cash, gift_tax, loan = parent_support_cash(scenario)
    assert gift_tax == 0
    assert loan == 50_000
    assert cash == 50_000


def test_parent_loan_interest_remaining_hand_worked():
    assert parent_loan_interest_remaining(100_000, 0.03, 24) == 6_000.0


def test_parent_loan_interest_monthly_hand_worked():
    assert parent_loan_interest_monthly(100_000, 0.03) == 250.0
    assert parent_loan_interest_monthly(50_000, 0) == 0.0


def test_parent_loan_principal_monthly_hand_worked():
    assert parent_loan_principal_monthly(100_000, 0.02) == pytest.approx(166.67, rel=0, abs=0.1)
    assert parent_loan_principal_monthly(100_000, 0) == 0.0


def test_parent_loan_rate_default_zero_in_saved_file():
    scenario = Scenario.model_validate(
        {
            "as_of": "2026-09-01",
            "adults": [
                {
                    "id": "ada",
                    "label": "Ada",
                    "birth": "1990-09-01",
                    "gross_salary": 50_000,
                    "depot": 0,
                    "sparrate": 0,
                    "kaltmiete": 800,
                }
            ],
            "parent_loan": True,
            "parent_loan_amount": 100_000,
            "dwelling": {"purchase_price": 400_000, "bundesland": "Hessen"},
        }
    )
    assert scenario.parent_loan_rate == 0.0
    assert scenario.parent_loan_tilgung == 0.0


def _loan_scenario(rate: float) -> Scenario:
    return Scenario.model_validate(
        {
            "as_of": "2026-09-01",
            "adults": [
                {
                    "id": "ada",
                    "label": "Ada",
                    "birth": "1990-09-01",
                    "gross_salary": 80_000,
                    "depot": 20_000,
                    "sparrate": 500,
                    "kaltmiete": 1_000,
                }
            ],
            "parent_loan": True,
            "parent_loan_amount": 100_000,
            "parent_loan_rate": rate,
            "dwelling": {"purchase_price": 400_000, "bundesland": "Hessen", "min_equity": False},
            "beliefs": {"etf_return": 0, "sollzins": 0, "anschlusszins": 0, "inflation": 0},
            "horizon": {"adult_id": "ada", "age": 85},
        }
    )


def test_parent_loan_rate_zero_matches_interest_free_loan():
    free = compare(_loan_scenario(0))
    explicit = compare(_loan_scenario(0.0))
    assert free.buy_final_nominal == explicit.buy_final_nominal
    assert free.rent_final_nominal == explicit.rent_final_nominal


def test_loan_chart_includes_parent_principal_and_interest():
    result = compare(_loan_scenario(0.03))
    assert result.series
    mid = result.series[len(result.series) // 2]
    assert mid.loan_balance > 100_000


def test_parent_loan_tilgung_raises_final_wealth():
    no_pay = compare(_loan_scenario(0))
    with_tilgung = compare(
        Scenario.model_validate(
            {**_loan_scenario(0).model_dump(mode="json"), "parent_loan_tilgung": 0.02}
        )
    )
    assert with_tilgung.buy_final_nominal > no_pay.buy_final_nominal


def test_parent_loan_tilgung_appears_in_buy_flow_chart():
    result = compare(
        Scenario.model_validate(
            {**_loan_scenario(0.03).model_dump(mode="json"), "parent_loan_tilgung": 0.02}
        )
    )
    assert result.purchase_date
    after = [
        point
        for point in result.cashflow
        if point.date >= result.purchase_date[:7] and point.buy_parent_principal > 100
    ]
    assert after
    bank_only = [
        point
        for point in result.cashflow
        if point.date >= result.purchase_date[:7] and point.buy_principal > 100
    ]
    assert bank_only


def test_parent_loan_payoff_marker_when_tilgung_positive():
    result = compare(
        Scenario.model_validate(
            {
                **_loan_scenario(0).model_dump(mode="json"),
                "parent_loan_amount": 12_000,
                "parent_loan_tilgung": 0.1,
            }
        )
    )
    labels = [marker.label for marker in result.markers if marker.chart == "loan"]
    assert "Darlehen abbezahlt" in labels


def test_parent_loan_rate_reduces_both_paths():
    free = compare(_loan_scenario(0))
    with_interest = compare(_loan_scenario(0.03))
    assert with_interest.buy_final_nominal < free.buy_final_nominal
    mid = len(free.series) // 2
    assert with_interest.series[mid].rent_nominal < free.series[mid].rent_nominal

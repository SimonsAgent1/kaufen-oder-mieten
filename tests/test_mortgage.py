import pytest

from buy_vs_rent.mortgage import (
    balance_after,
    closed_form_balance,
    initial_payment,
    payment_to_clear,
    step_month,
)
from buy_vs_rent.tax_rates import purchase_costs


def test_unpaid_interest_is_added_to_the_balance():
    interest, principal, balance = step_month(10_000, 0.12, 50)
    assert interest == 100
    assert principal == -50
    assert balance == 10_050


def test_first_month_of_100k_at_3_percent_and_2_percent_tilgung():
    payment = initial_payment(100_000, 0.03, 0.02)
    interest, principal, balance = step_month(100_000, 0.03, payment)
    assert payment == 100_000 * 0.05 / 12
    assert interest == 250
    assert principal == payment - 250
    assert balance == 100_000 - principal


def test_restschuld_after_ten_years_matches_closed_form():
    payment = initial_payment(100_000, 0.03, 0.02)
    stepped = balance_after(100_000, 0.03, payment, 120)
    closed = closed_form_balance(100_000, 0.03, payment, 120)
    assert stepped == pytest.approx(closed)
    assert 70_000 < stepped < 95_000


def test_payment_to_clear_reaches_zero():
    payment = payment_to_clear(100_000, 0.12, 36)
    assert balance_after(100_000, 0.12, payment, 36) == pytest.approx(0, abs=0.01)


def test_loan_pays_off():
    payment = initial_payment(10_000, 0.01, 0.2)
    balance = 10_000
    months = 0
    while balance > 1e-6 and months < 600:
        _, _, balance = step_month(balance, 0.01, payment)
        months += 1
    assert balance == 0
    assert months < 120


def test_payment_changes_after_zinsbindung():
    from datetime import date

    from buy_vs_rent.scenario import Scenario
    from buy_vs_rent.simulate import compare

    early = compare(
        Scenario.model_validate(
            {
                "as_of": date(2026, 9, 1),
                "adults": [
                    {
                        "id": "ada",
                        "birth": date(1990, 9, 1),
                        "gross_salary": 0,
                        "label": "Ada",
                        "depot": 50_000,
                        "sparrate": 0,
                        "kaltmiete": 0,
                        "pension_gross_today": 0,
                        "salary_growth": 0,
                    }
                ],
                "horizon": {"adult_id": "ada", "age": 39},
                "dwelling": {
                    "purchase_price": 200_000,
                    "bundesland": "Bayern",
                    "notary_rate": 0,
                    "broker_rate": 0,
                    "transfer_tax": 0,
                    "owner_costs": 0,
                    "owner_cost_growth": 0,
                    "appreciation": 0,
                    "min_equity": False,
                },
                "beliefs": {
                    "sollzins": 0.02,
                    "anschlusszins": 0.08,
                    "zinsbindung_years": 1,
                    "etf_return": 0,
                    "ter": 0,
                    "basiszins": 0,
                    "inflation": 0,
                    "rent_growth": 0,
                    "household_rate": False,
                },
            }
        )
    )
    assert early.restschuld_at_fixation is not None
    assert early.fixation_end is not None
    assert early.monthly_payment_at_purchase > 0


def test_hessen_nebenkosten_on_500k():
    costs = purchase_costs(500_000, 0.06, 0.02, 0.0357)
    assert costs == 57_850

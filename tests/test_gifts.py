from buy_vs_rent.gifts import gift_tax_parents, parent_support_cash
from buy_vs_rent.scenario import Scenario


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

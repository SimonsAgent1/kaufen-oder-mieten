import inspect
from datetime import date
from pathlib import Path

import pytest

from buy_vs_rent import etf, house, mortgage
from buy_vs_rent.catalog import by_function, render_rules
from buy_vs_rent.etf import Portfolio, capital_gains_rate
from buy_vs_rent.house import comparison_cold_rent_monthly, monthly_owner_costs, owner_occupied_exemption, price_to_rent_band
from buy_vs_rent.scenario import Scenario
from buy_vs_rent.law import de_2026
from buy_vs_rent.law.de_2026 import (
    child_rearing_entgeltpunkte,
    church_tax_rate,
    elterngeld_month,
    kindergeld_until_age,
    kinder_freibetrag_refund,
    monthly_net,
    solidarity,
    taxable_income,
)
from buy_vs_rent.mortgage import initial_payment, step_month

ROOT = Path(__file__).resolve().parents[1]


def _public(module, prefix: str) -> list[str]:
    found = []
    for name, obj in inspect.getmembers(module):
        if name.startswith("_"):
            continue
        if inspect.isfunction(obj) and obj.__module__ == module.__name__:
            found.append(f"{prefix}.{name}")
        elif inspect.isclass(obj) and obj.__module__ == module.__name__:
            for method_name, method in inspect.getmembers(obj):
                if method_name.startswith("_"):
                    continue
                if inspect.isfunction(method):
                    found.append(f"{prefix}.{name}.{method_name}")
    return found


def test_every_public_formula_has_a_catalog_entry():
    needed = (
        _public(de_2026, "law.de_2026")
        + _public(mortgage, "mortgage")
        + _public(etf, "etf")
        + _public(house, "house")
    )
    covered = set(by_function())
    assert [name for name in needed if name not in covered] == []


def test_rules_page_is_the_catalog():
    assert (ROOT / "docs" / "rules.md").read_text(encoding="utf-8") == render_rules()


def test_december_2020_purchase_sold_in_january_2021_is_exempt():
    assert owner_occupied_exemption(date(2020, 12, 1), date(2021, 1, 1))
    assert kindergeld_until_age(True) == 25
    assert child_rearing_entgeltpunkte(date(1992, 1, 1), date(2000, 1, 1)) == 6.0


def test_worked_examples_match_the_functions():
    assert church_tax_rate("Bayern") == 0.08
    assert church_tax_rate("Hessen") == 0.09
    assert initial_payment(120_000, 0.03, 0.02) == 500
    assert step_month(120_000, 0.03, 500)[0] == 300
    assert monthly_owner_costs(400_000, 0.0075) == 250
    assert comparison_cold_rent_monthly(
        Scenario.model_validate(
            {
                "as_of": date(2026, 9, 1),
                "adults": [
                    {
                        "id": "a1",
                        "birth": date(1990, 9, 1),
                        "work_start": date(2015, 9, 1),
                        "gross_salary": 0,
                        "depot": 0,
                        "sparrate": 0,
                        "kaltmiete": 800,
                        "care_age": 85,
                    }
                ],
                "equity_cash": 0,
                "horizon": {"adult_id": "a1", "age": 90},
                "dwelling": {"purchase_price": 400_000, "bundesland": "Hessen"},
                "extra_rent": {"amount_2026": 200, "from": date(2026, 9, 1), "until": date(2030, 9, 1)},
            }
        )
    ) == 800
    assert price_to_rent_band(19.9) == "unter 20"
    assert price_to_rent_band(22) == "20 bis 25"
    assert price_to_rent_band(26) == "über 25"
    assert monthly_net(60_000, church_rate=0.09) < monthly_net(60_000)
    assert owner_occupied_exemption(date(2020, 12, 1), date(2021, 1, 15))
    assert owner_occupied_exemption(date(2020, 12, 1), date(2022, 1, 1))
    assert owner_occupied_exemption(date(2020, 1, 1), date(2022, 12, 1))
    zve = taxable_income(40_000)
    assert kinder_freibetrag_refund(zve, [(4 * 259, 4)]) == 0
    assert solidarity(25_000) == pytest.approx(553.35, abs=0.05)
    assert solidarity(25_000) < 25_000 * 0.055
    pot = Portfolio(10_000, annual_return=0, ter=0, basiszins=0, allowance=0, tax_rate=capital_gains_rate())
    assert pot.vorabpauschale_tax() == 0
    assert pot.basis == 10_000
    assert elterngeld_month(1_000, 1, True) == pytest.approx(670)
    capped = Portfolio(1_000, annual_return=0, ter=0, basiszins=0.1, allowance=0, tax_rate=capital_gains_rate())
    capped.value = 1_010
    capped.year_fraction = 1
    capped.vorabpauschale_tax()
    assert capped.basis == pytest.approx(1_010)

"""One fictional household, followed from work through care."""

import math
from datetime import date

from buy_vs_rent.scenario import Scenario
from buy_vs_rent.simulate import compare


def _life() -> Scenario:
    return Scenario.model_validate(
        {
            "version": 1,
            "as_of": date(2026, 1, 1),
            "adults": [
                {
                    "id": "ada",
                    "label": "Ada",
                    "birth": date(1988, 3, 1),
                    "work_start": date(2012, 4, 1),
                    "retire_age": 67,
                    "care_age": 75,
                    "gross_salary": 52_000,
                    "salary_growth": 0.01,
                    "depot": 15_000,
                    "sparrate": 300,
                    "kaltmiete": 700,
                    "pension_gross_today": 1_400,
                },
                {
                    "id": "ben",
                    "label": "Ben",
                    "birth": date(1991, 6, 1),
                    "work_start": date(2016, 9, 1),
                    "retire_age": 67,
                    "care_age": 75,
                    "gross_salary": 48_000,
                    "salary_growth": 0.01,
                    "depot": 8_000,
                    "sparrate": 200,
                    "kaltmiete": 650,
                    "pension_gross_today": 1_200,
                },
            ],
            "together_from": date(2024, 6, 1),
            "married_from": date(2025, 6, 1),
            "shared_kaltmiete": 1_200,
            "children": [
                {
                    "id": "kind",
                    "birth": date(2027, 4, 1),
                    "room_until_age": 20,
                    "leave": [
                        {"adult_id": "ada", "months": 8},
                        {"adult_id": "ben", "months": 4},
                    ],
                }
            ],
            "equity_cash": 40_000,
            "horizon": {"adult_id": "ben", "age": 90},
            "care_copay_2026": 5_800,
            "dwelling": {
                "purchase_price": 350_000,
                "bundesland": "Hessen",
                "owner_costs": 250,
                "min_equity": True,
            },
            "beliefs": {
                "rent_growth": 0.02,
                "etf_return": 0.04,
                "ter": 0.0015,
                "basiszins": 0.02,
                "inflation": 0.02,
                "sollzins": 0.035,
                "anschlusszins": 0.035,
                "tilgung": 0.02,
                "zinsbindung_years": 15,
                "household_rate": False,
                "church_tax": False,
            },
        }
    )


def test_a_household_stays_coherent_through_work_retirement_and_care():
    result = compare(_life())
    assert result.purchase_date is not None
    assert result.purchase_date < "2055-03-01"
    assert result.loan_at_purchase > 0
    assert result.care_start == "2063-03-01"
    assert result.horizon_end == "2081-06-01"
    assert result.purchase_date < result.care_start < result.horizon_end

    for amount in (
        result.buy_final_nominal,
        result.rent_final_nominal,
        result.buy_final_real,
        result.rent_final_real,
        result.interest_paid,
    ):
        assert math.isfinite(amount)
    assert result.interest_paid > 0
    assert result.price_to_rent == 350_000 / (1_200 * 12)

    by_year = {point.date[:4]: point for point in result.cashflow}
    assert by_year["2056"].rent_etf > 0
    assert by_year["2060"].rent_etf == 0
    assert by_year["2060"].rent_draw > 0
    both = [
        point.date
        for point in result.cashflow
        if (point.rent_etf > 1 and point.rent_draw > 1) or (point.buy_etf > 1 and point.buy_draw > 1)
    ]
    assert both == []

    after_care = [point for point in result.series if point.date >= result.care_start]
    assert after_care
    assert all(point.property_value == 0 for point in after_care)
    assert all(point.loan_balance == 0 for point in after_care)

    labels = [marker.label for marker in result.markers]
    assert any("Kauf" in label for label in labels)
    assert any("Pflege" in label for label in labels)
    assert any("Ada Rente" in label for label in labels)
    assert any("Ben Rente" in label for label in labels)
    assert any("Kirchensteuer ist für niemanden an." == line for line in result.assumptions)
    assert any("Kindererziehungszeiten" in line for line in result.assumptions)
    assert all("Darmstadt" not in line for line in result.assumptions)


def test_care_gap_is_after_the_sale_and_the_life_sentence_names_the_dates():
    """Care wealth is the first point after the sale, not the year before it."""
    result = compare(_life())
    text = result.life_sentence
    assert text.startswith("Ada und Ben wohnen ab 01.06.2024 zusammen.")
    assert "Kind 1 ab 01.04.2027." in text
    assert "Ada spart bis 01.03.2055." in text
    assert "Ben spart bis 01.06.2058." in text
    assert text.endswith("Das Haus oder die Wohnung wird 01.03.2063 verkauft.")
    assert "wichtig" not in text.lower()
    after_sale = next(
        point for point in result.series if point.date >= result.care_start and point.property_value == 0
    )
    assert result.care_buy_real == after_sale.buy_real
    assert result.care_rent_real == after_sale.rent_real
    assert result.buy_final_real != result.care_buy_real
    assert result.rent_final_real != result.care_rent_real

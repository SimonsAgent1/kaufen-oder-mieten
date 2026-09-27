from datetime import date

from buy_vs_rent.house import owner_occupied_exemption
from buy_vs_rent.law.de_2026 import child_rearing_entgeltpunkte, kindergeld_until_age
from buy_vs_rent.scenario import Child, Leave, Scenario, default_child_rearing_adult_id


def _two_adults_scenario(**kwargs) -> Scenario:
    base = {
        "version": 1,
        "as_of": date(2026, 9, 1),
        "adults": [
            {
                "id": "a1",
                "birth": date(1990, 3, 1),
                "work_start": date(2015, 9, 1),
                "gross_salary": 50_000,
                "depot": 10_000,
                "sparrate": 200,
                "kaltmiete": 700,
                "care_age": 75,
            },
            {
                "id": "a2",
                "birth": date(1992, 11, 1),
                "work_start": date(2018, 1, 1),
                "gross_salary": 45_000,
                "depot": 5_000,
                "sparrate": 150,
                "kaltmiete": 700,
                "care_age": 75,
            },
        ],
        "together_from": date(2024, 6, 1),
        "shared_kaltmiete": 1_400,
        "equity_cash": 5_000,
        "horizon": {"adult_id": "a2", "age": 90},
        "dwelling": {"purchase_price": 400_000, "bundesland": "Bayern"},
    }
    base.update(kwargs)
    return Scenario.model_validate(base)


def test_kindergeld_until_age_defaults():
    assert kindergeld_until_age(True) == 25
    assert kindergeld_until_age(False) == 18


def test_child_rearing_entgeltpunkte_by_birth():
    assert child_rearing_entgeltpunkte() == 0.0
    assert child_rearing_entgeltpunkte(date(1992, 1, 1)) == 3.0
    assert child_rearing_entgeltpunkte(date(1991, 12, 1)) == 2.0
    assert child_rearing_entgeltpunkte(date(1991, 12, 1), date(2000, 6, 1)) == 5.0


def test_default_child_rearing_adult_follows_elternzeit():
    scenario = _two_adults_scenario(
        children=[
            Child(
                id="k1",
                birth=date(2028, 4, 1),
                leave=[
                    Leave(adult_id="a1", months=4),
                    Leave(adult_id="a2", months=8),
                ],
            )
        ]
    )
    assert default_child_rearing_adult_id(scenario) == "a2"


def test_owner_occupied_exemption_respects_own_use_flag():
    purchase = date(2020, 12, 1)
    sale = date(2021, 1, 1)
    assert owner_occupied_exemption(purchase, sale, exclusive_own_use_until_sale=True)
    assert not owner_occupied_exemption(purchase, sale, exclusive_own_use_until_sale=False)

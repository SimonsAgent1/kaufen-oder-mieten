from datetime import date

import pytest

from buy_vs_rent.bounds import validate_scenario
from buy_vs_rent.scenario import Scenario


def _minimal(**kwargs) -> Scenario:
    body = {
        "as_of": date(2026, 9, 1),
        "adults": [
            {
                "id": "a1",
                "label": "Ada",
                "birth": date(1990, 9, 1),
                "work_start": date(2015, 9, 1),
                "retire_age": 67,
                "care_age": 75,
                "gross_salary": 50_000,
                "depot": 10_000,
                "sparrate": 200,
                "kaltmiete": 800,
            }
        ],
        "horizon": {"adult_id": "a1", "age": 85},
        "dwelling": {"purchase_price": 400_000, "bundesland": "Hessen"},
        "beliefs": {"household_rate": False, "sollzins": 0.03, "anschlusszins": 0.03},
    }
    body.update(kwargs)
    return Scenario.model_validate(body)


def test_future_adult_birth_is_rejected():
    adult = _minimal().adults[0].model_dump()
    adult["birth"] = date(2027, 1, 1)
    with pytest.raises(ValueError, match="Geburtsmonat"):
        _minimal(adults=[adult])


def test_retire_age_outside_55_to_75_is_rejected():
    adult = _minimal().adults[0].model_dump()
    adult["retire_age"] = 54
    with pytest.raises((ValueError, Exception), match="55"):
        _minimal(adults=[adult])


def test_horizon_before_start_month_is_rejected():
    with pytest.raises((ValueError, Exception), match="Endalter"):
        _minimal(horizon={"adult_id": "a1", "age": 36})


def test_validate_scenario_accepts_a_coherent_household():
    validate_scenario(_minimal())

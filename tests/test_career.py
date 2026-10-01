"""Career segments and Arbeitslosengeld."""

from datetime import date

from buy_vs_rent.career import (
    arbeitslosengeld_benefit,
    arbeitslosengeld_months,
    employment_for_month,
    job_employment_for_month,
)
from buy_vs_rent.law.de_2026 import monthly_net
from buy_vs_rent.scenario import Adult, Scenario


def _adult(**kwargs) -> Adult:
    data = {
        "id": "ada",
        "birth": date(1990, 1, 1),
        "work_start": date(2015, 1, 1),
        "gross_salary": 60_000,
        "salary_growth": 0,
        "depot": 0,
        "sparrate": 0,
        "kaltmiete": 0,
    }
    data.update(kwargs)
    return Adult.model_validate(data)


def test_arbeitslosengeld_benefit_invented_example():
    assert arbeitslosengeld_benefit(3_000, False) == 1_800
    assert round(arbeitslosengeld_benefit(3_000, True)) == 2_010


def test_arbeitslosengeld_duration_by_age():
    assert arbeitslosengeld_months(49) == 12
    assert arbeitslosengeld_months(52) == 15
    assert arbeitslosengeld_months(56) == 18
    assert arbeitslosengeld_months(60) == 24


def test_job_change_replaces_gross_from_switch_month():
    adult = _adult(
        job_changes=[
            {"start": "2028-01-01", "gross_salary": 48_000, "salary_growth": 0},
        ]
    )
    scenario = Scenario.model_validate(
        {
            "as_of": date(2026, 1, 1),
            "adults": [adult],
            "dwelling": {"purchase_price": 400_000, "bundesland": "Hessen"},
        }
    )
    before = job_employment_for_month(adult, date(2027, 12, 1), 1, inflation_factor=1.0, pv_rate=0.018, church_rate=0)
    after = job_employment_for_month(adult, date(2028, 1, 1), 2, inflation_factor=1.0, pv_rate=0.018, church_rate=0)
    assert before.gross == 60_000
    assert after.gross == 48_000


def test_unemployment_pays_alg_then_zero_until_next_job():
    adult = _adult(
        gross_salary=60_000,
        job_changes=[{"start": "2029-01-01", "gross_salary": 48_000, "salary_growth": 0}],
        unemployment=[{"start": "2027-01-01"}],
    )
    scenario = Scenario.model_validate(
        {
            "as_of": date(2026, 1, 1),
            "adults": [adult],
            "dwelling": {"purchase_price": 400_000, "bundesland": "Hessen"},
        }
    )
    alg = employment_for_month(
        adult,
        date(2027, 1, 1),
        scenario,
        years_since_as_of=1,
        inflation_factor=1.0,
        pv_rate=0.018,
        church_rate=0,
        has_child_in_household=False,
    )
    prev = job_employment_for_month(adult, date(2026, 12, 1), 0, inflation_factor=1.0, pv_rate=0.018, church_rate=0)
    assert abs(alg.net - arbeitslosengeld_benefit(prev.net, False)) < 5
    gap = employment_for_month(
        adult,
        date(2028, 2, 1),
        scenario,
        years_since_as_of=2,
        inflation_factor=1.0,
        pv_rate=0.018,
        church_rate=0,
        has_child_in_household=False,
    )
    assert gap.gross == 0.0
    assert gap.net == 0.0
    new_job = employment_for_month(
        adult,
        date(2029, 1, 1),
        scenario,
        years_since_as_of=2,
        inflation_factor=1.0,
        pv_rate=0.018,
        church_rate=0,
        has_child_in_household=False,
    )
    assert new_job.gross == 48_000

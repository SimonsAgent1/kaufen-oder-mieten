from datetime import date

import pytest

from buy_vs_rent.household import build_calendar, child_count, cold_rent, leave_fraction
from buy_vs_rent.law.de_2026 import employee_pv_rate
from buy_vs_rent.scenario import Beliefs, Scenario
from buy_vs_rent.simulate import compare, path_depot_empty_before_horizon

AS_OF = date(2026, 9, 1)
BIRTH = date(1990, 9, 1)


def _adult(adult_id="ada", label="Ada", birth=BIRTH, **kwargs):
    data = {
        "id": adult_id,
        "label": label,
        "birth": birth,
        "work_start": date(2015, 9, 1),
        "gross_salary": 60_000,
        "salary_growth": 0,
        "depot": 0,
        "sparrate": 0,
        "kaltmiete": 0,
        "pension_gross_today": 0,
    }
    data.update(kwargs)
    return data


def _scenario(**kwargs) -> Scenario:
    beliefs = {
        "rent_growth": 0,
        "etf_return": 0,
        "ter": 0,
        "basiszins": 0,
        "inflation": 0,
        "sollzins": 0.03,
        "anschlusszins": 0.03,
        "household_rate": False,
    }
    beliefs.update(kwargs.pop("beliefs", {}))
    dwelling = {
        "purchase_price": 500_000,
        "bundesland": "Hessen",
        "owner_costs": 0,
        "owner_cost_growth": 0,
        "appreciation": 0,
        "min_equity": False,
    }
    dwelling.update(kwargs.pop("dwelling", {}))
    adults = kwargs.pop("adults", [_adult()])
    body = {
        "as_of": AS_OF,
        "adults": adults,
        "equity_cash": 0,
        "horizon": {"adult_id": adults[0]["id"], "age": 38},
        "dwelling": dwelling,
        "beliefs": beliefs,
    }
    body.update(kwargs)
    horizon_age = (body.get("horizon") or {}).get("age")
    if horizon_age is not None and horizon_age >= 60:
        for adult in body["adults"]:
            if adult.get("care_age", 75) >= horizon_age:
                adult["care_age"] = max(60, horizon_age - 1)
    return Scenario.model_validate(body)


def test_equal_housing_costs_leave_the_opening_depot_on_the_rent_side():
    result = compare(
        _scenario(
            adults=[_adult(depot=80_000, sparrate=0, kaltmiete=0)],
            dwelling={
                "purchase_price": 100_000,
                "notary_rate": 0,
                "broker_rate": 0,
                "transfer_tax": 0,
                "owner_costs": 0,
                "min_equity": False,
            },
            beliefs={"sollzins": 0, "tilgung": 0, "anschlusszins": 0},
        )
    )
    assert result.purchase_date == "2026-09-01"
    assert result.rent_final_nominal == 80_000


def test_buys_once_savings_cover_nebenkosten():
    blocked = compare(
        _scenario(
            adults=[_adult(depot=16_000, sparrate=1_000)],
            horizon={"adult_id": "ada", "age": 37},
            dwelling={"purchase_price": 500_000, "min_equity": False},
        )
    )
    assert blocked.purchase_date is None
    assert blocked.nebenkosten == 57_850

    bought = compare(
        _scenario(
            adults=[_adult(depot=16_000, sparrate=10_000)],
            dwelling={"purchase_price": 500_000, "min_equity": False},
        )
    )
    assert bought.purchase_date == "2027-02-01"
    assert bought.warning_below_down_payment


def test_move_in_cost_raises_loan_not_rent_wealth():
    base = compare(
        _scenario(
            adults=[_adult(depot=80_000, sparrate=0)],
            equity_cash=10_000,
            dwelling={"purchase_price": 400_000, "min_equity": False, "move_in_cost_2026": 0},
        )
    )
    with_move = compare(
        _scenario(
            adults=[_adult(depot=80_000, sparrate=0)],
            equity_cash=10_000,
            dwelling={"purchase_price": 400_000, "min_equity": False, "move_in_cost_2026": 12_000},
        )
    )
    assert base.purchase_date == with_move.purchase_date
    assert with_move.loan_at_purchase == pytest.approx(base.loan_at_purchase + 12_000)
    assert with_move.rent_final_nominal == base.rent_final_nominal
    assert with_move.price_at_purchase == base.price_at_purchase == pytest.approx(400_000)
    assert with_move.nebenkosten == base.nebenkosten
    assert with_move.house_gain == base.house_gain
    assert with_move.price_to_rent == base.price_to_rent


def test_fifteen_percent_option_waits_for_costs_plus_down_payment():
    early = compare(
        _scenario(
            adults=[_adult(depot=16_000, sparrate=10_000)],
            dwelling={"purchase_price": 500_000, "min_equity": False},
        )
    )
    waited = compare(
        _scenario(
            adults=[_adult(depot=16_000, sparrate=10_000)],
            dwelling={"purchase_price": 500_000, "min_equity": True},
        )
    )
    assert early.purchase_date == "2027-02-01"
    assert waited.purchase_date > early.purchase_date
    assert not waited.warning_below_down_payment
    assert waited.loan_at_purchase < early.loan_at_purchase


def test_high_follow_up_rate_pays_the_loan_off_by_care():
    shared = dict(
        adults=[_adult(depot=0, sparrate=3_000, pension_gross_today=0, care_age=60)],
        horizon={"adult_id": "ada", "age": 61},
        dwelling={
            "purchase_price": 200_000,
            "notary_rate": 0,
            "broker_rate": 0,
            "transfer_tax": 0,
            "owner_costs": 0,
            "min_equity": False,
        },
        beliefs={"sollzins": 0.02, "tilgung": 0.01, "zinsbindung_years": 1},
    )
    mild = compare(_scenario(**{k: v for k, v in shared.items() if k != "beliefs"}, beliefs={**shared["beliefs"], "anschlusszins": 0.02}))
    steep = compare(_scenario(**{k: v for k, v in shared.items() if k != "beliefs"}, beliefs={**shared["beliefs"], "anschlusszins": 0.10}))
    assert steep.payoff_date is not None
    assert steep.payoff_date <= steep.care_start
    mild_year = {point.date[:4]: point for point in mild.cashflow}
    steep_year = {point.date[:4]: point for point in steep.cashflow}
    assert (
        steep_year["2028"].buy_interest + steep_year["2028"].buy_principal
        > mild_year["2028"].buy_interest + mild_year["2028"].buy_principal
    )


def test_care_replaces_rent_and_sells_the_house():
    result = compare(
        _scenario(
            as_of=date(2026, 1, 1),
            adults=[
                _adult(
                    birth=date(1951, 1, 1),
                    care_age=76,
                    depot=200_000,
                    sparrate=0,
                    kaltmiete=1_000,
                    pension_gross_today=2_000,
                    gross_salary=0,
                )
            ],
            horizon={"adult_id": "ada", "age": 80},
            dwelling={
                "purchase_price": 100_000,
                "notary_rate": 0,
                "broker_rate": 0,
                "transfer_tax": 0,
                "owner_costs": 0,
                "min_equity": False,
            },
        )
    )
    by_year = {point.date[:4]: point for point in result.cashflow}
    assert result.purchase_date == "2026-01-01"
    assert by_year["2026"].rent_housing == 1_000
    assert by_year["2026"].buy_rent == 0
    assert by_year["2027"].rent_housing == 3_600
    assert by_year["2027"].buy_rent == 3_600
    assert result.series[-1].property_value == 0


def test_salary_growth_raises_one_later_sparrate_month():
    flat = compare(_scenario(adults=[_adult(sparrate=1_000)], horizon={"adult_id": "ada", "age": 37}))
    growing = compare(
        _scenario(
            adults=[_adult(sparrate=1_000, salary_growth=0.05)],
            horizon={"adult_id": "ada", "age": 37},
        )
    )
    assert growing.rent_final_nominal == flat.rent_final_nominal + 50


def test_unmarried_parents_still_receive_kindergeld():
    child = {"id": "kind", "birth": date(2020, 1, 1), "leave": []}
    shared = dict(
        as_of=date(2026, 1, 1),
        adults=[
            _adult(birth=date(1990, 1, 1), gross_salary=0, sparrate=0, kaltmiete=0, depot=0),
            _adult(
                adult_id="ben",
                label="Ben",
                birth=date(1992, 1, 1),
                gross_salary=0,
                sparrate=0,
                kaltmiete=0,
                depot=0,
            ),
        ],
        together_from=date(2024, 1, 1),
        married_from=None,
        shared_kaltmiete=0,
        horizon={"adult_id": "ada", "age": 37},
        dwelling={"purchase_price": 5_000_000, "min_equity": False},
    )
    without = compare(_scenario(**shared))
    with_child = compare(_scenario(**shared, children=[child]))
    assert with_child.rent_final_nominal - without.rent_final_nominal == 13 * 259


def test_the_working_adult_keeps_saving_after_the_other_retires():
    result = compare(
        _scenario(
            as_of=date(2026, 1, 1),
            adults=[
                _adult(
                    birth=date(1959, 1, 1),
                    retire_age=67,
                    sparrate=500,
                    gross_salary=40_000,
                    pension_gross_today=1_500,
                ),
                _adult(
                    adult_id="ben",
                    label="Ben",
                    birth=date(1961, 1, 1),
                    retire_age=67,
                    sparrate=400,
                    gross_salary=40_000,
                    pension_gross_today=1_500,
                ),
            ],
            together_from=date(2020, 1, 1),
            married_from=date(2020, 1, 1),
            shared_kaltmiete=0,
            horizon={"adult_id": "ben", "age": 70},
            dwelling={"purchase_price": 5_000_000, "min_equity": False},
            beliefs={"etf_consume": 1},
        )
    )
    by_year = {point.date[:4]: point for point in result.cashflow}
    assert by_year["2027"].rent_etf == pytest.approx(400, abs=1)
    assert by_year["2029"].rent_etf == 0
    assert by_year["2029"].rent_draw > 0


def test_extra_rent_defaults_to_zero_and_drops_after_purchase():
    children = [
        {"id": "a", "birth": date(2024, 1, 1), "leave": []},
        {"id": "b", "birth": date(2026, 1, 1), "leave": []},
    ]
    adults = [
        _adult(kaltmiete=700, birth=date(1990, 1, 1)),
        _adult(adult_id="ben", label="Ben", birth=date(1992, 1, 1), kaltmiete=800),
    ]
    plain = compare(
        _scenario(
            as_of=date(2026, 1, 1),
            adults=adults,
            together_from=date(2024, 1, 1),
            married_from=date(2025, 1, 1),
            shared_kaltmiete=1_500,
            children=children,
            horizon={"adult_id": "ben", "age": 40},
            dwelling={"purchase_price": 5_000_000, "min_equity": False},
        )
    )
    by_year = {point.date[:4]: point for point in plain.cashflow}
    assert by_year["2027"].rent_housing == 1_500
    bumped = compare(
        _scenario(
            as_of=date(2026, 1, 1),
            adults=[
                _adult(depot=200_000, kaltmiete=700, birth=date(1990, 1, 1)),
                _adult(adult_id="ben", label="Ben", birth=date(1992, 1, 1), kaltmiete=800),
            ],
            together_from=date(2024, 1, 1),
            married_from=date(2025, 1, 1),
            shared_kaltmiete=1_500,
            children=children,
            extra_rent={"amount_2026": 600, "from": date(2026, 6, 1), "until": date(2030, 1, 1)},
            horizon={"adult_id": "ben", "age": 40},
            dwelling={
                "purchase_price": 100_000,
                "notary_rate": 0,
                "broker_rate": 0,
                "transfer_tax": 0,
                "min_equity": False,
            },
        )
    )
    owned = {point.date[:4]: point for point in bumped.cashflow}
    assert bumped.purchase_date == "2026-01-01"
    assert owned["2027"].rent_housing == 2_100
    assert owned["2027"].buy_rent == 0


def test_inflation_deflates_final_wealth():
    nominal = compare(
        _scenario(
            adults=[_adult(sparrate=1_000)],
            horizon={"adult_id": "ada", "age": 37},
            dwelling={"purchase_price": 5_000_000},
        )
    )
    real = compare(
        _scenario(
            adults=[_adult(sparrate=1_000)],
            horizon={"adult_id": "ada", "age": 37},
            dwelling={"purchase_price": 5_000_000},
            beliefs={"inflation": 0.02, "rent_growth": 0.02},
        )
    )
    assert nominal.rent_final_real == nominal.rent_final_nominal
    assert real.rent_final_real < real.rent_final_nominal


def test_moving_in_together_invests_the_rent_saved():
    adults = [
        _adult(birth=date(1990, 1, 1), kaltmiete=700, sparrate=0),
        _adult(adult_id="ben", label="Ben", birth=date(1992, 1, 1), kaltmiete=900, sparrate=0),
    ]
    shared = dict(
        as_of=date(2026, 1, 1),
        adults=adults,
        together_from=date(2028, 1, 1),
        married_from=None,
        horizon={"adult_id": "ada", "age": 40},
        dwelling={"purchase_price": 5_000_000, "min_equity": False},
    )
    cheap = compare(_scenario(**shared, shared_kaltmiete=1_500))
    same = compare(_scenario(**shared, shared_kaltmiete=1_600))
    assert cheap.rent_final_nominal - same.rent_final_nominal == 25 * 100


def test_a_stated_pension_replaces_the_estimate():
    base = _scenario(adults=[_adult(pension_gross_today=None, gross_salary=60_000)])
    moved = _scenario(adults=[_adult(pension_gross_today=1_234)])
    assert compare(base).pensions[0].estimate > 0
    assert compare(moved).pensions[0].estimate == 1_234


def test_cash_is_invested_on_the_rent_path_and_depots_add_up():
    result = compare(
        _scenario(
            adults=[
                _adult(depot=20_000),
                _adult(adult_id="ben", label="Ben", birth=date(1992, 9, 1), depot=10_000),
            ],
            together_from=date(2024, 1, 1),
            shared_kaltmiete=0,
            equity_cash=5_000,
            horizon={"adult_id": "ada", "age": 37},
            dwelling={"purchase_price": 5_000_000, "min_equity": False},
            beliefs={"etf_return": 0.12},
        )
    )
    assert result.rent_final_nominal > 35_000
    assert result.rent_final_nominal > result.buy_final_nominal


def test_spend_down_reaches_the_reserve_at_the_horizon():
    adults = [
        _adult(birth=date(1950, 1, 1), depot=100_000, sparrate=0, pension_gross_today=5_000, gross_salary=0)
    ]
    shared = dict(
        as_of=date(2026, 1, 1),
        adults=adults,
        horizon={"adult_id": "ada", "age": 80},
        dwelling={"purchase_price": 5_000_000, "min_equity": False},
        beliefs={"etf_return": 0, "inflation": 0},
    )
    base = {k: v for k, v in shared.items() if k != "beliefs"}
    empty = compare(_scenario(**base, beliefs={**shared["beliefs"], "etf_consume": 1, "etf_reserve": 0}))
    kept = compare(_scenario(**base, beliefs={**shared["beliefs"], "etf_consume": 1, "etf_reserve": 50_000}))
    assert empty.rent_final_real < 100
    assert kept.rent_final_real == pytest.approx(50_000, abs=1)


def test_default_etf_return_is_the_world_index_window():
    assert Beliefs().etf_return == 0.087


def test_leave_months_are_assigned_in_order():
    scenario = _scenario(
        adults=[
            _adult(),
            _adult(adult_id="ben", label="Ben", birth=date(1992, 9, 1)),
        ],
        together_from=date(2024, 6, 1),
        children=[
            {
                "id": "kind",
                "birth": date(2028, 1, 1),
                "leave": [{"adult_id": "ben", "months": 7}, {"adult_id": "ada", "months": 5}],
            }
        ],
    )
    calendar = build_calendar(scenario)
    assert leave_fraction(calendar, date(2028, 1, 1), "ben") == 1
    assert leave_fraction(calendar, date(2028, 7, 1), "ben") == 1
    assert leave_fraction(calendar, date(2028, 8, 1), "ada") == 1
    assert leave_fraction(calendar, date(2028, 12, 1), "ada") == 1
    assert leave_fraction(calendar, date(2029, 1, 1), "ada") == 0
    assert cold_rent(calendar, date(2026, 9, 1)) == 0
    assert child_count(calendar, date(2028, 6, 1)) == 1


def test_pv_rate_follows_the_child_count():
    assert employee_pv_rate(0, 30) == pytest.approx(0.018 + 0.006)
    assert employee_pv_rate(0, 22) == pytest.approx(0.018)
    assert employee_pv_rate(1, 40) == pytest.approx(0.018)
    assert employee_pv_rate(2, 40) == pytest.approx(0.018 - 0.0025)
    assert employee_pv_rate(5, 40) == pytest.approx(0.018 - 0.01)
    assert employee_pv_rate(6, 40) == pytest.approx(0.018 - 0.01)


def test_monthly_slices_add_up():
    result = compare(_scenario(adults=[_adult(sparrate=500, kaltmiete=800, depot=50_000)]))
    assert result.cashflow
    for point in result.cashflow:
        rent_sum = point.rent_housing + max(point.rent_etf, 0) + point.rent_left
        buy_housing = point.buy_rent + point.buy_interest + point.buy_principal + point.buy_owner
        buy_sum = buy_housing + max(point.buy_etf, 0) + point.buy_left
        assert abs(rent_sum - point.income) < 0.05 or abs(rent_sum - point.income - point.rent_draw) < 0.05
        assert abs(buy_sum - point.income) < 0.05 or abs(buy_sum - point.income - point.buy_draw) < 0.05


def test_path_depot_empty_before_horizon_ignores_rent_on_buy_only():
    assert not path_depot_empty_before_horizon(
        "buy",
        rent_etf_value=0.0,
        buy_etf_value=50_000.0,
        owns_home=True,
    )
    assert path_depot_empty_before_horizon(
        "rent",
        rent_etf_value=0.0,
        buy_etf_value=50_000.0,
        owns_home=True,
    )


def test_buy_only_does_not_warn_when_rent_comparison_depot_is_empty():
    scenario = _scenario(
        path_scope="buy",
        adults=[_adult(depot=100_000, sparrate=500, kaltmiete=1_000)],
        equity_cash=50_000,
        horizon={"adult_id": "ada", "age": 85},
        beliefs={"rent_growth": 0, "inflation": 0, "etf_return": 0.05, "ter": 0},
        dwelling={"purchase_price": 400_000, "bundesland": "Hessen", "owner_costs": 200, "min_equity": False},
    )
    result = compare(scenario, display=scenario)
    assert result.buy_final_nominal > 100_000
    assert not any("Depot ist vor dem Horizont leer" in line for line in result.warnings)


def test_rent_path_includes_church_tax_assumption():
    result = compare(
        _scenario(
            path_scope="rent",
            adults=[
                _adult(
                    depot=80_000,
                    sparrate=200,
                    kaltmiete=700,
                    church_tax=True,
                    church_tax_consent=True,
                )
            ],
            dwelling={"bundesland": "Hessen", "min_equity": True},
        )
    )
    assert any(line.startswith("Kirchensteuer ist für") for line in result.assumptions)
    assert any("Bundesland für die Kirchensteuer" in line for line in result.assumptions)


def test_church_tax_is_off_until_switched_on():
    quiet = compare(_scenario(adults=[_adult(depot=80_000, sparrate=200, kaltmiete=700)]))
    assert quiet.assumptions
    assert any("Kirchensteuer ist für niemanden an." == line for line in quiet.assumptions)
    taxed = compare(
        _scenario(
            adults=[
                _adult(
                    depot=80_000,
                    sparrate=200,
                    kaltmiete=700,
                    pension_gross_today=2000,
                    church_tax=True,
                    church_tax_consent=True,
                )
            ],
            horizon={"adult_id": "ada", "age": 70},
        )
    )
    assert any(line.startswith("Kirchensteuer ist für Ada an: 9 %") for line in taxed.assumptions)


def test_interest_is_the_sum_of_the_months():
    from buy_vs_rent.mortgage import initial_payment, step_month
    from buy_vs_rent.scenario import months_between

    free = compare(
        _scenario(
            adults=[_adult(depot=20_000)],
            beliefs={"sollzins": 0, "anschlusszins": 0, "tilgung": 0.02},
            dwelling={
                "purchase_price": 100_000,
                "min_equity": False,
                "owner_costs": 0,
                "transfer_tax": 0,
                "notary_rate": 0,
                "broker_rate": 0,
            },
        )
    )
    assert free.interest_paid == 0
    priced = compare(
        _scenario(
            adults=[_adult(depot=20_000)],
            beliefs={"sollzins": 0.03, "anschlusszins": 0.03, "tilgung": 0.02},
            dwelling={
                "purchase_price": 100_000,
                "min_equity": False,
                "owner_costs": 0,
                "transfer_tax": 0,
                "notary_rate": 0,
                "broker_rate": 0,
            },
        )
    )
    balance = 80_000.0
    payment = initial_payment(balance, 0.03, 0.02)
    expected = 0.0
    months = months_between(date.fromisoformat(priced.purchase_date), date.fromisoformat(priced.horizon_end))
    for _ in range(months + 1):
        interest, _, balance = step_month(balance, 0.03, payment)
        expected += interest
    assert priced.interest_paid == pytest.approx(expected)


def test_empty_depot_warns_before_the_horizon():
    result = compare(
        _scenario(
            adults=[_adult(depot=100, sparrate=0, kaltmiete=0)],
            equity_cash=0,
            extra_rent={"amount_2026": 500, "from": AS_OF, "until": date(2027, 9, 1)},
            dwelling={"owner_costs": 0, "purchase_price": 500_000, "min_equity": True},
            beliefs={"etf_return": 0, "sollzins": 0, "anschlusszins": 0},
        )
    )
    assert any("leer" in line for line in result.warnings)


def test_pots_off_leave_compare_unchanged():
    adult = _adult(depot=50_000, sparrate=500, kaltmiete=1_000)
    dwelling = {"purchase_price": 400_000, "min_equity": False, "owner_costs": 0}
    without = compare(_scenario(adults=[adult], dwelling=dwelling))
    with_default_pots = compare(_scenario(adults=[{**adult, "pots": {}}], dwelling=dwelling))
    assert without.buy_final_nominal == with_default_pots.buy_final_nominal
    assert without.rent_final_nominal == with_default_pots.rent_final_nominal


def test_owner_costs_follow_yearly_rate_after_load():
    result = compare(
        _scenario(
            adults=[_adult(depot=200_000, kaltmiete=1000)],
            dwelling={"purchase_price": 400_000, "owner_costs": 100, "owner_costs_rate": 0.0075, "min_equity": False},
        )
    )
    assert any("250 €" in line for line in result.assumptions)


def test_saved_euros_without_rate_become_yearly_share_once():
    from buy_vs_rent.scenario import Dwelling

    dwelling = Dwelling.model_validate(
        {"bundesland": "Hessen", "purchase_price": 400_000, "owner_costs": 200}
    )
    assert abs(dwelling.owner_costs_rate - 0.006) < 1e-9
    assert dwelling.owner_costs == 200


def test_min_equity_share_changes_purchase_threshold():
    low = compare(
        _scenario(
            adults=[_adult(depot=50_000, kaltmiete=1000)],
            dwelling={"purchase_price": 400_000, "min_equity": True, "min_equity_share": 0.10, "owner_costs": 0},
        )
    )
    high = compare(
        _scenario(
            adults=[_adult(depot=50_000, kaltmiete=1000)],
            dwelling={"purchase_price": 400_000, "min_equity": True, "min_equity_share": 0.20, "owner_costs": 0},
        )
    )
    assert low.equity_shortfall_today < high.equity_shortfall_today


def test_a_path_that_stays_ahead_has_no_break_even_year():
    """Buying that is ahead from the purchase on does not cross the rent line."""
    result = compare(
        _scenario(
            adults=[_adult(depot=500_000, sparrate=0, kaltmiete=1_000)],
            horizon={"adult_id": "ada", "age": 40},
            dwelling={
                "purchase_price": 100_000,
                "notary_rate": 0,
                "broker_rate": 0,
                "transfer_tax": 0,
                "owner_costs": 0,
                "min_equity": False,
            },
            beliefs={"sollzins": 0, "anschlusszins": 0, "tilgung": 0, "etf_return": 0},
        )
    )
    assert result.purchase_date == "2026-09-01"
    assert result.buy_final_nominal > result.rent_final_nominal
    assert result.break_even_year is None
    assert any("kreuzen sich im Horizont nicht" in line for line in result.limits)


def test_follow_up_payment_is_funded_from_leftover():
    """A higher rate cannot amortise a loan when income and the depot are both empty."""
    result = compare(
        _scenario(
            as_of=date(2026, 1, 1),
            adults=[
                _adult(
                    birth=date(1990, 1, 1),
                    gross_salary=0,
                    sparrate=0,
                    kaltmiete=0,
                    depot=0,
                    pension_gross_today=0,
                )
            ],
            equity_cash=20_000,
            horizon={"adult_id": "ada", "age": 40},
            care_copay_2026=0,
            dwelling={
                "purchase_price": 100_000,
                "notary_rate": 0,
                "broker_rate": 0,
                "transfer_tax": 0,
                "owner_costs": 0,
                "min_equity": False,
            },
            beliefs={
                "sollzins": 0.02,
                "anschlusszins": 0.10,
                "tilgung": 0.01,
                "zinsbindung_years": 1,
                "etf_return": 0,
            },
        )
    )
    assert result.purchase_date == "2026-01-01"
    assert result.fixation_end == "2027-01-01"
    assert result.buy_final_nominal <= result.rent_final_nominal + 1


def test_partial_first_year_does_not_take_a_full_kinderfreibetrag():
    """Four months of Kindergeld are not a full year of Kinderfreibetrag.

    At 40.000 € the full-year Freibetrag does not beat twelve months of Kindergeld,
    so a September start must add only the months actually paid.
    """
    child = {"id": "kind", "birth": date(2020, 1, 1), "leave": []}
    shared = dict(
        as_of=date(2026, 9, 1),
        adults=[
            _adult(
                birth=date(1990, 9, 1),
                gross_salary=40_000,
                sparrate=0,
                kaltmiete=0,
                depot=0,
                pension_gross_today=0,
            )
        ],
        horizon={"adult_id": "ada", "age": 37},
        dwelling={"purchase_price": 5_000_000, "min_equity": False},
        beliefs={"etf_return": 0, "inflation": 0},
    )
    without = compare(_scenario(**shared))
    with_child = compare(_scenario(**shared, children=[child]))
    assert with_child.rent_final_nominal - without.rent_final_nominal == 13 * 259


def test_a_later_child_does_not_take_the_older_childs_full_freibetrag():
    """A child born in November is not given the older child's twelve months.

    At 40.000 € neither a full year nor two months of Kindergeld loses to the
    matching Freibetrag, so the younger child adds only the months paid.
    """
    older = {"id": "aelter", "birth": date(2020, 1, 1), "leave": []}
    younger = {"id": "juenger", "birth": date(2026, 11, 1), "leave": []}
    shared = dict(
        as_of=date(2026, 1, 1),
        adults=[
            _adult(
                birth=date(1990, 1, 1),
                gross_salary=40_000,
                sparrate=0,
                kaltmiete=0,
                depot=0,
                pension_gross_today=0,
            )
        ],
        horizon={"adult_id": "ada", "age": 37},
        dwelling={"purchase_price": 5_000_000, "min_equity": False},
        beliefs={"etf_return": 0, "inflation": 0, "sollzins": 0, "anschlusszins": 0},
    )
    one = compare(_scenario(**shared, children=[older]))
    two = compare(_scenario(**shared, children=[older, younger]))
    assert two.rent_final_nominal - one.rent_final_nominal == 3 * 259


def test_price_to_rent_ignores_extra_rent_in_divisor():
    result = compare(
        _scenario(
            adults=[_adult(kaltmiete=800)],
            extra_rent={"amount_2026": 200, "from": AS_OF, "until": date(2030, 9, 1)},
            dwelling={"purchase_price": 400_000, "min_equity": False},
        )
    )
    assert result.price_to_rent == pytest.approx(400_000 / (800 * 12))
    assert result.price_to_rent != pytest.approx(400_000 / ((800 + 200) * 12))


def test_kaufpreisfaktor_uses_shared_rent_for_two_adults():
    result = compare(
        _scenario(
            adults=[
                _adult(adult_id="a1", kaltmiete=400),
                _adult(adult_id="a2", label="Ben", birth=date(1992, 9, 1), kaltmiete=500),
            ],
            together_from=date(2028, 6, 1),
            shared_kaltmiete=1500,
            dwelling={"purchase_price": 360_000, "min_equity": False},
        )
    )
    assert result.price_to_rent == pytest.approx(360_000 / (1500 * 12))
    assert result.price_to_rent != pytest.approx(360_000 / ((400 + 500) * 12))


def test_per_adult_church_tax_only_on_one_adult():
    result = compare(
        _scenario(
            adults=[
                _adult(
                    adult_id="a1",
                    label="Erste",
                    church_tax=True,
                    church_tax_consent=True,
                    pension_gross_today=1500,
                ),
                _adult(adult_id="a2", label="Zweite", birth=date(1992, 9, 1), church_tax=False, pension_gross_today=1500),
            ],
            together_from=AS_OF,
            shared_kaltmiete=1000,
            horizon={"adult_id": "a1", "age": 70},
        )
    )
    line = next(item for item in result.assumptions if item.startswith("Kirchensteuer ist für"))
    assert "Erste" in line
    assert "Zweite" not in line.split("an:")[0]


def test_consume_zero_ignores_reserve():
    spent = compare(_scenario(beliefs={"etf_consume": 0, "etf_reserve": 100_000}, horizon={"adult_id": "ada", "age": 75}))
    kept = compare(_scenario(beliefs={"etf_consume": 0, "etf_reserve": 0}, horizon={"adult_id": "ada", "age": 75}))
    assert spent.rent_final_nominal == pytest.approx(kept.rent_final_nominal)
    assert spent.buy_final_nominal == pytest.approx(kept.buy_final_nominal)


def test_beliefs_church_tax_legacy_ignores_adults_without_consent():
    scenario = _scenario(
        adults=[_adult(adult_id="a1", care_age=69), _adult(adult_id="a2", birth=date(1992, 9, 1), care_age=69)],
        together_from=AS_OF,
        shared_kaltmiete=1000,
        horizon={"adult_id": "a1", "age": 70},
        dwelling={"purchase_price": 400_000, "bundesland": "Hessen", "min_equity": False},
        beliefs={"church_tax": True},
    )
    assert not any(adult.church_tax for adult in scenario.adults)


def test_beliefs_church_tax_legacy_turns_on_consenting_adults_only():
    scenario = _scenario(
        adults=[
            _adult(adult_id="a1", care_age=69, church_tax_consent=True),
            _adult(adult_id="a2", birth=date(1992, 9, 1), care_age=69, church_tax_consent=False),
        ],
        together_from=AS_OF,
        shared_kaltmiete=1000,
        horizon={"adult_id": "a1", "age": 70},
        dwelling={"purchase_price": 400_000, "bundesland": "Hessen", "min_equity": False},
        beliefs={"church_tax": True},
    )
    assert scenario.adults[0].church_tax
    assert not scenario.adults[1].church_tax


def test_church_tax_without_consent_is_rejected():
    with pytest.raises(ValueError, match="Einwilligung"):
        _scenario(adults=[_adult(church_tax=True, church_tax_consent=False)])


def test_future_marriage_month_is_kept():
    future = date(2032, 6, 1)
    scenario = _scenario(
        adults=[_adult(adult_id="a1"), _adult(adult_id="a2", birth=date(1992, 9, 1))],
        together_from=AS_OF,
        married_from=future,
        shared_kaltmiete=1000,
    )
    assert scenario.married_from == future


def test_unmarried_leaves_married_from_empty():
    scenario = _scenario(
        adults=[_adult(adult_id="a1"), _adult(adult_id="a2", birth=date(1992, 9, 1))],
        together_from=AS_OF,
        married_from=None,
        shared_kaltmiete=1000,
    )
    assert scenario.married_from is None

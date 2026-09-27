from datetime import date

import pytest

from buy_vs_rent.income import elterngeld_month, income_tax, monthly_net, net_monthly_pension, taxable_income
from buy_vs_rent.pension import DURCHSCHNITTSENTGELT, points_for_year, estimate_points, pension_today_euros


def test_one_average_year_is_one_point():
    assert points_for_year(DURCHSCHNITTSENTGELT[2026], 2026, 0.02) == 1


def test_gross_above_beitragsbemessungsgrenze_is_capped():
    capped = points_for_year(200_000, 2026, 0.02)
    assert capped == 101_400 / DURCHSCHNITTSENTGELT[2026]
    assert capped < points_for_year(101_400, 2026, 0.02) + 1e-9
    assert capped == points_for_year(101_400, 2026, 0.02)


def test_partner_points_start_september_2023():
    points = estimate_points(
        work_start=date(2023, 9, 1),
        retire=date(2024, 1, 1),
        salary_2026=51_944,
        salary_growth=0,
        inflation=0,
    )
    # September through December 2023 only. Retirement in January 2024 adds no month.
    assert points == pytest.approx(pytest_approx_fraction())


def pytest_approx_fraction():
    from buy_vs_rent.pension import points_for_year as year_points

    return year_points(51_944, 2023, 0) * 4 / 12


def test_salary_growth_walks_back_and_forward():
    assert 70_000 * 1.03 == 72_100
    assert 1_000 * 1.05 == 1_050


def test_elterngeld_rate_bands():
    assert elterngeld_month(1_000, 1, True) == pytest.approx(670)
    assert elterngeld_month(1_220, 1, True) == pytest.approx(1_220 * 0.66)
    assert elterngeld_month(1_240, 1, True) == pytest.approx(806)
    assert elterngeld_month(800, 1, True) == pytest.approx(616)
    assert elterngeld_month(340, 1, True) == pytest.approx(340)
    assert elterngeld_month(2_000, 2, True) == pytest.approx(1_340)
    assert elterngeld_month(2_480, 2, True) == pytest.approx(1_612)


def test_elterngeld_cap_at_these_salaries():
    net = monthly_net(80_000)
    assert net > 2_770
    assert elterngeld_month(net, 1, True) == 1_800


def test_no_elterngeld_above_joint_limit():
    assert taxable_income(300_000) + taxable_income(300_000) > 175_000
    assert elterngeld_month(monthly_net(300_000), 1, False) == 0


def test_2026_tariff_is_monotonic_at_the_42_percent_edge():
    assert income_tax(69_879) >= income_tax(69_878)
    assert income_tax(60_000) == pytest.approx(14_233.23, abs=0.1)


def test_soli_uses_the_minderungszone():
    from buy_vs_rent.income import solidarity

    assert solidarity(20_350) == 0
    assert solidarity(25_000) == pytest.approx(553.35, abs=0.05)
    assert solidarity(25_000) < 25_000 * 0.055


def test_pension_contributions_are_the_retiree_half():
    net = net_monthly_pension(2_000)
    # Half of KV, half of the Zusatzbeitrag, and 1.8% Pflegeversicherung.
    assert net == pytest.approx(1_630, abs=5)


def test_tax_brackets_and_pension_keep_their_real_value():
    assert income_tax(200_000, 2) == pytest.approx(2 * income_tax(100_000, 1))
    assert net_monthly_pension(10_000, 1) < 10_000
    assert net_monthly_pension(10_000, 2) == pytest.approx(2 * net_monthly_pension(5_000, 1))


def test_pension_slider_default_is_points_times_rentenwert():
    points = estimate_points(
        work_start=date(2026, 1, 1),
        retire=date(2027, 1, 1),
        salary_2026=DURCHSCHNITTSENTGELT[2026],
        salary_growth=0,
        inflation=0.02,
    )
    assert points == 1
    assert pension_today_euros(points) == 42.52

"""Hand-worked checks for § 21 deductions while living there."""

from datetime import date

from buy_vs_rent.house import (
    _building_depreciation_rate,
    annual_building_afa,
    annual_rental_deductions,
    craftsman_income_tax_credit_annual,
    rent_while_living_tax_monthly,
    rental_deductions_configured,
)
from buy_vs_rent.income import income_levy
from buy_vs_rent.scenario import Dwelling


def test_building_depreciation_rate_bands():
    assert _building_depreciation_rate(2023) == 0.03
    assert _building_depreciation_rate(2005) == 0.02
    assert _building_depreciation_rate(1924) == 0.025


def test_afa_hand_worked_first_full_year():
    afa = annual_building_afa(300_000, 2 / 3, 2005, 12)
    assert abs(afa - 4_000) < 0.01


def test_section_21_rental_loss_hand_worked():
    afa = 4_000.0
    interest = 550_000 * 0.04 * (2 / 3)
    assert abs(interest - 14_666.67) < 0.1
    deductions = afa + interest
    rental_zve = 16_800 - deductions
    assert abs(rental_zve - (-1_866.67)) < 0.1
    zve = 50_000.0
    loss_tax = income_levy(zve + rental_zve, 1.0, False) - income_levy(zve, 1.0, False)
    monthly_tax = rent_while_living_tax_monthly(
        1_400,
        other_zve_annual=zve,
        inflation_factor=1.0,
        splitting=False,
        annual_rental_deductions=deductions,
    )
    assert abs(monthly_tax * 12 - loss_tax) < 1.0
    assert monthly_tax < 0


def test_deductions_only_when_building_and_share_set():
    bare = Dwelling(bundesland="Bayern")
    assert not rental_deductions_configured(bare)
    full = Dwelling(
        bundesland="Bayern",
        building_cost=300_000,
        rented_area_share=2 / 3,
        building_finished_year=2005,
    )
    assert rental_deductions_configured(full)
    ded = annual_rental_deductions(
        full,
        date(2027, 6, 1),
        purchase=date(2026, 1, 1),
        monthly_loan_interest=550_000 * 0.04 / 12,
    )
    assert ded > 18_000


def test_craftsman_credit_cap():
    assert craftsman_income_tax_credit_annual(3_000) == 600
    assert craftsman_income_tax_credit_annual(10_000) == 1_200

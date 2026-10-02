"""Hand-worked checks for retirement pot formulas."""

from datetime import date

from buy_vs_rent.pot_ledger import january_contributions, ledger_from_adult
from buy_vs_rent.pots import (
    avd_excess_contribution_tax,
    avd_grundzulage_and_refund,
    avd_monthly_growth_factor,
    avd_sonderausgaben_tax_benefit,
    grundzulage_altersvorsorgedepot,
    pot_surplus_after_shortfall,
    kinderzulage_altersvorsorgedepot,
    lump_insurance_gain,
    lump_insurance_tax,
    private_annuity_taxable_annual,
    promoted_payout_tax,
)


def test_avd_monthly_growth_uses_etf_return_without_ter():
    assert avd_monthly_growth_factor(0.087) > 1.0
    assert avd_monthly_growth_factor(0.0) == 1.0


def test_grundzulage_at_1200_own_contribution():
    assert grundzulage_altersvorsorgedepot(1_200) == 390


def test_avd_1200_own_has_no_sonderausgaben_beyond_zulage():
    zulage = grundzulage_altersvorsorgedepot(1_200)
    to_pot, refund = avd_grundzulage_and_refund(1_200, other_zve=40_000)
    assert to_pot == zulage
    assert refund == 0
    assert avd_sonderausgaben_tax_benefit(1_200, other_zve=40_000) == 0
    assert avd_excess_contribution_tax(1_200, other_zve=60_000) == 0


def test_avd_january_1200_adds_1590_to_pot_without_tax_cash():
    from buy_vs_rent.scenario import Adult, Scenario

    adult = Adult.model_validate(
        {
            "id": "ada",
            "label": "Ada",
            "birth": "1990-09-01",
            "gross_salary": 60_000,
            "depot": 0,
            "sparrate": 0,
            "kaltmiete": 0,
            "pots": {
                "altersvorsorgedepot": True,
                "altersvorsorgedepot_balance": 0,
                "altersvorsorgedepot_contribution_yearly": 1_200,
            },
        }
    )
    scenario = Scenario.model_validate(
        {
            "as_of": "2027-01-01",
            "adults": [adult],
            "dwelling": {"purchase_price": 400_000, "bundesland": "Hessen"},
        }
    )
    ledgers = {adult.id: ledger_from_adult(adult, scenario.as_of)}
    deduct, tax_cash = january_contributions(
        scenario,
        ledgers,
        date(2027, 1, 1),
        1.0,
        0,
        household_zve=40_000,
        splitting=False,
    )
    assert deduct == 1_200
    assert tax_cash == 0
    assert ledgers[adult.id].avd_balance == 1_590


def test_avd_excess_above_1800_is_taxed_in_contribution_year():
    assert (
        avd_excess_contribution_tax(
            1_800,
            other_zve=30_000,
            inflation_factor=1.0,
            splitting=False,
        )
        == 0
    )
    tax = avd_excess_contribution_tax(
        2_000,
        other_zve=30_000,
        inflation_factor=1.0,
        splitting=False,
    )
    assert tax > 0


def test_pot_surplus_after_shortfall_hand_worked():
    assert pot_surplus_after_shortfall(10_000, 3_000) == 7_000
    assert pot_surplus_after_shortfall(10_000, -100) == 10_000


def test_grundzulage_caps_at_540():
    assert grundzulage_altersvorsorgedepot(1_800) == 540


def test_kinderzulage_caps_at_300_per_child():
    assert kinderzulage_altersvorsorgedepot(500) == 300


def test_lump_gain_is_payout_minus_premiums():
    assert lump_insurance_gain(60_000, 40_000) == 20_000


def test_lump_half_gain_at_personal_rate_after_twelve_years_and_age_62():
    tax = lump_insurance_tax(
        20_000,
        years_held=12,
        payout_age=67,
        other_zve=50_000,
        inflation_factor=1.0,
        splitting=False,
    )
    assert tax > 0
    assert tax < 20_000 * 0.25


def test_lump_flat_rate_below_twelve_years():
    tax = lump_insurance_tax(
        20_000,
        years_held=5,
        payout_age=67,
        other_zve=0,
        inflation_factor=1.0,
        splitting=False,
    )
    assert tax == 5_000


def test_private_annuity_ertragsanteil_at_67():
    assert round(private_annuity_taxable_annual(12_000, 67)) == 2_040


def test_promoted_payout_is_fully_taxable():
    tax = promoted_payout_tax(20_000, other_zve=30_000, inflation_factor=1.0, splitting=False)
    assert tax > 0

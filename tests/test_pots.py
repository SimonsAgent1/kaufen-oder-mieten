"""Hand-worked checks for retirement pot formulas."""

from buy_vs_rent.pots import (
    grundzulage_altersvorsorgedepot,
    kinderzulage_altersvorsorgedepot,
    lump_insurance_gain,
    lump_insurance_tax,
    private_annuity_taxable_annual,
    promoted_payout_tax,
)


def test_grundzulage_at_1200_own_contribution():
    assert grundzulage_altersvorsorgedepot(1_200) == 390


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

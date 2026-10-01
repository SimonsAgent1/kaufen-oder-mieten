"""Retirement pots besides the ETF depot: balances, grants, and payout tax."""

from __future__ import annotations

from datetime import date

from buy_vs_rent.law.de_2026 import income_levy, solidarity

RIESTER_GRUNDZULAGE_2026 = 175.0
ALTERSVORSORGEDEPOT_START = date(2027, 1, 1)
PRIVATE_ANNUITY_TAXABLE_SHARE_FROM_67 = 0.17
CAPITAL_GAINS_FLAT = 0.25


def grundzulage_altersvorsorgedepot(own_contribution_yearly: float) -> float:
    """Grundzulage: 50 % up to 360 €, then 25 % up to 1.800 € own contributions, max 540 €."""
    own = max(0.0, own_contribution_yearly)
    first = min(own, 360.0) * 0.5
    rest = max(0.0, min(own, 1_800.0) - 360.0) * 0.25
    return min(540.0, first + rest)


def kinderzulage_altersvorsorgedepot(own_contribution_yearly: float) -> float:
    """Per child: 100 % of own contributions, capped at 300 € each (model: one child gets min(own, 300))."""
    return min(max(0.0, own_contribution_yearly), 300.0)


def kinderzulage_total(own_contribution_yearly: float, children: int) -> float:
    if children <= 0:
        return 0.0
    per = kinderzulage_altersvorsorgedepot(own_contribution_yearly)
    return per * children


def lump_insurance_gain(payout: float, premiums_paid: float) -> float:
    return max(0.0, payout - premiums_paid)


def lump_insurance_tax(
    gain: float,
    *,
    years_held: float,
    payout_age: int,
    other_zve: float,
    inflation_factor: float = 1.0,
    splitting: bool = False,
) -> float:
    """§ 20 Abs. 1 Nr. 6 EStG: half the gain at personal rate after 12 years and age 62+, else 25 % + Soli on full gain."""
    if gain <= 0:
        return 0.0
    if years_held >= 12 and payout_age >= 62:
        taxable = gain / 2
        with_gain = income_levy(other_zve + taxable, inflation_factor, splitting)
        without = income_levy(other_zve, inflation_factor, splitting)
        return max(0.0, with_gain - without)
    base_tax = gain * CAPITAL_GAINS_FLAT
    return base_tax + solidarity(base_tax, inflation_factor, splitting)


def private_annuity_taxable_annual(annual_payment: float, payout_age: int) -> float:
    """§ 22 Nr. 1 EStG Ertragsanteil; from age 67 the share is 17 %."""
    if annual_payment <= 0:
        return 0.0
    share = PRIVATE_ANNUITY_TAXABLE_SHARE_FROM_67 if payout_age >= 67 else 0.0
    return annual_payment * share


def private_annuity_income_tax(
    annual_payment: float,
    *,
    payout_age: int,
    other_zve: float,
    inflation_factor: float = 1.0,
    splitting: bool = False,
) -> float:
    taxable = private_annuity_taxable_annual(annual_payment, payout_age)
    if taxable <= 0:
        return 0.0
    with_pay = income_levy(other_zve + taxable, inflation_factor, splitting)
    without = income_levy(other_zve, inflation_factor, splitting)
    return max(0.0, with_pay - without)


def promoted_payout_tax(
    payout: float,
    *,
    other_zve: float,
    inflation_factor: float = 1.0,
    splitting: bool = False,
) -> float:
    """Fully taxable payout (Riester, Altersvorsorgedepot) under § 22 Nr. 5 EStG."""
    if payout <= 0:
        return 0.0
    with_pay = income_levy(other_zve + payout, inflation_factor, splitting)
    without = income_levy(other_zve, inflation_factor, splitting)
    return max(0.0, with_pay - without)


def pot_surrender_total(
    *,
    capital_life: bool,
    capital_life_balance: float,
    private_lump: bool,
    private_lump_balance: float,
    private_annuity: bool,
    private_annuity_balance: float,
    riester: bool,
    riester_balance: float,
    altersvorsorgedepot: bool,
    altersvorsorgedepot_balance: float,
    annuity_paying: bool,
) -> float:
    total = 0.0
    if capital_life:
        total += capital_life_balance
    if private_lump:
        total += private_lump_balance
    if private_annuity and not annuity_paying:
        total += private_annuity_balance
    if riester:
        total += riester_balance
    if altersvorsorgedepot:
        total += altersvorsorgedepot_balance
    return total

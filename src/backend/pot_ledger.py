"""Month updates for retirement pots shared by both paths."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from buy_vs_rent.pots import (
    ALTERSVORSORGEDEPOT_START,
    RIESTER_GRUNDZULAGE_2026,
    grundzulage_altersvorsorgedepot,
    kinderzulage_total,
    lump_insurance_gain,
    lump_insurance_tax,
    pot_surrender_total,
    private_annuity_income_tax,
    promoted_payout_tax,
)
from buy_vs_rent.scenario import Adult, Scenario, age_years, months_between, retire_month


@dataclass
class AdultPotLedger:
    capital_life_balance: float
    capital_life_premiums: float
    capital_life_start: date
    capital_life_paid: bool

    private_lump_balance: float
    private_lump_premiums: float
    private_lump_start: date
    private_lump_paid: bool

    private_annuity_balance: float
    private_annuity_yearly: float
    private_annuity_paying: bool

    riester_balance: float
    riester_paid: bool

    avd_balance: float
    avd_paid: bool


def ledger_from_adult(adult: Adult, as_of: date) -> AdultPotLedger:
    pots = adult.pots
    cap_start = pots.capital_life_start or adult.work_start or as_of
    lump_start = pots.private_lump_start or adult.work_start or as_of
    return AdultPotLedger(
        capital_life_balance=pots.capital_life_balance if pots.capital_life else 0.0,
        capital_life_premiums=pots.capital_life_premiums if pots.capital_life else 0.0,
        capital_life_start=cap_start,
        capital_life_paid=not pots.capital_life,
        private_lump_balance=pots.private_lump_balance if pots.private_lump else 0.0,
        private_lump_premiums=pots.private_lump_premiums if pots.private_lump else 0.0,
        private_lump_start=lump_start,
        private_lump_paid=not pots.private_lump,
        private_annuity_balance=pots.private_annuity_balance if pots.private_annuity else 0.0,
        private_annuity_yearly=pots.private_annuity_yearly if pots.private_annuity else 0.0,
        private_annuity_paying=False,
        riester_balance=pots.riester_balance if pots.riester else 0.0,
        riester_paid=not pots.riester,
        avd_balance=pots.altersvorsorgedepot_balance if pots.altersvorsorgedepot else 0.0,
        avd_paid=not pots.altersvorsorgedepot,
    )


def surrender_value(adult: Adult, ledger: AdultPotLedger) -> float:
    pots = adult.pots
    return pot_surrender_total(
        capital_life=pots.capital_life and not ledger.capital_life_paid,
        capital_life_balance=ledger.capital_life_balance,
        private_lump=pots.private_lump and not ledger.private_lump_paid,
        private_lump_balance=ledger.private_lump_balance,
        private_annuity=pots.private_annuity,
        private_annuity_balance=ledger.private_annuity_balance,
        riester=pots.riester and not ledger.riester_paid,
        riester_balance=ledger.riester_balance,
        altersvorsorgedepot=pots.altersvorsorgedepot and not ledger.avd_paid,
        altersvorsorgedepot_balance=ledger.avd_balance,
        annuity_paying=ledger.private_annuity_paying,
    )


def january_contributions(
    scenario: Scenario,
    ledgers: dict[str, AdultPotLedger],
    month: date,
    inflation_factor: float,
    child_count: int,
) -> float:
    """Own AVD contributions to deduct from ETF savings (both paths)."""
    if month.month != 1:
        return 0.0
    deduct = 0.0
    for adult in scenario.adults:
        pots = adult.pots
        ledger = ledgers[adult.id]
        if pots.riester and not ledger.riester_paid:
            ledger.riester_balance += RIESTER_GRUNDZULAGE_2026 * inflation_factor
        if pots.altersvorsorgedepot and not ledger.avd_paid and month >= ALTERSVORSORGEDEPOT_START:
            own_nominal = pots.altersvorsorgedepot_contribution_yearly
            own = own_nominal * inflation_factor
            zulage = grundzulage_altersvorsorgedepot(own_nominal) * inflation_factor
            kinder = kinderzulage_total(own_nominal, child_count) * inflation_factor
            ledger.avd_balance += own + zulage + kinder
            deduct += own
    return deduct


def retire_payouts(
    adult: Adult,
    ledger: AdultPotLedger,
    month: date,
    *,
    other_zve: float,
    inflation_factor: float,
    splitting: bool,
) -> float:
    """Net cash from pots paid at retirement month. Mutates ledger."""
    if month != retire_month(adult):
        return 0.0
    payout_age = age_years(adult.birth, month)
    net_total = 0.0
    pots = adult.pots

    def lump_net(balance: float, premiums: float, start: date) -> float:
        gain = lump_insurance_gain(balance, premiums)
        years = months_between(start, month) / 12
        tax = lump_insurance_tax(
            gain,
            years_held=years,
            payout_age=payout_age,
            other_zve=other_zve,
            inflation_factor=inflation_factor,
            splitting=splitting,
        )
        return max(0.0, balance - tax)

    if pots.capital_life and not ledger.capital_life_paid:
        net_total += lump_net(ledger.capital_life_balance, ledger.capital_life_premiums, ledger.capital_life_start)
        ledger.capital_life_balance = 0.0
        ledger.capital_life_paid = True
    if pots.private_lump and not ledger.private_lump_paid:
        net_total += lump_net(ledger.private_lump_balance, ledger.private_lump_premiums, ledger.private_lump_start)
        ledger.private_lump_balance = 0.0
        ledger.private_lump_paid = True
    if pots.private_annuity and not ledger.private_annuity_paying:
        ledger.private_annuity_balance = 0.0
        ledger.private_annuity_paying = True
    if pots.riester and not ledger.riester_paid:
        tax = promoted_payout_tax(
            ledger.riester_balance,
            other_zve=other_zve,
            inflation_factor=inflation_factor,
            splitting=splitting,
        )
        net_total += max(0.0, ledger.riester_balance - tax)
        ledger.riester_balance = 0.0
        ledger.riester_paid = True
    if pots.altersvorsorgedepot and not ledger.avd_paid:
        tax = promoted_payout_tax(
            ledger.avd_balance,
            other_zve=other_zve,
            inflation_factor=inflation_factor,
            splitting=splitting,
        )
        net_total += max(0.0, ledger.avd_balance - tax)
        ledger.avd_balance = 0.0
        ledger.avd_paid = True
    return net_total


def annuity_january_net(
    adult: Adult,
    ledger: AdultPotLedger,
    month: date,
    *,
    other_zve: float,
    inflation_factor: float,
    splitting: bool,
) -> float:
    if month.month != 1 or not ledger.private_annuity_paying:
        return 0.0
    payout_age = age_years(adult.birth, month)
    annual = ledger.private_annuity_yearly * inflation_factor
    tax = private_annuity_income_tax(
        annual,
        payout_age=payout_age,
        other_zve=other_zve,
        inflation_factor=inflation_factor,
        splitting=splitting,
    )
    return max(0.0, annual - tax)

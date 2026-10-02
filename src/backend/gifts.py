"""Gifts and loans from parents (not the bank mortgage)."""

from __future__ import annotations

from buy_vs_rent.scenario import Scenario

PARENT_GIFT_ALLOWANCE_EACH = 400_000.0


def inheritance_tax_class_i(taxable: float) -> float:
    """§ 19 ErbStG Steuerklasse I on the taxable share above the Freibetrag."""
    if taxable <= 0:
        return 0.0
    bands = (
        (75_000, 0.07),
        (225_000, 0.11),
        (300_000, 0.15),
        (5_400_000, 0.19),
        (7_000_000, 0.23),
        (13_000_000, 0.27),
    )
    tax = 0.0
    remaining = taxable
    for width, rate in bands:
        if remaining <= 0:
            break
        chunk = min(remaining, width)
        tax += chunk * rate
        remaining -= chunk
    if remaining > 0:
        tax += remaining * 0.30
    return tax


def gift_tax_one_parent(gift_from_parent: float) -> float:
    """Erwerbsteuer on one parent's half after the 400.000 € Freibetrag, § 16 Abs. 1 Nr. 2 ErbStG."""
    taxable = max(0.0, gift_from_parent - PARENT_GIFT_ALLOWANCE_EACH)
    return inheritance_tax_class_i(taxable)


def gift_tax_parents(total_gift: float) -> float:
    """One gift sum split equally between two parents; each has a separate Freibetrag."""
    if total_gift <= 0:
        return 0.0
    half = total_gift / 2
    return round(gift_tax_one_parent(half) + gift_tax_one_parent(half), 2)


def parent_support_cash(scenario: Scenario) -> tuple[float, float, float]:
    """Spendable cash at start, gift tax paid once, and outstanding parent loan principal."""
    cash = scenario.equity_cash
    gift_tax = 0.0
    loan = 0.0
    if scenario.parent_gift:
        gift_tax = gift_tax_parents(scenario.parent_gift_amount)
        cash += scenario.parent_gift_amount - gift_tax
    if scenario.parent_loan:
        loan = scenario.parent_loan_amount
        cash += loan
    return cash, gift_tax, loan

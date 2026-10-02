"""German annuity: Sollzins plus anfängliche Tilgung."""

from __future__ import annotations

from dataclasses import dataclass


def initial_payment(balance: float, annual_rate: float, tilgung: float) -> float:
    if balance <= 0:
        return 0.0
    return balance * (annual_rate + tilgung) / 12


def step_month(balance: float, annual_rate: float, payment: float) -> tuple[float, float, float]:
    """Return interest, principal, and the new balance."""
    if balance <= 1e-8:
        return 0.0, 0.0, 0.0
    interest = balance * annual_rate / 12
    if payment >= balance + interest:
        return interest, balance, 0.0
    principal = payment - interest
    return interest, principal, balance - principal


def balance_after(balance: float, annual_rate: float, payment: float, months: int) -> float:
    """Closed form for a fixed payment. Matches step_month while the balance stays positive."""
    remaining = balance
    for _ in range(months):
        _, _, remaining = step_month(remaining, annual_rate, payment)
        if remaining <= 1e-8:
            return 0.0
    return remaining


def payment_to_clear(balance: float, annual_rate: float, months: int) -> float:
    """Monthly payment that brings the balance to zero in `months`."""
    if balance <= 0 or months <= 0:
        return 0.0
    monthly = annual_rate / 12
    if monthly == 0:
        return balance / months
    grown = (1 + monthly) ** months
    return balance * monthly * grown / (grown - 1)


@dataclass(frozen=True)
class MortgageSnapshot:
    balance: float
    rate: float
    payment: float
    months_left_in_fixation: int
    switched: bool


def bank_loan_obligation_chart_value(
    snap: MortgageSnapshot | None,
    *,
    months_until_sale: int,
    anschluss_rate: float,
    payment_at_purchase: float,
) -> float:
    """Principal still owed plus interest still due until payoff or home sale. Not wealth."""
    if snap is None or snap.balance <= 0 or months_until_sale <= 0:
        return 0.0
    balance = snap.balance
    rate = snap.rate
    payment = snap.payment
    fix_left = snap.months_left_in_fixation
    switched = snap.switched
    principal = snap.balance
    interest_sum = 0.0
    for step in range(months_until_sale):
        if balance <= 1e-8:
            break
        if fix_left == 0 and not switched:
            rate = anschluss_rate
            switched = True
        if switched:
            remaining = months_until_sale - step
            required = payment_to_clear(balance, rate, remaining)
            if required > payment_at_purchase:
                payment = required
        interest, _, balance = step_month(balance, rate, payment)
        interest_sum += interest
        if fix_left > 0:
            fix_left -= 1
    return principal + interest_sum


def closed_form_balance(balance: float, annual_rate: float, payment: float, months: int) -> float:
    monthly = annual_rate / 12
    if months <= 0:
        return balance
    if monthly == 0:
        return max(0.0, balance - payment * months)
    grown = (1 + monthly) ** months
    remaining = balance * grown - payment * (grown - 1) / monthly
    return max(0.0, remaining)

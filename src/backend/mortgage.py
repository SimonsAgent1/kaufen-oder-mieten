"""German annuity: Sollzins plus anfängliche Tilgung."""

from __future__ import annotations


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


def closed_form_balance(balance: float, annual_rate: float, payment: float, months: int) -> float:
    monthly = annual_rate / 12
    if months <= 0:
        return balance
    if monthly == 0:
        return max(0.0, balance - payment * months)
    grown = (1 + monthly) ** months
    remaining = balance * grown - payment * (grown - 1) / monthly
    return max(0.0, remaining)

"""Shim. Transfer-tax figures live in ``buy_vs_rent.law.de_2026``."""

from buy_vs_rent.law.de_2026 import TRANSFER_TAX, purchase_costs, transfer_tax_rate

__all__ = ["TRANSFER_TAX", "purchase_costs", "transfer_tax_rate"]

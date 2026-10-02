"""Sale tax under §23 EStG."""

from __future__ import annotations

from buy_vs_rent.income import income_levy
from buy_vs_rent.scenario import Scenario


def comparison_cold_rent_monthly(scenario: Scenario) -> float:
    """Cold rent for the Kaufpreisfaktor in today's euros."""
    if len(scenario.adults) == 1:
        monthly = scenario.adults[0].kaltmiete
    else:
        monthly = scenario.shared_kaltmiete
    return monthly


def comparison_rent_monthly(scenario: Scenario, rent_growth_factor: float) -> float:
    """Vergleichskaltmiete for the month, with rent growth applied once per year."""
    return comparison_cold_rent_monthly(scenario) * rent_growth_factor


def price_to_rent(purchase_price: float, scenario: Scenario) -> float | None:
    """Purchase price divided by twelve months of comparison cold rent."""
    monthly = comparison_cold_rent_monthly(scenario)
    if monthly <= 0:
        return None
    return purchase_price / (monthly * 12)


def price_to_rent_band(factor: float) -> str:
    if factor < 20:
        return "unter 20"
    if factor <= 25:
        return "20 bis 25"
    return "über 25"


def rent_while_living_tax_monthly(
    monthly_cold_rent: float,
    *,
    other_zve_annual: float,
    inflation_factor: float = 1.0,
    splitting: bool = False,
) -> float:
    """§ 21 EStG cold rent while owner-occupied; taxed at the personal rate, not as capital income."""
    annual = monthly_cold_rent * 12
    if annual <= 0:
        return 0.0
    with_rent = income_levy(other_zve_annual + annual, inflation_factor, splitting)
    without = income_levy(other_zve_annual, inflation_factor, splitting)
    return max(0.0, with_rent - without) / 12


def monthly_owner_costs(price: float, rate: float) -> float:
    """A share of the purchase price per year, as euros per month."""
    return price * rate / 12


def extra_equity_from_price(purchase_price: float, share: float) -> float:
    """Extra equity as a share of the purchase price, not Nebenkosten."""
    return purchase_price * share


def sale_gain(sale_price: float, selling_cost_rate: float, purchase_price: float, nebenkosten: float) -> float:
    return sale_price * (1 - selling_cost_rate) - purchase_price - nebenkosten


def house_sale_tax(
    gain: float,
    *,
    held_years: float,
    owner_occupied_exemption: bool,
    other_income: float,
    inflation_factor: float = 1.0,
    splitting: bool = False,
) -> float:
    """Exempt if §23 owner-occupied rules apply, or if held longer than 10 years."""
    if gain <= 0:
        return 0.0
    if owner_occupied_exemption or held_years > 10:
        return 0.0
    with_gain = income_levy(other_income + gain, inflation_factor, splitting)
    without = income_levy(other_income, inflation_factor, splitting)
    return max(0.0, with_gain - without)


def owner_occupied_exemption(
    purchase: "date",
    sale: "date",
    *,
    exclusive_own_use_until_sale: bool = True,
) -> bool:
    from datetime import date

    if not exclusive_own_use_until_sale:
        return False
    if not isinstance(purchase, date) or not isinstance(sale, date):
        return False
    if sale < purchase:
        return False
    # Buy path: exclusive own use from purchase through sale (§23).
    return True

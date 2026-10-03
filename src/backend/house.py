"""Sale tax under §23 EStG."""

from __future__ import annotations

from datetime import date

from buy_vs_rent.income import income_levy
from buy_vs_rent.scenario import Dwelling, Scenario


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


def _building_depreciation_rate(finished_year: int) -> float:
    """Linear AfA rate on the building share, § 7 Abs. 4 EStG (approximation)."""
    if finished_year >= 2023:
        return 0.03
    if finished_year >= 1925:
        return 0.02
    return 0.025


def rental_deductions_configured(dwelling: Dwelling) -> bool:
    """True when building cost, rented share, and finished year are all set."""
    return (
        dwelling.building_cost is not None
        and dwelling.building_cost > 0
        and dwelling.rented_area_share is not None
        and dwelling.rented_area_share > 0
        and dwelling.building_finished_year is not None
    )


def _modernization_afa_extra_base(building_cost: float, modernization_cost: float) -> float:
    """§ 6 Abs. 1 Nr. 1a EStG: modernization above 15 % of building cost joins the AfA base."""
    if modernization_cost <= 0:
        return 0.0
    if modernization_cost > 0.15 * building_cost:
        return modernization_cost
    return 0.0


def _modernization_immediate_deduction(building_cost: float, modernization_cost: float, share: float) -> float:
    """Erhaltungsaufwand on the rented share when the 15 % cap is not exceeded."""
    if modernization_cost <= 0 or modernization_cost > 0.15 * building_cost:
        return 0.0
    return modernization_cost * share


def annual_building_afa(
    building_cost: float,
    share: float,
    finished_year: int,
    months_in_calendar_year: int,
    *,
    extra_afa_base: float = 0.0,
) -> float:
    """AfA on building cost times rented share, pro-rata when fewer than twelve months apply."""
    if months_in_calendar_year <= 0:
        return 0.0
    base = (building_cost + extra_afa_base) * share
    rate = _building_depreciation_rate(finished_year)
    return base * rate * (months_in_calendar_year / 12)


def _months_owned_in_calendar_year(purchase: date, month: date) -> int:
    if month.year < purchase.year:
        return 0
    if month.year > purchase.year:
        return 12
    return 12 - purchase.month + 1


def annual_rental_deductions(
    dwelling: Dwelling,
    month: date,
    *,
    purchase: date | None,
    monthly_loan_interest: float,
) -> float:
    """AfA, financed interest share, and maintenance on the stranger-rented share (annual euros)."""
    if not rental_deductions_configured(dwelling):
        return 0.0
    building_cost = dwelling.building_cost
    share = dwelling.rented_area_share
    finished = dwelling.building_finished_year
    assert building_cost is not None and share is not None and finished is not None
    months = 12
    if purchase is not None:
        months = _months_owned_in_calendar_year(purchase, month)
    extra_base = 0.0
    immediate_mod = 0.0
    if purchase is not None and month.year == purchase.year:
        extra_base = _modernization_afa_extra_base(building_cost, dwelling.modernization_cost)
        immediate_mod = _modernization_immediate_deduction(building_cost, dwelling.modernization_cost, share)
    afa = annual_building_afa(
        building_cost,
        share,
        finished,
        months,
        extra_afa_base=extra_base,
    )
    interest = monthly_loan_interest * 12 * share
    maintenance = dwelling.rented_maintenance_annual * share + immediate_mod
    return afa + interest + maintenance


def rent_while_living_tax_monthly(
    monthly_cold_rent: float,
    *,
    other_zve_annual: float,
    inflation_factor: float = 1.0,
    splitting: bool = False,
    annual_rental_deductions: float = 0.0,
) -> float:
    """§ 21 EStG cold rent while owner-occupied; taxed at the personal rate, not as capital income."""
    annual = monthly_cold_rent * 12
    if annual <= 0 and annual_rental_deductions <= 0:
        return 0.0
    rental_zve = annual - annual_rental_deductions
    with_rent = income_levy(other_zve_annual + rental_zve, inflation_factor, splitting)
    without = income_levy(other_zve_annual, inflation_factor, splitting)
    return (with_rent - without) / 12


def craftsman_income_tax_credit_annual(labor: float) -> float:
    """§ 35a Abs. 3 EStG: 20 % of craftsman labor on the owner-occupied part, capped at 1.200 €."""
    if labor <= 0:
        return 0.0
    return min(1200.0, 0.20 * labor)


def craftsman_income_tax_credit_monthly(annual_labor: float) -> float:
    return craftsman_income_tax_credit_annual(annual_labor) / 12


def _shared_home_rent_split_monthly(
    dwelling: Dwelling, month: date, inflation_factor: float
) -> tuple[float, float]:
    """Cold rent in the active stretch: (stranger §21 gross, spouse inflow gross)."""
    for period in dwelling.shared_home_rent:
        if period.start <= month <= period.until:
            gross = period.kalt * inflation_factor
            if period.payer == "spouse":
                return 0.0, gross
            return gross, 0.0
    return 0.0, 0.0


def shared_home_living_rent_net(
    dwelling: Dwelling,
    month: date,
    *,
    other_zve_annual: float,
    inflation_factor: float,
    splitting: bool,
    purchase: date | None = None,
    monthly_loan_interest: float = 0.0,
) -> float:
    stranger_gross, spouse_gross = _shared_home_rent_split_monthly(dwelling, month, inflation_factor)
    if stranger_gross <= 0 and spouse_gross <= 0:
        return 0.0
    stranger_net = stranger_gross
    if stranger_gross > 0:
        deductions = 0.0
        if rental_deductions_configured(dwelling):
            deductions = annual_rental_deductions(
                dwelling,
                month,
                purchase=purchase,
                monthly_loan_interest=monthly_loan_interest,
            )
        tax = rent_while_living_tax_monthly(
            stranger_gross,
            other_zve_annual=other_zve_annual,
            inflation_factor=inflation_factor,
            splitting=splitting,
            annual_rental_deductions=deductions,
        )
        stranger_net = stranger_gross - tax
    return stranger_net + spouse_gross


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

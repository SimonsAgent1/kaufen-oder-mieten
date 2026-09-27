"""Germany 2026 approximations: wage tax, Elterngeld, Kindergeld, transfer tax, pension anchors.

A later year is a new module. The month loop reads this pack and does not carry its own tax numbers.
"""

from __future__ import annotations

# 2026 social-security anchors. Employee shares are a simplification:
# Rentenversicherung 9.3%, Arbeitslosenversicherung 1.3%,
# Employee shares, 2026. KV is half of 14.6% plus half of the 2.9% average Zusatzbeitrag.
# PV is 1.8% for a parent. Childless contributors over 23 add 0.6 points.
RV_RATE = 0.093
AV_RATE = 0.013
KV_RATE = 0.0875
PV_RATE = 0.018
PV_CHILDLESS = 0.006
# Euro of 2026. A Hessen nursing-home illustration, not a personal care plan.
# The state average first-year copay was 3,431 € on 1 July 2026 (vdek).
CARE_ALONE_2026 = 3_600.0
CARE_COUPLE_2026 = 5_800.0
# Pensioners pay half of KV, half of the Zusatzbeitrag, and half of Pflegeversicherung.
# With children that Pflege share is 1.8%, not the full 3.6%.
PENSION_HEALTH_RATE = 0.073 + 0.029 / 2 + 0.036 / 2
RV_CEILING_2026 = 101_400.0
KV_CEILING_2026 = 69_750.0
WERBUNGSKOSTEN = 1_230.0
PENSION_WERBUNGSKOSTEN = 102.0
GRUNDFREIBETRAG = 12_348.0
KINDERGELD_2026 = 259.0
# One parent receives Kindererziehungszeiten for all children; three Entgeltpunkte per child (SGB VI simplification).
CHILD_REARING_ENTGELTPUNKTE_PER_CHILD = 3.0


def kindergeld_until_age(accept_until_25: bool) -> int:
    """Kindergeld runs until this birthday age. Nein ends at 18 without training or income tests."""
    return 25 if accept_until_25 else 18


def child_rearing_entgeltpunkte(child_count: int) -> float:
    """Entgeltpunkte from Kindererziehungszeiten credited to one adult for all children."""
    if child_count <= 0:
        return 0.0
    return child_count * CHILD_REARING_ENTGELTPUNKTE_PER_CHILD
# Kinderfreibetrag 6,828 € plus BEA-Freibetrag 2,928 €, both parents together.
KINDERFREIBETRAG_2026 = 9_756.0
SOLI_FREE_2026 = 20_350.0
ELTERNGELD_MIN = 300.0
ELTERNGELD_CAP = 1_800.0
ELTERNGELD_NET_CAP_TRIGGER = 2_770.0
ELTERNGELD_INCOME_LIMIT = 175_000.0


def _factor(inflation_factor: float) -> float:
    return inflation_factor if inflation_factor > 0 else 1.0


def social_contributions(gross: float, inflation_factor: float = 1.0, pv_rate: float = PV_RATE) -> float:
    if gross <= 0:
        return 0.0
    factor = _factor(inflation_factor)
    pension_base = min(gross, RV_CEILING_2026 * factor)
    health_base = min(gross, KV_CEILING_2026 * factor)
    return pension_base * (RV_RATE + AV_RATE) + health_base * (KV_RATE + pv_rate)


def taxable_income(gross: float, inflation_factor: float = 1.0, pv_rate: float = PV_RATE) -> float:
    factor = _factor(inflation_factor)
    return max(0.0, gross - social_contributions(gross, factor, pv_rate) - WERBUNGSKOSTEN * factor)


def _income_tax_2026(zve: float) -> float:
    """Approximate §32a tariff around the 2026 Grundfreibetrag. Monotonic, not a Bescheid."""
    x = max(0.0, zve)
    if x <= GRUNDFREIBETRAG:
        return 0.0
    if x <= 17_799:
        y = (x - GRUNDFREIBETRAG) / 10_000
        return (914.51 * y + 1_400) * y
    if x <= 69_878:
        z = (x - 17_799) / 10_000
        return (173.10 * z + 2_397) * z + 1_034.87
    if x <= 277_825:
        return 0.42 * x - 11_135.63
    return 0.45 * x - 19_470.38


def income_tax(zve: float, inflation_factor: float = 1.0) -> float:
    """2026 tariff, scaled so brackets keep their real value."""
    factor = _factor(inflation_factor)
    return _income_tax_2026(zve / factor) * factor


def solidarity(tax: float, inflation_factor: float = 1.0, splitting: bool = False) -> float:
    """5.5% above the Freigrenze, capped by the 11.9% Milderungszone. Joint returns use twice the limit."""
    if tax <= 0:
        return 0.0
    limit = SOLI_FREE_2026 * _factor(inflation_factor) * (2 if splitting else 1)
    if tax <= limit:
        return 0.0
    return min(tax * 0.055, 0.119 * (tax - limit))


def income_levy(zve: float, inflation_factor: float = 1.0, splitting: bool = False) -> float:
    if splitting:
        tax = 2 * income_tax(max(0.0, zve) / 2, inflation_factor)
    else:
        tax = income_tax(max(0.0, zve), inflation_factor)
    return tax + solidarity(tax, inflation_factor, splitting)


def church_tax_rate(bundesland: str) -> float:
    """Share of the income tax. Bayern and Baden-Württemberg use 8 %, every other state 9 %."""
    if bundesland in {"Bayern", "Baden-Württemberg"}:
        return 0.08
    return 0.09


def annual_net(
    gross: float,
    inflation_factor: float = 1.0,
    pv_rate: float = PV_RATE,
    church_rate: float = 0.0,
) -> float:
    factor = _factor(inflation_factor)
    soc = social_contributions(gross, factor, pv_rate)
    tax = income_tax(taxable_income(gross, factor, pv_rate), factor)
    return gross - soc - tax - solidarity(tax, factor) - tax * church_rate


def monthly_net(
    gross: float,
    inflation_factor: float = 1.0,
    pv_rate: float = PV_RATE,
    church_rate: float = 0.0,
) -> float:
    if gross <= 0:
        return 0.0
    return annual_net(gross, inflation_factor, pv_rate, church_rate) / 12


def pension_deductions(annual_gross: float, inflation_factor: float = 1.0) -> tuple[float, float]:
    """Health and care contributions, then the pension Werbungskostenpauschale, both in euros."""
    factor = _factor(inflation_factor)
    health = min(max(0.0, annual_gross), KV_CEILING_2026 * factor) * PENSION_HEALTH_RATE
    return health, PENSION_WERBUNGSKOSTEN * factor


def net_monthly_pension(
    gross_monthly: float, inflation_factor: float = 1.0, church_rate: float = 0.0
) -> float:
    """Gesetzliche Rente after income tax, Soli, church tax, and retiree health and care contributions."""
    if gross_monthly <= 0:
        return 0.0
    factor = _factor(inflation_factor)
    annual = gross_monthly * 12
    health, costs = pension_deductions(annual, factor)
    zve = max(0.0, annual - health - costs)
    tax = income_tax(zve, factor)
    net = annual - health - tax - solidarity(tax, factor) - tax * church_rate
    return max(0.0, net / 12)


def kinder_freibetrag_refund(
    zve: float,
    child_payments: list[tuple[float, int]],
    inflation_factor: float = 1.0,
    splitting: bool = False,
) -> float:
    """Cash to invest when the Freibetrag beats Kindergeld. Zero when Kindergeld wins.

    Each tuple is one child's Kindergeld paid so far that year and the months it was paid.
    """
    kindergeld_year = sum(paid for paid, _ in child_payments)
    if not child_payments or kindergeld_year <= 0 or zve <= 0:
        return 0.0
    factor = _factor(inflation_factor)
    relief = sum(
        KINDERFREIBETRAG_2026 * factor * min(months, 12) / 12
        for _, months in child_payments
        if months > 0
    )
    if relief <= 0:
        return 0.0
    saved = income_levy(zve, inflation_factor, splitting) - income_levy(zve - relief, inflation_factor, splitting)
    if saved <= kindergeld_year:
        return 0.0
    return saved - kindergeld_year


def elterngeld_month(usual_net: float, inflation: float, eligible: bool, sibling: bool = False) -> float:
    """Basiselterngeld for one month. Cap and floor grow with inflation; the 175k test does not."""
    if not eligible or usual_net <= 0:
        return 0.0
    if usual_net > ELTERNGELD_NET_CAP_TRIGGER * inflation:
        benefit = ELTERNGELD_CAP * inflation
    elif usual_net >= 1_240 * inflation:
        benefit = 0.65 * usual_net
    elif usual_net >= 1_200 * inflation:
        steps = (usual_net - 1_200 * inflation) / (2 * inflation)
        benefit = max(0.65, 0.67 - 0.001 * steps) * usual_net
    elif usual_net >= 1_000 * inflation:
        benefit = 0.67 * usual_net
    else:
        steps = max(0.0, (1_000 * inflation - usual_net) / (2 * inflation))
        benefit = min(1.0, 0.67 + 0.001 * steps) * usual_net
    floor = ELTERNGELD_MIN * inflation
    cap = ELTERNGELD_CAP * inflation
    benefit = min(cap, max(floor, benefit))
    if sibling and benefit > 0:
        benefit += max(75.0 * inflation, 0.10 * benefit)
    return benefit


# Grunderwerbsteuer by Bundesland, January 2026.
TRANSFER_TAX = {
    "Baden-Württemberg": 0.05,
    "Bayern": 0.035,
    "Berlin": 0.06,
    "Brandenburg": 0.065,
    "Bremen": 0.055,
    "Hamburg": 0.055,
    "Hessen": 0.06,
    "Mecklenburg-Vorpommern": 0.06,
    "Niedersachsen": 0.05,
    "Nordrhein-Westfalen": 0.065,
    "Rheinland-Pfalz": 0.05,
    "Saarland": 0.065,
    "Sachsen": 0.055,
    "Sachsen-Anhalt": 0.05,
    "Schleswig-Holstein": 0.065,
    "Thüringen": 0.05,
}

# Published pension averages. 2023 is the West figure from before the single national series.
DURCHSCHNITTSENTGELT = {2023: 44_732.0, 2024: 47_085.0, 2025: 50_493.0, 2026: 51_944.0}
BEITRAGSBEMESSUNGSGRENZE = {2023: 87_600.0, 2024: 90_600.0, 2025: 96_600.0, 2026: 101_400.0}
RENTENWERT_2026 = 42.52


def transfer_tax_rate(bundesland: str) -> float:
    try:
        return TRANSFER_TAX[bundesland]
    except KeyError as exc:
        known = ", ".join(sorted(TRANSFER_TAX))
        raise ValueError(f"Unbekanntes Bundesland: {bundesland}. Bekannt: {known}") from exc


def purchase_costs(price: float, transfer: float, notary: float, broker: float) -> float:
    return price * (transfer + notary + broker)


def employee_pv_rate(child_count: int, age_years: int) -> float:
    """Employee Pflegeversicherung for this month.

    A childless adult who is already 23 pays the extra 0.6 points. From the second
    child under 25 the share falls by 0.25 points per such child, through the fifth.
    """
    if child_count <= 0:
        return PV_RATE + (PV_CHILDLESS if age_years >= 23 else 0.0)
    reduction = min(max(child_count - 1, 0), 4) * 0.0025
    return PV_RATE - reduction

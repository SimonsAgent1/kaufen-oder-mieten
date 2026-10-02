"""Month-by-month buy path and rent path."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

from buy_vs_rent.career import employment_for_month
from buy_vs_rent.catalog import result_sentences
from buy_vs_rent.etf import Portfolio, capital_gains_rate
from buy_vs_rent.gifts import parent_loan_interest_monthly, parent_support_cash
from buy_vs_rent.house import (
    house_sale_tax,
    extra_equity_from_price,
    monthly_owner_costs,
    owner_occupied_exemption,
    price_to_rent,
    price_to_rent_band,
    rent_while_living_tax_monthly,
    sale_gain,
)
from buy_vs_rent.household import (
    build_calendar,
    children_under,
    cold_rent,
    extra_rent,
    facts,
    leave_fraction,
    pv_rate,
    sibling_bonus,
)
from buy_vs_rent.income import (
    ELTERNGELD_INCOME_LIMIT,
    KINDERGELD_2026,
    elterngeld_month,
    kinder_freibetrag_refund,
    monthly_net,
    net_monthly_pension,
    pension_deductions,
    taxable_income,
)
from buy_vs_rent.law.de_2026 import (
    CARE_ALONE_2026,
    CARE_COUPLE_2026,
    child_rearing_entgeltpunkte,
    church_tax_rate,
    kindergeld_until_age,
)
from buy_vs_rent.mortgage import initial_payment, payment_to_clear, step_month
from buy_vs_rent.pot_ledger import (
    annuity_january_net,
    grow_avd_balances,
    january_contributions,
    ledger_from_adult,
    retire_payouts,
    surrender_value,
)
from buy_vs_rent.pension import estimate_points, pension_today_euros
from buy_vs_rent.scenario import (
    Adult,
    Scenario,
    add_months,
    care_start,
    child_rearing_adult_id,
    first_of_month,
    labels,
    month_turning,
    months_between,
    retire_month,
)
from buy_vs_rent.tax_rates import purchase_costs, transfer_tax_rate

REAL_ETF_GROWTH = 0.005
@dataclass
class Marker:
    date: str
    label: str
    chart: str


@dataclass
class YearPoint:
    date: str
    buy_nominal: float
    rent_nominal: float
    buy_real: float
    rent_real: float
    loan_balance: float
    property_value: float
    buy_etf_nominal: float = 0.0
    buy_etf_real: float = 0.0


@dataclass
class CashPoint:
    date: str
    inflation: float
    income: float
    rent_housing: float
    rent_etf: float
    rent_draw: float
    rent_left: float
    buy_rent: float
    buy_living_rent: float
    buy_interest: float
    buy_principal: float
    buy_owner: float
    buy_etf: float
    buy_draw: float
    buy_left: float


@dataclass
class PensionLine:
    id: str
    label: str
    estimate: float


@dataclass
class Result:
    nebenkosten: float
    loan_at_purchase: float
    price_at_purchase: float
    purchase_date: str | None
    equity_shortfall_today: float
    warning_below_down_payment: bool
    monthly_payment_at_purchase: float
    restschuld_at_fixation: float | None
    fixation_end: str | None
    payoff_date: str | None
    break_even_year: int | None
    buy_final_nominal: float
    rent_final_nominal: float
    buy_final_real: float
    rent_final_real: float
    etf_tax_buy: float
    etf_tax_rent: float
    house_gain: float
    house_tax: float
    house_tax_exempt: bool
    horizon_end: str
    care_start: str
    pensions: list[PensionLine] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    limits: list[str] = field(default_factory=list)
    interest_paid: float = 0.0
    rent_saving_monthly: float = 0.0
    price_to_rent: float | None = None
    price_to_rent_band: str | None = None
    series: list[YearPoint] = field(default_factory=list)
    cashflow: list[CashPoint] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)
    care_buy_real: float | None = None
    care_rent_real: float | None = None
    life_sentence: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def euro_de(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", ".")


def _percent_de(share: float) -> str:
    pct = share * 100
    if abs(pct - round(pct)) < 1e-6:
        return f"{int(round(pct))} Prozent"
    return f"{pct:.1f}".replace(".", ",") + " Prozent"


def _equity_share_clause(share: float, *, kind: str) -> str:
    """German phrasing for Nebenkosten with optional equity share of purchase price."""
    if share > 1e-9:
        pct = _percent_de(share)
        if kind == "fuer":
            return f"Nebenkosten plus {pct} des Kaufpreises"
        if kind == "unter":
            return f"den Nebenkosten plus {pct} des Kaufpreises"
        if kind == "decken":
            return f"die Nebenkosten plus {pct} des Kaufpreises decken"
        if kind == "nicht_fuer":
            return f"Nebenkosten plus {pct} des Kaufpreises"
        raise ValueError(kind)
    if kind == "fuer":
        return "die Kaufnebenkosten"
    if kind == "unter":
        return "den Nebenkosten"
    if kind == "decken":
        return "die Nebenkosten decken"
    if kind == "nicht_fuer":
        return "die Kaufnebenkosten"
    raise ValueError(kind)


def _de_date(value: date) -> str:
    return f"{value.day:02d}.{value.month:02d}.{value.year}"


def _years_held(purchase: date, sale: date) -> float:
    return months_between(purchase, sale) / 12


def _wealth_at(series: list[YearPoint], when: date) -> YearPoint | None:
    hit: YearPoint | None = None
    for point in series:
        if date.fromisoformat(point.date) <= when:
            hit = point
    return hit


def _care_wealth_at(series: list[YearPoint], care_start: date) -> YearPoint | None:
    """First year point on or after care, once the home is sold."""
    for point in series:
        when = date.fromisoformat(point.date)
        if when >= care_start and point.property_value == 0:
            return point
    return None


def _life_sentence(
    scenario: Scenario,
    names: dict[str, str],
    planned_care: date,
    purchase: date | None,
) -> str:
    clauses: list[str] = []
    adults = scenario.adults
    if len(adults) == 2 and scenario.together_from is not None:
        first, second = adults
        clauses.append(
            f"{names[first.id]} und {names[second.id]} wohnen ab {_de_date(scenario.together_from)} zusammen"
        )
    elif len(adults) == 1:
        clauses.append(names[adults[0].id])
    for index, child in enumerate(scenario.children, start=1):
        clauses.append(f"Kind {index} ab {_de_date(first_of_month(child.birth))}")
    for adult in adults:
        clauses.append(f"{names[adult.id]} spart bis {_de_date(retire_month(adult))}")
    if purchase is not None:
        clauses.append(f"Das Haus oder die Wohnung wird {_de_date(planned_care)} verkauft")
    if not clauses:
        return ""
    return ". ".join(clauses) + "."




def _pension_estimate(scenario: Scenario, adult: Adult, calendar) -> float:
    if adult.pension_gross_today is not None:
        return adult.pension_gross_today
    if adult.work_start is None:
        return 0.0
    points = estimate_points(
        work_start=adult.work_start,
        retire=retire_month(adult),
        salary_2026=adult.gross_salary,
        salary_growth=adult.salary_growth,
        inflation=scenario.beliefs.inflation,
        work_share=calendar.work_share.get(adult.id) or None,
    )
    credit = child_rearing_adult_id(scenario)
    if credit == adult.id:
        points += child_rearing_entgeltpunkte(*(child.birth for child in scenario.children))
    return pension_today_euros(points)


def _spend_down(anchor: float, elapsed: int, total: int, real_monthly: float, reserve: float) -> float:
    if anchor <= 0:
        return 0.0
    if total <= 0 or elapsed >= total:
        return reserve
    if abs(real_monthly) < 1e-12:
        excess = anchor - reserve
        if excess <= 0:
            return anchor
        return excess * (1 - elapsed / total) + reserve
    horizon = (1 + real_monthly) ** total
    growth = (1 + real_monthly) ** elapsed
    excess = anchor - reserve / horizon
    if excess <= 0:
        return anchor * growth
    remaining = excess * (growth - horizon * (growth - 1) / (horizon - 1))
    return remaining + reserve / (1 + real_monthly) ** (total - elapsed)


def _draw_target(
    anchor: float,
    elapsed: int,
    total: int,
    real_monthly: float,
    consume: float,
    inflation_factor: float,
    reserve: float,
) -> float:
    preserve = anchor * (1 + REAL_ETF_GROWTH) ** (elapsed / 12)
    if consume <= 0:
        return preserve * inflation_factor
    deplete = _spend_down(anchor, elapsed, total, real_monthly, max(0.0, reserve))
    blended = (1 - consume) * preserve + consume * max(0.0, deplete)
    return blended * inflation_factor


def _take_home(net: float, leave: float, benefit: float, retired: bool) -> float:
    if retired:
        return 0.0
    if leave <= 0:
        return net
    return net * (1.0 - leave) + benefit * leave


def _scaled_sparrate(base: float, growth: float, retired: bool, leave: float, benefit: float, net: float) -> float:
    if retired:
        return 0.0
    full = base * growth
    if leave <= 0 or net <= 0:
        return full
    ratio = benefit / net if benefit else 0.0
    return full * ((1 - leave) + leave * ratio)


@dataclass
class _Mortgage:
    balance: float
    rate: float
    payment: float
    months_left_in_fixation: int
    switched: bool = False


def path_depot_empty_before_horizon(
    path_scope: str,
    *,
    rent_etf_value: float,
    buy_etf_value: float,
    owns_home: bool,
) -> bool:
    """True when an ETF on a user-visible path is empty before the horizon.

    On buy-only runs the parallel rent ETF is not shown. After a purchase, buy-path
    wealth may sit in the house while the buy ETF is near zero.
    """
    rent_low = rent_etf_value <= 1.0
    buy_low = buy_etf_value <= 1.0
    if path_scope == "rent":
        return rent_low
    if path_scope == "buy":
        return buy_low and not owns_home
    return rent_low or (buy_low and not owns_home)


def compare(scenario: Scenario, *, display: Scenario | None = None) -> Result:
    if display is None:
        display = scenario
    beliefs = scenario.beliefs
    dwelling = scenario.dwelling
    calendar = build_calendar(scenario)
    names = labels(scenario)
    end = calendar.end
    planned_care = calendar.care_on
    owner_base = dwelling.owner_costs
    equity_share = dwelling.min_equity_share if dwelling.min_equity else 0.0

    def extra_equity_at(price: float) -> float:
        if not dwelling.min_equity:
            return 0.0
        return extra_equity_from_price(price, equity_share)

    def equity_warning_floor(price: float) -> float:
        if not dwelling.min_equity:
            return 0.0
        return extra_equity_from_price(price, dwelling.min_equity_share)
    sollzins = beliefs.sollzins if beliefs.sollzins is not None else 0.035
    anschlusszins = beliefs.anschlusszins if beliefs.anschlusszins is not None else sollzins
    transfer = dwelling.transfer_tax if dwelling.transfer_tax is not None else transfer_tax_rate(dwelling.bundesland)
    pensions = {adult.id: _pension_estimate(scenario, adult, calendar) for adult in scenario.adults}
    opening = sum(adult.depot for adult in scenario.adults)
    couple = len(scenario.adults) == 2
    care_copay = scenario.care_copay_2026
    if care_copay is None:
        care_copay = CARE_COUPLE_2026 if couple else CARE_ALONE_2026

    def allowance(month: date, inflation_factor: float) -> float:
        people = 2 if couple and scenario.married_from is not None and month >= scenario.married_from else 1
        return people * 1_000.0 * inflation_factor

    def new_portfolio(value: float) -> Portfolio:
        return Portfolio(
            value,
            annual_return=beliefs.etf_return,
            ter=beliefs.ter,
            basiszins=beliefs.basiszins,
            allowance=1_000.0,
            tax_rate=capital_gains_rate(),
            acquired_month=scenario.as_of.month,
        )

    def eligible(month: date, inflation_factor: float) -> bool:
        total = 0.0
        years = months_between(scenario.as_of, month) // 12
        for adult in scenario.adults:
            if month >= calendar.retire[adult.id]:
                continue
            gross = adult.gross_salary * (1 + adult.salary_growth) ** years
            total += taxable_income(gross, inflation_factor, pv_rate(calendar, month, adult.id))
        return total <= ELTERNGELD_INCOME_LIMIT

    def income_at_sale(when: date, inflation_factor: float) -> tuple[float, bool]:
        splitting = bool(couple and scenario.married_from is not None and when >= scenario.married_from)
        years = months_between(scenario.as_of, when) // 12
        zve = 0.0
        for adult in scenario.adults:
            if when >= calendar.retire[adult.id]:
                annual = pensions[adult.id] * inflation_factor * 12
                health, costs = pension_deductions(annual, inflation_factor)
                zve += max(0.0, annual - health - costs)
            else:
                gross = adult.gross_salary * (1 + adult.salary_growth) ** years
                zve += taxable_income(gross, inflation_factor, pv_rate(calendar, when, adult.id))
        return zve, splitting

    external_cash, _, parent_loan_balance = parent_support_cash(scenario)
    buy = new_portfolio(opening)
    rent = new_portfolio(opening + external_cash)
    mortgage: _Mortgage | None = None
    purchase: date | None = None
    property_value = 0.0
    payment_at_purchase = 0.0
    loan_at_purchase = 0.0
    price_at_purchase = 0.0
    nebenkosten_paid = purchase_costs(dwelling.purchase_price, transfer, dwelling.notary_rate, dwelling.broker_rate)
    purchase_price_paid = dwelling.purchase_price
    warning_20 = False
    house_sold = False
    house_gain_value = 0.0
    house_tax = 0.0
    exempt = False
    restschuld: float | None = None
    fixation_end: str | None = None
    payoff: str | None = None
    etf_tax_buy = 0.0
    etf_tax_rent = 0.0
    kindergeld_by_child: dict[str, tuple[float, int]] = {}
    interest_paid = 0.0
    saving_amounts: list[float] = []
    depot_empty = False
    rent_anchor: float | None = None
    buy_anchor: float | None = None
    rent_draw_months = 0
    buy_draw_months = 0
    rent_draw_total = 1
    buy_draw_total = 1
    nominal_monthly = (1 + beliefs.etf_return - beliefs.ter) ** (1 / 12) - 1
    real_monthly = (1 + nominal_monthly) / ((1 + beliefs.inflation) ** (1 / 12)) - 1
    series: list[YearPoint] = []
    cash_months: list[dict[str, float]] = []
    cashflow: list[CashPoint] = []
    total_months = months_between(scenario.as_of, end)
    separate_base = sum(adult.kaltmiete for adult in scenario.adults)
    pot_ledgers = {adult.id: ledger_from_adult(adult, scenario.as_of) for adult in scenario.adults}

    def flush_cash(when: date) -> None:
        if not cash_months:
            return
        count = len(cash_months)

        def avg(key: str) -> float:
            return sum(item[key] for item in cash_months) / count

        rent_flow = sum(item["rent_etf"] - item["rent_draw"] for item in cash_months) / count
        buy_flow = sum(item["buy_etf"] - item["buy_draw"] for item in cash_months) / count
        rent_etf = max(rent_flow, 0.0)
        rent_draw = max(-rent_flow, 0.0)
        buy_etf = max(buy_flow, 0.0)
        buy_draw = max(-buy_flow, 0.0)
        income = avg("income")
        rent_housing = avg("rent_housing")
        buy_rent = avg("buy_rent")
        buy_living = avg("buy_living_rent")
        buy_housing = buy_rent + avg("buy_interest") + avg("buy_principal") + avg("buy_owner")

        cashflow.append(
            CashPoint(
                date=when.isoformat(),
                inflation=avg("inflation"),
                income=income,
                rent_housing=rent_housing,
                rent_etf=rent_etf,
                rent_draw=rent_draw,
                rent_left=income - rent_housing - rent_etf + rent_draw,
                buy_rent=buy_rent,
                buy_living_rent=buy_living,
                buy_interest=avg("buy_interest"),
                buy_principal=avg("buy_principal"),
                buy_owner=avg("buy_owner"),
                buy_etf=buy_etf,
                buy_draw=buy_draw,
                buy_left=income - buy_housing - buy_etf - buy_living + buy_draw,
            )
        )
        cash_months.clear()

    warnings: list[str] = []
    ready_today = opening + external_cash
    move_in_today = dwelling.move_in_cost_2026
    needed_today = nebenkosten_paid + move_in_today + extra_equity_at(dwelling.purchase_price)
    if ready_today + 1e-6 < needed_today:
        if dwelling.min_equity:
            warnings.append(
                f"Heute fehlen {euro_de(needed_today - ready_today)} € für {_equity_share_clause(equity_share, kind='fuer')}. "
                "Gekauft wird im ersten Monat, in dem Depot und zusätzliches Eigenkapital das erreichen."
            )
        else:
            warnings.append(
                f"Heute fehlen {euro_de(nebenkosten_paid - ready_today)} € für die Kaufnebenkosten. "
                "Gekauft wird im ersten Monat, in dem Depot und zusätzliches Eigenkapital reichen."
            )

    for offset in range(total_months + 1):
        month = add_months(scenario.as_of, offset)
        years = offset // 12
        inflation_factor = (1 + beliefs.inflation) ** years
        inflation_path = (1 + beliefs.inflation) ** (offset / 12)
        rent_factor = (1 + beliefs.rent_growth) ** years
        owner_factor = (1 + dwelling.owner_cost_growth) ** years
        price_now = dwelling.purchase_price * (1 + dwelling.appreciation) ** years
        nebenkosten = purchase_costs(price_now, transfer, dwelling.notary_rate, dwelling.broker_rate)
        if month.month == 1:
            rent.reset_allowance()
            buy.reset_allowance()
        month_allowance = allowance(month, inflation_factor)
        rent.allowance = month_allowance
        buy.allowance = month_allowance
        here = facts(calendar, month)
        lodging_rent = here.cold_rent * rent_factor
        renting_extra = extra_rent(calendar, month, True) * inflation_factor
        if here.in_care:
            lodging_rent = care_copay * inflation_factor
            renting_extra = 0.0
        actual_rent = lodging_rent + renting_extra
        kg_age = kindergeld_until_age(scenario.kindergeld_until_25)
        kindergeld = here.children * KINDERGELD_2026 * inflation_factor
        if here.children > 0:
            unit = KINDERGELD_2026 * inflation_factor
            for child in children_under(calendar, month, kg_age):
                paid, months = kindergeld_by_child.get(child.id, (0.0, 0))
                kindergeld_by_child[child.id] = (paid + unit, months + 1)
        can_claim = eligible(month, inflation_factor)

        saves = 0.0
        take_home = 0.0
        pension_net = 0.0
        zve = 0.0
        for adult in scenario.adults:
            retired = month >= calendar.retire[adult.id]
            growth = (1 + adult.salary_growth) ** years
            pv = pv_rate(calendar, month, adult.id)
            church = church_tax_rate(dwelling.bundesland) if adult.church_tax else 0.0
            if retired:
                gross = 0.0
                net = 0.0
                usual = 0.0
            elif adult.job_changes or adult.unemployment:
                emp = employment_for_month(
                    adult,
                    month,
                    scenario,
                    years_since_as_of=years,
                    inflation_factor=inflation_factor,
                    pv_rate=pv,
                    church_rate=church,
                    has_child_in_household=here.children > 0,
                )
                gross = emp.gross
                net = emp.net
                usual = net
            else:
                gross = adult.gross_salary * growth
                net = monthly_net(gross, inflation_factor, pv, church)
                usual = monthly_net(adult.gross_salary * growth, inflation_factor, pv, church)
            leave = 0.0 if retired else leave_fraction(calendar, month, adult.id)
            benefit = elterngeld_month(
                usual,
                inflation_factor,
                can_claim,
                sibling_bonus(calendar, month, adult.id),
            )
            saves += _scaled_sparrate(adult.sparrate, growth, retired, leave, benefit, net)
            take_home += _take_home(net, leave, benefit, retired)
            if retired:
                pension_net += net_monthly_pension(
                    pensions[adult.id] * inflation_factor,
                    inflation_factor,
                    church,
                )
            else:
                zve += taxable_income(gross, inflation_factor, pv)
        pot_deduct, avd_tax_cash = january_contributions(
            scenario,
            pot_ledgers,
            month,
            inflation_factor,
            here.children,
            household_zve=zve,
            splitting=here.married,
        )
        grow_avd_balances(scenario, pot_ledgers, month, beliefs.etf_return)
        other_zve, splitting = income_at_sale(month, inflation_factor)
        pot_inflow = 0.0
        for adult in scenario.adults:
            pot_inflow += retire_payouts(
                adult,
                pot_ledgers[adult.id],
                month,
                other_zve=other_zve,
                inflation_factor=inflation_factor,
                splitting=splitting,
            )
            pot_inflow += annuity_january_net(
                adult,
                pot_ledgers[adult.id],
                month,
                other_zve=other_zve,
                inflation_factor=inflation_factor,
                splitting=splitting,
            )
        if here.all_retired:
            invest_base = 0.0
        else:
            housing_budget = separate_base * rent_factor
            invest_base = saves + kindergeld + housing_budget - actual_rent - pot_deduct + avd_tax_cash
        drawdown = here.all_retired
        parent_interest = parent_loan_interest_monthly(
            parent_loan_balance,
            scenario.parent_loan_rate if scenario.parent_loan else 0.0,
        )
        invest_rent = invest_base - parent_interest
        rent_month_net = pot_inflow + invest_rent
        buy_month_net = pot_inflow
        if invest_rent > 0 and drawdown:
            rent_anchor = None
        if drawdown and rent_anchor is None:
            rent_anchor = rent.liquidation()[1] / inflation_path
            rent_draw_months = 0
            rent_draw_total = months_between(month, end) + 1
        rent.grow_month()

        move_in = dwelling.move_in_cost_2026 * inflation_factor
        needed = nebenkosten + move_in + extra_equity_at(price_now)
        if not here.in_care and mortgage is None and buy.value + external_cash + 1e-6 >= needed:
            tax, proceeds = buy.liquidation()
            equity_cash = proceeds + external_cash
            if equity_cash >= needed:
                etf_tax_buy += tax
                buy.wipe()
                loan = price_now - (equity_cash - nebenkosten - move_in)
                nebenkosten_paid = nebenkosten
                purchase_price_paid = price_now
                if loan < 0:
                    buy.deposit(-loan, month.month)
                    loan = 0.0
                buy_anchor = None
                buy_draw_months = 0
                purchase = month
                loan_at_purchase = loan
                price_at_purchase = price_now
                property_value = price_now
                payment_at_purchase = initial_payment(loan, sollzins, beliefs.tilgung)
                mortgage = _Mortgage(
                    balance=loan,
                    rate=sollzins,
                    payment=payment_at_purchase,
                    months_left_in_fixation=beliefs.zinsbindung_years * 12,
                )
                warning_20 = equity_cash < nebenkosten + move_in + equity_warning_floor(price_now)

        buy_still_renting = mortgage is None
        buy_living_rent = 0.0
        buy_extra = 0.0 if here.in_care else extra_rent(calendar, month, buy_still_renting) * inflation_factor
        buy_rent_flow = (care_copay * inflation_factor) if here.in_care and not buy_still_renting else 0.0
        if buy_still_renting:
            buy_saving = (
                0.0
                if here.all_retired
                else saves + kindergeld + separate_base * rent_factor - (lodging_rent + buy_extra) - pot_deduct + avd_tax_cash
            )
        else:
            buy_saving = invest_base if not here.in_care else (0.0 if here.all_retired else saves + kindergeld + separate_base * rent_factor - actual_rent)
        buy_interest_flow = 0.0
        buy_principal_flow = 0.0
        buy_owner_flow = 0.0
        buy_etf_flow = buy_saving
        if mortgage is not None:
            if not house_sold and purchase is not None and month > purchase and months_between(purchase, month) % 12 == 0:
                property_value *= 1 + dwelling.appreciation
            if not house_sold and here.in_care and purchase is not None:
                years_held = _years_held(purchase, month)
                occupied = owner_occupied_exemption(
                    purchase,
                    month,
                    exclusive_own_use_until_sale=scenario.exclusive_own_use_until_sale,
                )
                exempt = occupied or years_held > 10
                other_income, splitting = income_at_sale(month, inflation_factor)
                house_gain_value = sale_gain(
                    property_value, dwelling.selling_cost_rate, purchase_price_paid, nebenkosten_paid
                )
                house_tax = house_sale_tax(
                    house_gain_value,
                    held_years=years_held,
                    owner_occupied_exemption=occupied,
                    other_income=other_income,
                    inflation_factor=inflation_factor,
                    splitting=splitting,
                )
                proceeds = property_value * (1 - dwelling.selling_cost_rate) - house_tax - mortgage.balance
                etf_tax_buy += buy.deposit(proceeds, month.month)
                property_value = 0.0
                mortgage.balance = 0.0
                mortgage.payment = 0.0
                house_sold = True
                buy_anchor = None
            owner_paid = owner_base * owner_factor
            cash_interest = 0.0
            cash_principal = 0.0
            if house_sold:
                owner_paid = 0.0
            elif mortgage.balance > 0:
                if mortgage.months_left_in_fixation == 0 and not mortgage.switched:
                    mortgage.rate = anschlusszins
                    mortgage.switched = True
                    fixation_end = month.isoformat()
                    restschuld = mortgage.balance
                if mortgage.switched:
                    months_left = months_between(month, planned_care)
                    required = payment_to_clear(mortgage.balance, mortgage.rate, months_left)
                    if required > payment_at_purchase:
                        mortgage.payment = required
                        income_now = take_home + pension_net + kindergeld
                        affordable = max(payment_at_purchase, income_now - owner_paid)
                        if mortgage.payment > affordable:
                            mortgage.payment = affordable
                interest, principal, mortgage.balance = step_month(mortgage.balance, mortgage.rate, mortgage.payment)
                if mortgage.months_left_in_fixation > 0:
                    mortgage.months_left_in_fixation -= 1
                if principal < 0:
                    cash_interest = interest + principal
                    cash_principal = 0.0
                else:
                    cash_interest = interest
                    cash_principal = principal
                if mortgage.balance <= 1e-6:
                    mortgage.balance = 0.0
                    mortgage.payment = 0.0
                    if payoff is None:
                        payoff = month.isoformat()
            if house_sold:
                buy_etf_flow = 0.0 if here.all_retired else buy_saving
            else:
                paid = cash_interest + cash_principal
                contract_paid = min(paid, payment_at_purchase)
                extra_paid = max(0.0, paid - payment_at_purchase)
                owner_out = contract_paid + owner_paid
                if here.all_retired:
                    buy_etf_flow = 0.0
                else:
                    buy_etf_flow = saves + kindergeld - owner_out + avd_tax_cash
                    if extra_paid > 0 and buy_etf_flow > 0:
                        buy_etf_flow = max(0.0, buy_etf_flow - extra_paid)
            if (
                dwelling.rent_while_living
                and mortgage is not None
                and not house_sold
                and not here.in_care
                and not buy_still_renting
            ):
                gross_rent = dwelling.rent_while_living_kalt * inflation_factor
                rent_tax = rent_while_living_tax_monthly(
                    gross_rent,
                    other_zve_annual=zve,
                    inflation_factor=inflation_factor,
                    splitting=here.married,
                )
                buy_living_rent = gross_rent - rent_tax
            buy_month_net += buy_etf_flow + buy_living_rent
            if drawdown and buy_etf_flow > 0:
                buy_anchor = None
            if drawdown and buy_anchor is None:
                buy_anchor = buy.liquidation()[1] / inflation_path
                buy_draw_months = 0
                buy_draw_total = months_between(month, end) + 1
            buy.grow_month()
            if house_sold:
                buy_rent_flow = lodging_rent
                buy_interest_flow = 0.0
                buy_principal_flow = 0.0
                buy_owner_flow = 0.0
            else:
                buy_rent_flow = 0.0
                buy_interest_flow = cash_interest
                buy_principal_flow = cash_principal
                buy_owner_flow = owner_paid
        else:
            buy_etf_flow = buy_saving
            buy_rent_flow = lodging_rent + buy_extra
            buy_month_net += buy_etf_flow
            if drawdown and buy_etf_flow > 0:
                buy_anchor = None
            if drawdown and buy_anchor is None:
                buy_anchor = buy.liquidation()[1] / inflation_path
                buy_draw_months = 0
                buy_draw_total = months_between(month, end) + 1
            buy.grow_month()

        if parent_interest > 0:
            buy_month_net -= parent_interest

        if month.month == 12 and here.children > 0 and not drawdown:
            refund = kinder_freibetrag_refund(
                zve,
                list(kindergeld_by_child.values()),
                inflation_factor,
                splitting=here.married,
            )
            kindergeld_by_child.clear()
            rent_month_net += refund
            buy_month_net += refund

        if month.month == 12:
            rent.vorabpauschale_tax()
            buy.vorabpauschale_tax()

        rent_consume = 0.0
        buy_consume = 0.0
        if drawdown and rent_anchor is not None and rent_month_net <= 1e-6:
            rent_draw_months += 1
            rent_target = _draw_target(
                rent_anchor,
                rent_draw_months,
                rent_draw_total,
                real_monthly,
                beliefs.etf_consume,
                inflation_path,
                beliefs.etf_reserve,
            )
            tax, rent_consume = rent.trim_to_net(rent_target)
            etf_tax_rent += tax
        if drawdown and buy_anchor is not None and buy_month_net <= 1e-6:
            buy_draw_months += 1
            buy_target = _draw_target(
                buy_anchor,
                buy_draw_months,
                buy_draw_total,
                real_monthly,
                beliefs.etf_consume,
                inflation_path,
                beliefs.etf_reserve,
            )
            tax, buy_consume = buy.trim_to_net(buy_target)
            etf_tax_buy += tax

        interest_paid += buy_interest_flow
        if not here.all_retired and invest_rent > 0:
            saving_amounts.append(invest_rent)
        if month < end and path_depot_empty_before_horizon(
            display.path_scope,
            rent_etf_value=rent.value,
            buy_etf_value=buy.value,
            owns_home=mortgage is not None,
        ):
            depot_empty = True
        income = take_home + pension_net + kindergeld
        buy_housing = buy_rent_flow + buy_interest_flow + buy_principal_flow + buy_owner_flow
        rent_gap = 0.0
        buy_gap = 0.0
        if here.in_care:
            rent_gap = max(0.0, actual_rent - income - rent_consume)
            rent_month_net -= rent_gap
            rent_consume += rent_gap
            buy_gap = max(0.0, buy_housing - income - buy_consume)
            buy_month_net -= buy_gap
            buy_consume += buy_gap
        if abs(rent_month_net) > 1e-9:
            etf_tax_rent += rent.deposit(rent_month_net, month.month)
        if abs(buy_month_net) > 1e-9:
            etf_tax_buy += buy.deposit(buy_month_net, month.month)
        rent_flow_net = rent_month_net - rent_consume
        rent_etf_display = max(rent_flow_net, 0.0)
        rent_draw_display = max(-rent_flow_net, 0.0)
        buy_living_display = buy_living_rent if buy_living_rent > 1 else 0.0
        buy_flow_net = buy_month_net - buy_consume
        savings_net = buy_flow_net - buy_living_display
        buy_etf_display = max(savings_net, 0.0)
        buy_draw_display = max(-savings_net, 0.0)
        cash_months.append(
            {
                "inflation": inflation_factor,
                "income": income,
                "rent_housing": actual_rent,
                "rent_etf": rent_etf_display,
                "rent_draw": rent_draw_display,
                "rent_left": income - actual_rent - rent_etf_display + rent_draw_display,
                "buy_rent": buy_rent_flow,
                "buy_living_rent": buy_living_display,
                "buy_interest": buy_interest_flow,
                "buy_principal": buy_principal_flow,
                "buy_owner": buy_owner_flow,
                "buy_etf": buy_etf_display,
                "buy_draw": buy_draw_display,
                "buy_left": income
                - buy_housing
                - buy_etf_display
                - buy_living_display
                + buy_draw_display,
            }
        )

        if month.month == 12 or month == end:
            inf = inflation_factor
            buy_equity = property_value * (1 - dwelling.selling_cost_rate) - (mortgage.balance if mortgage else 0.0)
            held_cash = 0.0 if mortgage else external_cash
            buy_etf_net = buy.liquidation()[1]
            pots_market = sum(
                surrender_value(adult, pot_ledgers[adult.id]) for adult in scenario.adults
            )
            buy_market = (
                buy_etf_net
                + (buy_equity if mortgage else 0.0)
                + held_cash
                + pots_market
                - parent_loan_balance
            )
            rent_market = rent.liquidation()[1] + pots_market - parent_loan_balance
            series.append(
                YearPoint(
                    date=month.isoformat(),
                    buy_nominal=buy_market,
                    rent_nominal=rent_market,
                    buy_real=buy_market / inf,
                    rent_real=rent_market / inf,
                    loan_balance=mortgage.balance if mortgage else 0.0,
                    property_value=property_value,
                    buy_etf_nominal=buy_etf_net,
                    buy_etf_real=buy_etf_net / inf,
                )
            )
            flush_cash(month)

    final_inflation = (1 + beliefs.inflation) ** (total_months // 12)
    final_allowance = allowance(end, final_inflation)
    rent.allowance = final_allowance
    buy.allowance = final_allowance
    rent_tax, rent_net = rent.liquidation()
    buy_tax, buy_net = buy.liquidation()
    etf_tax_rent += rent_tax
    etf_tax_buy += buy_tax
    final_pots = sum(surrender_value(adult, pot_ledgers[adult.id]) for adult in scenario.adults)
    rent_net += final_pots
    buy_net += final_pots
    rent_net -= parent_loan_balance
    if house_sold:
        buy_final = buy_net - parent_loan_balance
    elif purchase is not None and mortgage is not None:
        years_held = _years_held(purchase, end)
        occupied = owner_occupied_exemption(
            purchase,
            end,
            exclusive_own_use_until_sale=scenario.exclusive_own_use_until_sale,
        )
        exempt = occupied or years_held > 10
        other_income, splitting = income_at_sale(end, final_inflation)
        house_gain_value = sale_gain(property_value, dwelling.selling_cost_rate, purchase_price_paid, nebenkosten_paid)
        house_tax = house_sale_tax(
            house_gain_value,
            held_years=years_held,
            owner_occupied_exemption=occupied,
            other_income=other_income,
            inflation_factor=final_inflation,
            splitting=splitting,
        )
        sale_proceeds = property_value * (1 - dwelling.selling_cost_rate) - house_tax - mortgage.balance
        buy_final = buy_net + sale_proceeds - parent_loan_balance
    else:
        buy_final = buy_net + external_cash - parent_loan_balance
        if dwelling.min_equity:
            warnings.append(
                f"Innerhalb des Horizonts reichen Depot und zusätzliches Eigenkapital nicht für {_equity_share_clause(equity_share, kind='nicht_fuer')}. Beide Linien bleiben Miete."
            )
        else:
            warnings.append(
                "Innerhalb des Horizonts reichen Depot und zusätzliches Eigenkapital nicht für die Kaufnebenkosten. Beide Linien bleiben Miete."
            )
    if series:
        series[-1].buy_nominal = buy_final
        series[-1].rent_nominal = rent_net
        series[-1].buy_real = buy_final / final_inflation if final_inflation else buy_final
        series[-1].rent_real = rent_net / final_inflation if final_inflation else rent_net
        series[-1].buy_etf_nominal = buy_net
        series[-1].buy_etf_real = buy_net / final_inflation if final_inflation else buy_net

    break_even = None
    was_behind = False
    for point in series if purchase is not None else []:
        if purchase is not None and point.date < purchase.isoformat():
            continue
        if point.buy_nominal + 1 < point.rent_nominal:
            was_behind = True
            continue
        if was_behind and point.buy_nominal >= point.rent_nominal:
            break_even = int(point.date[:4])
            break

    if warning_20 and purchase is not None:
        warnings.append(
            f"Beim Kauf liegt das Eigenkapital unter {_equity_share_clause(equity_share, kind='unter')}."
        )
    if not eligible(scenario.as_of, 1.0):
        warnings.append("Das zu versteuernde Einkommen liegt über 175.000 €. Dann gibt es kein Elterngeld.")
    if depot_empty:
        warnings.append("Ein Depot ist vor dem Horizont leer, auch in der Pflege. Danach ist das keine Ersparnis mehr.")

    factor = None
    if display.path_scope != "rent":
        factor = price_to_rent(dwelling.purchase_price, scenario)
    if factor is not None:
        price_to_rent_value = factor
        price_band = price_to_rent_band(factor)
    else:
        price_to_rent_value = None
        price_band = None
    rent_saving_monthly = sum(saving_amounts) / len(saving_amounts) if saving_amounts else 0.0
    limits = [
        "Keine Vorfälligkeitsentschädigung bei einem früheren Verkauf. Kein Weg für Arbeitslosigkeit oder Trennung.",
        f"Mieten liegt nur vorn, wenn der Unterschied angelegt wird. Solange gespart wird, legt der Mietweg im Schnitt {euro_de(rent_saving_monthly)} € im Monat an.",
    ]
    if purchase is None:
        limits.append("Ohne Kauf gibt es keinen Gleichstand der beiden Wege.")
    elif break_even is None:
        limits.append("Die Kauf-Linie und die Miet-Linie kreuzen sich im Horizont nicht.")
    else:
        limits.append(f"Gleichstand im Jahr {break_even}. Die Marke sitzt auf der Vermögenslinie.")

    assumptions = _assumptions(
        scenario,
        display,
        names,
        end,
        planned_care,
        pensions,
        care_copay,
        transfer,
        exempt,
        house_gain_value,
    )
    if price_to_rent_value is not None:
        assumptions.append(
            "Der Kaufpreisfaktor nutzt die Kaltmiete des verglichenen Haushalts in Euro von heute. "
            "Bei zwei Personen die gemeinsame Kaltmiete, auch vor dem Zusammenziehen. "
            "Ein Zuschlag für eine größere Wohnung zählt nicht. "
            "Unter 20, 20 bis 25 und über 25 sind keine Empfehlung."
        )
    care_point = _care_wealth_at(series, planned_care)
    care_buy_real = care_point.buy_real if care_point else None
    care_rent_real = care_point.rent_real if care_point else None
    life_sentence = _life_sentence(scenario, names, planned_care, purchase)
    return Result(
        nebenkosten=nebenkosten_paid,
        loan_at_purchase=loan_at_purchase,
        price_at_purchase=price_at_purchase,
        purchase_date=purchase.isoformat() if purchase else None,
        equity_shortfall_today=max(0.0, needed_today - ready_today),
        warning_below_down_payment=warning_20,
        monthly_payment_at_purchase=payment_at_purchase,
        restschuld_at_fixation=restschuld,
        fixation_end=fixation_end,
        payoff_date=payoff,
        break_even_year=break_even,
        buy_final_nominal=buy_final,
        rent_final_nominal=rent_net,
        buy_final_real=buy_final / final_inflation if final_inflation else buy_final,
        rent_final_real=rent_net / final_inflation if final_inflation else rent_net,
        etf_tax_buy=etf_tax_buy,
        etf_tax_rent=etf_tax_rent,
        house_gain=house_gain_value,
        house_tax=house_tax,
        house_tax_exempt=exempt,
        horizon_end=end.isoformat(),
        care_start=planned_care.isoformat(),
        pensions=[PensionLine(adult.id, names[adult.id], pensions[adult.id]) for adult in scenario.adults],
        assumptions=assumptions,
        warnings=warnings,
        limits=limits,
        interest_paid=interest_paid,
        rent_saving_monthly=rent_saving_monthly,
        price_to_rent=price_to_rent_value,
        price_to_rent_band=price_band,
        series=series,
        cashflow=cashflow,
        markers=_break_even_mark(
            _markers(scenario, names, end, purchase, fixation_end, payoff),
            series,
            break_even,
        ),
        care_buy_real=care_buy_real,
        care_rent_real=care_rent_real,
        life_sentence=life_sentence,
    )


def _assumptions(
    scenario: Scenario,
    display: Scenario,
    names: dict[str, str],
    end: date,
    planned_care: date,
    pensions: dict[str, float],
    care_copay: float,
    transfer: float,
    exempt: bool,
    house_gain_value: float,
) -> list[str]:
    beliefs = scenario.beliefs
    dwelling = scenario.dwelling
    who = " und ".join(names[adult.id] for adult in scenario.adults)
    depots = ", ".join(f"{names[adult.id]} {euro_de(adult.depot)} €" for adult in scenario.adults)
    pension_bits = ", ".join(f"{names[adult.id]} {euro_de(pensions[adult.id])} €" for adult in scenario.adults)
    rent_only = display.path_scope == "rent"
    land_share = "Ein niedrigerer Anteil ist im Modell der Weg, den Grund und Boden auszuklammern."
    lines = [
        f"Start ist der {_de_date(scenario.as_of)}. Die Rechnung läuft bis zum {_de_date(end)}. "
        f"Pflege beginnt am {_de_date(planned_care)}. Gearbeitet wird bis zum jeweils gesetzten Rentenalter.",
        f"Die ETF-Depots sind das Startkapital: {depots}.",
        f"Zusätzliches Eigenkapital ist {euro_de(scenario.equity_cash)} € und ist Bargeld. "
        "Beim Kauf zahlt es die Nebenkosten und senkt den Kredit. Wer mietet, legt denselben Betrag im Startmonat in den ETF.",
        f"Die ETF-Rendite liegt bei {beliefs.etf_return * 100:.1f} % nominal im Jahr, die TER bei {beliefs.ter * 100:.2f} %.",
        f"Die gesetzliche Rente ist brutto in Euro von heute: {pension_bits} im Monat. "
        "Sie wächst mit der Inflation und wird um Einkommensteuer, Soli, gegebenenfalls Kirchensteuer und die halben Beiträge zur Kranken- und Pflegeversicherung gekürzt.",
        f"Die Mietsteigerung liegt bei {beliefs.rent_growth * 100:.1f} % pro Jahr.",
        f"Die Inflation liegt bei {beliefs.inflation * 100:.1f} % pro Jahr.",
    ]
    if not rent_only:
        rate_text = f"{dwelling.owner_costs_rate * 100:.2f}".replace(".", ",")
        owner_euro = (
            f"Eigentümerkosten sind {rate_text} % des Kaufpreises im Jahr, "
            f"also {euro_de(dwelling.owner_costs)} € im Monat."
        )
        lines.extend(
            [
                f"Die Wertsteigerung von Haus oder Wohnung liegt bei {dwelling.appreciation * 100:.1f} % pro Jahr. "
                f"Der Kaufpreis startet bei {euro_de(dwelling.purchase_price)} € und steigt bis zum Kauf mit.",
                f"Grunderwerbsteuer in {dwelling.bundesland}: {transfer * 100:.2f} % des Kaufpreises.",
                f"Notar und Grundbuch: {dwelling.notary_rate * 100:.1f} % des Kaufpreises.",
                f"Makler, Käuferanteil: {dwelling.broker_rate * 100:.2f} % des Kaufpreises.",
                owner_euro,
                land_share,
            ]
        )
        if dwelling.min_equity:
            share = dwelling.min_equity_share
            lines.append(
                "Gekauft wird erst, wenn Depot und zusätzliches Eigenkapital "
                f"{_equity_share_clause(share, kind='decken')}."
            )
        else:
            lines.append("Gekauft wird, sobald Depot und zusätzliches Eigenkapital die Nebenkosten decken.")
        if dwelling.move_in_cost_2026 > 0:
            lines.append(
                f"Einmalige Einzugskosten in Euro von 2026: {euro_de(dwelling.move_in_cost_2026)}. "
                "Sie werden zum Kaufmonat mit der Inflation angehoben, bar mit den Nebenkosten gezahlt und nicht finanziert."
            )
    else:
        lines.append(f"Bundesland für die Kirchensteuer: {dwelling.bundesland}.")
    if scenario.extra_rent is not None:
        lines.append(
            f"Solange ein Weg noch mietet, kommen von {_de_date(scenario.extra_rent.start)} bis {_de_date(scenario.extra_rent.until)} "
            f"{euro_de(scenario.extra_rent.amount_2026)} € Miete in Euro von 2026 dazu."
        )
    if scenario.children:
        bits = []
        for index, child in enumerate(scenario.children, start=1):
            parts = [f"{names[item.adult_id]} {item.months} Monate" for item in child.leave if item.months]
            if parts:
                bits.append(f"Kind {index}: {', '.join(parts)}")
        if bits:
            lines.append("Elternzeit zählt keine Entgeltpunkte. " + " ".join(bits) + ".")
    lines.append(f"Jede Person spart bis zur eigenen Rente. Entnommen wird, wenn {who} in Rente sind.")
    lines.extend(result_sentences(scenario))
    lines.append(
        "Heiz- und andere Kosten, die Mieter und Eigentümer beide tragen, sind nicht enthalten. "
        f"Mit dem Eintritt in die Pflege wird das Haus oder die Wohnung verkauft. Ab dann zahlen beide Wege {euro_de(care_copay)} € "
        "Eigenanteil in Euro von 2026. Der hessische Schnitt im ersten Heimjahr lag am 1. Juli 2026 bei 3.431 €. "
        "Das ist eine Illustration, kein Pflegeplan."
    )
    if exempt:
        if scenario.dwelling.rent_while_living:
            lines.append(
                "Die Verkaufssteuer ist 0 €; der vermietete Teil zählt nicht als Verkaufsgewinn in diesem Lauf. "
                f"Der steuerfreie Gewinn beträgt {euro_de(house_gain_value)} €."
            )
        elif scenario.exclusive_own_use_until_sale:
            lines.append(
                "Die Verkaufssteuer ist 0 € nur bei ausschließlicher Eigennutzung bis zum Verkauf. "
                f"Der steuerfreie Gewinn beträgt {euro_de(house_gain_value)} €."
            )
        else:
            lines.append(
                "Die Steuer auf den Verkauf von Haus oder Wohnung ist 0 €, weil die Haltedauer über zehn Jahre liegt "
                f"oder der Gewinn nicht positiv ist. Der steuerfreie Gewinn beträgt {euro_de(house_gain_value)} €."
            )
    return lines


def _break_even_mark(markers: list[Marker], series: list[YearPoint], year: int | None) -> list[Marker]:
    if year is None:
        return markers
    hit = next((point.date for point in series if point.date.startswith(str(year))), None)
    if hit is None:
        return markers
    return [*markers, Marker(hit, "Gleichstand", "wealth")]


def _markers(
    scenario: Scenario,
    names: dict[str, str],
    end: date,
    purchase: date | None,
    fixation_end: str | None,
    payoff: str | None,
) -> list[Marker]:
    buckets: dict[tuple[str, str], list[str]] = {}

    def add(when: date | None, label: str, chart: str) -> None:
        if when is None or when < scenario.as_of or when > end:
            return
        for item in (("wealth", "loan") if chart == "both" else (chart,)):
            labels_here = buckets.setdefault((when.isoformat(), item), [])
            if label not in labels_here:
                labels_here.append(label)

    if scenario.together_from is not None:
        add(scenario.together_from, "Zusammenziehen", "wealth")
    if scenario.married_from is not None:
        add(scenario.married_from, "Heirat", "wealth")
    for index, child in enumerate(scenario.children, start=1):
        add(first_of_month(child.birth), f"Kind {index}", "wealth")
        add(month_turning(child.birth, 25), f"Kind {index} wird 25", "wealth")
    retire_days: dict[date, list[str]] = {}
    for adult in scenario.adults:
        when = retire_month(adult)
        retire_days.setdefault(when, []).append(f"{names[adult.id]} Rente")
    for when, bits in retire_days.items():
        add(when, " · ".join(bits), "wealth")
    add(purchase, "Kauf", "both")
    if fixation_end:
        add(date.fromisoformat(fixation_end), "Zinsbindung", "loan")
    if payoff:
        add(date.fromisoformat(payoff), "Abbezahlt", "loan")
    care = care_start(scenario)
    if care <= end:
        add(care, "Pflege", "wealth")
    horizon_adult = next(adult for adult in scenario.adults if adult.id == scenario.horizon.adult_id)
    add(end, f"{names[horizon_adult.id]} {scenario.horizon.age}", "wealth")
    return [Marker(day, " · ".join(text), chart) for (day, chart), text in buckets.items()]

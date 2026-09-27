"""What is true in one month, read from the scenario."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from buy_vs_rent.law.de_2026 import employee_pv_rate
from buy_vs_rent.scenario import (
    Child,
    Scenario,
    add_months,
    age_years,
    care_month,
    care_start,
    first_of_month,
    horizon_end,
    kindergeld_window,
    months_between,
    retire_month,
)


@dataclass
class MonthFacts:
    cold_rent: float
    children: int
    in_care: bool
    married: bool
    all_retired: bool
    anyone_working: bool


@dataclass
class Calendar:
    scenario: Scenario
    retire: dict[str, date]
    care: dict[str, date]
    leave: dict[tuple[date, str], float] = field(default_factory=dict)
    leave_for: dict[tuple[date, str], set[str]] = field(default_factory=dict)
    work_share: dict[str, dict[int, float]] = field(default_factory=dict)

    @property
    def end(self) -> date:
        return horizon_end(self.scenario)

    @property
    def care_on(self) -> date:
        return care_start(self.scenario)


def build_calendar(scenario: Scenario) -> Calendar:
    calendar = Calendar(
        scenario=scenario,
        retire={adult.id: retire_month(adult) for adult in scenario.adults},
        care={adult.id: care_month(adult) for adult in scenario.adults},
    )
    for child in scenario.children:
        cursor = first_of_month(child.birth)
        for assignment in child.leave:
            for _ in range(assignment.months):
                key = (cursor, assignment.adult_id)
                calendar.leave[key] = min(1.0, calendar.leave.get(key, 0.0) + 1.0)
                calendar.leave_for.setdefault(key, set()).add(child.id)
                cursor = add_months(cursor, 1)
    for adult in scenario.adults:
        shares: dict[int, float] = {}
        seen: dict[int, float] = {}
        for (month, adult_id), fraction in calendar.leave.items():
            if adult_id != adult.id:
                continue
            seen[month.year] = seen.get(month.year, 0.0) + fraction
        for year, months_off in seen.items():
            shares[year] = max(0.0, 1.0 - months_off / 12)
        calendar.work_share[adult.id] = shares
    return calendar


def cold_rent(calendar: Calendar, month: date) -> float:
    scenario = calendar.scenario
    if len(scenario.adults) == 1:
        return scenario.adults[0].kaltmiete
    assert scenario.together_from is not None
    if month >= scenario.together_from:
        return scenario.shared_kaltmiete
    return sum(adult.kaltmiete for adult in scenario.adults)


def children_under(calendar: Calendar, month: date, age: int = 25) -> list[Child]:
    found = []
    for child in calendar.scenario.children:
        start = first_of_month(child.birth)
        if age == 25:
            _, end = kindergeld_window(child)
        else:
            end = date(child.birth.year + age, child.birth.month, 1)
        if start <= month < end:
            found.append(child)
    return found


def child_count(calendar: Calendar, month: date) -> int:
    return len(children_under(calendar, month, 25))


def leave_fraction(calendar: Calendar, month: date, adult_id: str) -> float:
    return calendar.leave.get((month, adult_id), 0.0)


def sibling_bonus(calendar: Calendar, month: date, adult_id: str) -> bool:
    """Elterngeld sibling bonus: leave for a child while another child is under three."""
    covered = calendar.leave_for.get((month, adult_id), set())
    if not covered:
        return False
    for child in calendar.scenario.children:
        if child.id in covered:
            continue
        age_months = months_between(first_of_month(child.birth), month)
        if 0 <= age_months < 36:
            return True
    return False


def pv_rate(calendar: Calendar, month: date, adult_id: str) -> float:
    adult = next(item for item in calendar.scenario.adults if item.id == adult_id)
    return employee_pv_rate(child_count(calendar, month), age_years(adult.birth, month))


def extra_rent(calendar: Calendar, month: date, still_renting: bool) -> float:
    event = calendar.scenario.extra_rent
    if event is None or not still_renting:
        return 0.0
    if event.start <= month < event.until:
        return event.amount_2026
    return 0.0


def facts(calendar: Calendar, month: date) -> MonthFacts:
    retired = [month >= calendar.retire[adult.id] for adult in calendar.scenario.adults]
    married = calendar.scenario.married_from is not None and month >= calendar.scenario.married_from
    return MonthFacts(
        cold_rent=cold_rent(calendar, month),
        children=child_count(calendar, month),
        in_care=month >= calendar.care_on,
        married=married,
        all_retired=all(retired),
        anyone_working=not all(retired),
    )

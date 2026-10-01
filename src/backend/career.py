"""Job segments and Arbeitslosengeld between jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from buy_vs_rent.law.de_2026 import monthly_net
from buy_vs_rent.scenario import Adult, Scenario, add_months, age_years, first_of_month, months_between, retire_month


@dataclass(frozen=True)
class EmploymentMonth:
    gross: float
    net: float


def arbeitslosengeld_rate(has_child_in_household: bool) -> float:
    """§ 149 SGB III: 60 % or 67 % of the model net before unemployment."""
    return 0.67 if has_child_in_household else 0.60


def arbeitslosengeld_benefit(previous_net: float, has_child_in_household: bool) -> float:
    return max(0.0, previous_net) * arbeitslosengeld_rate(has_child_in_household)


def arbeitslosengeld_months(age_years: int) -> int:
    """§ 147 SGB III simplified duration after the qualifying period."""
    if age_years < 50:
        return 12
    if age_years < 55:
        return 15
    if age_years < 58:
        return 18
    return 24


def _segments(adult: Adult) -> list[tuple[date, float, float]]:
    if not adult.job_changes:
        return []
    ordered = sorted(adult.job_changes, key=lambda item: item.start)
    start = adult.work_start or ordered[0].start
    segments: list[tuple[date, float, float]] = [
        (first_of_month(start), adult.gross_salary, adult.salary_growth)
    ]
    for change in ordered:
        segments.append((first_of_month(change.start), change.gross_salary, change.salary_growth))
    return segments


def _segment_gross(segment_start: date, month: date, base_gross: float, growth: float) -> float:
    years = months_between(segment_start, month) // 12
    return base_gross * (1 + growth) ** years


def _job_gross(adult: Adult, month: date, years_since_as_of: int) -> float:
    segments = _segments(adult)
    if not segments:
        if adult.work_start is None or month < first_of_month(adult.work_start):
            return 0.0
        return adult.gross_salary * (1 + adult.salary_growth) ** years_since_as_of
    active = segments[0]
    for seg in segments:
        if seg[0] <= month:
            active = seg
        else:
            break
    return _segment_gross(active[0], month, active[1], active[2])


def _next_job_start(adult: Adult, after: date) -> date:
    for change in sorted(adult.job_changes, key=lambda item: item.start):
        if first_of_month(change.start) > after:
            return first_of_month(change.start)
    return date(9999, 12, 1)


def job_employment_for_month(
    adult: Adult,
    month: date,
    years_since_as_of: int,
    *,
    inflation_factor: float,
    pv_rate: float,
    church_rate: float,
) -> EmploymentMonth:
    gross = _job_gross(adult, month, years_since_as_of)
    net = monthly_net(gross, inflation_factor, pv_rate, church_rate)
    return EmploymentMonth(gross, net)


def employment_for_month(
    adult: Adult,
    month: date,
    scenario: Scenario,
    *,
    years_since_as_of: int,
    inflation_factor: float,
    pv_rate: float,
    church_rate: float,
    has_child_in_household: bool,
) -> EmploymentMonth:
    if month >= retire_month(adult):
        return EmploymentMonth(0.0, 0.0)

    for stretch in sorted(adult.unemployment, key=lambda item: item.start):
        start = first_of_month(stretch.start)
        if month < start:
            continue
        duration = arbeitslosengeld_months(age_years(adult.birth, start))
        alg_end = add_months(start, duration)
        if month < alg_end:
            prev_month = add_months(start, -1)
            prev_years = months_between(scenario.as_of, prev_month) // 12
            prev = job_employment_for_month(
                adult,
                prev_month,
                prev_years,
                inflation_factor=inflation_factor,
                pv_rate=pv_rate,
                church_rate=church_rate,
            )
            benefit = arbeitslosengeld_benefit(prev.net, has_child_in_household)
            return EmploymentMonth(0.0, benefit)
        next_job = _next_job_start(adult, start)
        if month < next_job:
            return EmploymentMonth(0.0, 0.0)

    return job_employment_for_month(
        adult,
        month,
        years_since_as_of,
        inflation_factor=inflation_factor,
        pv_rate=pv_rate,
        church_rate=church_rate,
    )

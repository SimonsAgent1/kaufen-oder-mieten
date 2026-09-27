"""Gesetzliche Rente from Entgeltpunkte. The slider starts here and can move."""

from __future__ import annotations

from datetime import date

from buy_vs_rent.law.de_2026 import BEITRAGSBEMESSUNGSGRENZE, DURCHSCHNITTSENTGELT, RENTENWERT_2026


def _anchor(table: dict[int, float], year: int, inflation: float) -> float:
    if year in table:
        return table[year]
    years_after = year - 2026
    return table[2026] * (1 + inflation) ** years_after


def points_for_year(gross: float, year: int, inflation: float) -> float:
    if gross <= 0:
        return 0.0
    ceiling = _anchor(BEITRAGSBEMESSUNGSGRENZE, year, inflation)
    average = _anchor(DURCHSCHNITTSENTGELT, year, inflation)
    return min(gross, ceiling) / average


def estimate_points(
    *,
    work_start: date,
    retire: date,
    salary_2026: float,
    salary_growth: float,
    inflation: float,
    work_share: dict[int, float] | None = None,
) -> float:
    """Points from work_start through the month before retire. Past pay is walked back by salary growth."""
    total = 0.0
    for year in range(work_start.year, retire.year + 1):
        gross = salary_2026 * (1 + salary_growth) ** (year - 2026)
        if year == work_start.year:
            months = 12 - work_start.month + 1
            if work_start.day > 1 and work_start.month == retire.month and work_start.year == retire.year:
                months = 0
            # A start mid-month counts as that month. September 2023 is 4 months.
            if work_start.day > 1:
                months = 12 - work_start.month + 1
            fraction = months / 12
        elif year == retire.year:
            # Work stops at the birthday month, so that month is excluded.
            fraction = max(0, retire.month - 1) / 12
        else:
            fraction = 1.0
        if year == work_start.year and year == retire.year:
            fraction = max(0, retire.month - work_start.month) / 12
        if work_share and year in work_share:
            fraction *= work_share[year]
        total += points_for_year(gross, year, inflation) * fraction
    return total


def pension_today_euros(points: float) -> float:
    """Monthly pension in 2026 euros. Later Rentenwert inflation is applied when it is paid."""
    return points * RENTENWERT_2026

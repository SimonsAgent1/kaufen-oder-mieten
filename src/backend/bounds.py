"""Chat and import bounds shared with the scenario validator."""

from __future__ import annotations

from datetime import date

from buy_vs_rent.scenario import (
    Scenario,
    age_years,
    care_month,
    first_of_month,
    horizon_end,
    month_turning,
    months_between,
)
from buy_vs_rent.tax_rates import TRANSFER_TAX

YEAR_MIN = 1930
YEAR_MAX = 2100
RETIRE_MIN = 55
RETIRE_MAX = 75
CARE_MIN = 60
CARE_MAX = 110
HORIZON_AGE_MIN = 1
HORIZON_AGE_MAX = 120
LEAVE_MONTHS_TOTAL = 12
LEAVE_MONTHS_MAX = 12


def _month_ok(value: date) -> bool:
    return YEAR_MIN <= value.year <= YEAR_MAX


def validate_scenario(scenario: Scenario) -> None:
    as_of = scenario.as_of
    if not _month_ok(as_of):
        raise ValueError("Der Startmonat liegt außerhalb des erlaubten Jahresbereichs.")

    if scenario.dwelling.bundesland not in TRANSFER_TAX:
        raise ValueError("Das Bundesland ist unbekannt.")

    older_birth = min(adult.birth for adult in scenario.adults)
    for adult in scenario.adults:
        if not _month_ok(adult.birth):
            raise ValueError("Der Geburtsmonat liegt außerhalb des erlaubten Jahresbereichs.")
        if adult.birth > as_of:
            raise ValueError("Der Geburtsmonat darf nicht nach dem Startmonat liegen.")
        if not RETIRE_MIN <= adult.retire_age <= RETIRE_MAX:
            raise ValueError(
                f"Das Renteneintrittsalter muss zwischen {RETIRE_MIN} und {RETIRE_MAX} liegen."
            )
        age_now = age_years(adult.birth, as_of)
        if age_now >= 67:
            if adult.retire_age > age_now:
                raise ValueError("Das Renteneintrittsalter darf das heutige Alter nicht überschreiten.")
        elif adult.retire_age <= age_now:
            raise ValueError("Das Renteneintrittsalter muss über dem heutigen Alter liegen.")
        if adult.work_start is not None:
            if not _month_ok(adult.work_start):
                raise ValueError("Der erste Arbeitsmonat liegt außerhalb des erlaubten Jahresbereichs.")
            if adult.work_start < adult.birth:
                raise ValueError("Der erste Arbeitsmonat darf nicht vor dem Geburtsmonat liegen.")
            if adult.work_start > as_of:
                raise ValueError("Der erste Arbeitsmonat darf nicht nach dem Startmonat liegen.")
        if not CARE_MIN <= adult.care_age <= CARE_MAX:
            raise ValueError(f"Das Pflegealter muss zwischen {CARE_MIN} und {CARE_MAX} liegen.")
        if age_years(adult.birth, as_of) < adult.care_age and care_month(adult) <= as_of:
            raise ValueError("Der Pflegebeginn muss nach dem Startmonat liegen.")

    for child in scenario.children:
        if not _month_ok(child.birth):
            raise ValueError("Der Geburtsmonat des Kindes liegt außerhalb des erlaubten Jahresbereichs.")
        if child.birth <= older_birth:
            raise ValueError("Der Geburtsmonat des Kindes muss nach dem der älteren Person liegen.")
        assigned = sum(item.months for item in child.leave)
        if child.leave and assigned != LEAVE_MONTHS_TOTAL:
            raise ValueError("Elternzeit je Kind muss zusammen zwölf Monate ergeben.")
        for item in child.leave:
            if item.months < 0 or item.months > LEAVE_MONTHS_MAX:
                raise ValueError("Elternzeit je Person ist höchstens zwölf Monate.")

    if len(scenario.adults) == 2:
        if scenario.together_from is not None:
            if not _month_ok(scenario.together_from):
                raise ValueError("Der Monat zum Zusammenziehen liegt außerhalb des erlaubten Jahresbereichs.")
        if scenario.married_from is not None:
            if not _month_ok(scenario.married_from):
                raise ValueError("Der Heiratsmonat liegt außerhalb des erlaubten Jahresbereichs.")

    assert scenario.horizon is not None
    if not HORIZON_AGE_MIN <= scenario.horizon.age <= HORIZON_AGE_MAX:
        raise ValueError(
            f"Das Endalter muss zwischen {HORIZON_AGE_MIN} und {HORIZON_AGE_MAX} liegen."
        )
    younger = min(scenario.adults, key=lambda adult: (adult.birth, adult.id))
    younger_age = age_years(younger.birth, as_of)
    if scenario.horizon.age <= younger_age:
        raise ValueError("Das Endalter muss über dem heutigen Alter der jüngeren Person liegen.")
    if scenario.horizon.age >= CARE_MIN and scenario.horizon.age <= younger.care_age:
        raise ValueError("Das Endalter muss über dem Pflegealter liegen.")
    if horizon_end(scenario) <= as_of:
        raise ValueError("Der Horizont liegt vor dem Startmonat.")

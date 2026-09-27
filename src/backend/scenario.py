"""The only input to a comparison: facts, beliefs, and a dwelling."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import yaml
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LINK_FIELDS = ("purchase_price", "bundesland", "notary_rate", "broker_rate", "owner_costs")
MAX_CHILDREN = 8


def first_of_month(value: date) -> date:
    return date(value.year, value.month, 1)


def month_turning(birth: date, age: int) -> date:
    """The month in which this birthday reaches `age`."""
    return date(birth.year + age, birth.month, 1)


def add_months(month: date, count: int) -> date:
    index = month.year * 12 + (month.month - 1) + count
    return date(index // 12, index % 12 + 1, 1)


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


class Leave(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adult_id: str
    months: int = Field(ge=0, le=12)


class Adult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=40)
    label: str = ""
    birth: date
    work_start: date | None = None
    retire_age: int = Field(default=67, ge=55, le=75)
    care_age: int = Field(default=75, ge=60, le=110)
    gross_salary: float = Field(ge=0, le=1_000_000)
    salary_growth: float = Field(default=0.02, ge=-0.05, le=0.2)
    depot: float = Field(ge=0, le=5_000_000)
    sparrate: float = Field(ge=0, le=50_000)
    pension_gross_today: float | None = Field(default=None, ge=0, le=20_000)
    kaltmiete: float = Field(ge=0, le=20_000)
    church_tax: bool = False
    church_tax_consent: bool = False


class Child(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=40)
    birth: date
    room_until_age: int = Field(default=20, ge=0, le=30)
    leave: list[Leave] = Field(default_factory=list)


class ExtraRent(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    amount_2026: float = Field(ge=0, le=20_000)
    start: date = Field(alias="from")
    until: date

    @field_validator("start", "until")
    @classmethod
    def _month(cls, value: date) -> date:
        return first_of_month(value)


class Horizon(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adult_id: str
    age: int = Field(ge=1, le=120)


class Dwelling(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purchase_price: float = Field(gt=0, le=5_000_000)
    bundesland: str
    transfer_tax: float | None = Field(default=None, ge=0, le=0.15)
    notary_rate: float = Field(default=0.02, ge=0, le=0.1)
    broker_rate: float = Field(default=0.0357, ge=0, le=0.1)
    selling_cost_rate: float = Field(default=0.0, ge=0, le=0.2)
    owner_costs: float = Field(default=250, ge=0, le=10_000)
    owner_costs_rate: float | None = Field(default=None, ge=0, le=0.1)
    owner_cost_growth: float = Field(default=0.02, ge=-0.05, le=0.15)
    appreciation: float = Field(default=0.025, ge=-0.05, le=0.15)
    min_equity: bool = True
    move_in_cost_2026: float = Field(default=0, ge=0, le=500_000)


class Beliefs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rent_growth: float = Field(default=0.025, ge=-0.05, le=0.15)
    etf_return: float = Field(default=0.087, ge=-0.05, le=0.2)
    ter: float = Field(default=0.0015, ge=0, le=0.05)
    basiszins: float = Field(default=0.032, ge=0, le=0.1)
    inflation: float = Field(default=0.02, ge=0, le=0.1)
    etf_consume: float = Field(default=0, ge=0, le=1)
    etf_reserve: float = Field(default=0, ge=0, le=5_000_000)
    tilgung: float = Field(default=0.02, ge=0, le=0.2)
    zinsbindung_years: int = Field(default=15, ge=1, le=40)
    household_rate: bool = True
    sollzins: float | None = Field(default=None, ge=0, le=0.10)
    anschlusszins: float | None = Field(default=None, ge=0, le=0.10)
    church_tax: bool = False


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=1)
    path_scope: Literal["both", "buy", "rent"] = "both"
    as_of: date
    adults: list[Adult] = Field(min_length=1, max_length=2)
    together_from: date | None = None
    married_from: date | None = None
    shared_kaltmiete: float = Field(default=0, ge=0, le=20_000)
    children: list[Child] = Field(default_factory=list, max_length=MAX_CHILDREN)
    extra_rent: ExtraRent | None = None
    equity_cash: float = Field(default=0, ge=0, le=5_000_000)
    horizon: Horizon | None = None
    care_copay_2026: float | None = Field(default=None, ge=0, le=30_000)
    dwelling: Dwelling
    beliefs: Beliefs = Field(default_factory=Beliefs)

    @field_validator("as_of")
    @classmethod
    def _as_of_month(cls, value: date) -> date:
        return first_of_month(value)

    @field_validator("together_from", "married_from")
    @classmethod
    def _optional_month(cls, value: date | None) -> date | None:
        if value is None:
            return None
        return first_of_month(value)

    @model_validator(mode="after")
    def _household(self) -> Scenario:
        if self.version != 1:
            raise ValueError("Nur Szenario-Version 1 wird gelesen.")
        ids = [adult.id for adult in self.adults]
        if len(ids) != len(set(ids)):
            raise ValueError("Jede Person braucht eine eigene id.")
        child_ids = [child.id for child in self.children]
        if len(child_ids) != len(set(child_ids)):
            raise ValueError("Jedes Kind braucht eine eigene id.")
        if set(ids) & set(child_ids):
            raise ValueError("Kinder und Erwachsene teilen keine id.")
        known = set(ids)
        if len(self.adults) == 1:
            if self.together_from is not None or self.married_from is not None:
                raise ValueError("Zusammenziehen und Heirat gibt es erst bei zwei Personen.")
        elif self.together_from is None:
            raise ValueError("Zwei Personen brauchen den Monat, ab dem sie zusammenwohnen.")
        for child in self.children:
            assigned = sum(item.months for item in child.leave)
            if child.leave and assigned != 12:
                raise ValueError("Elternzeit je Kind muss zusammen zwölf Monate ergeben.")
            for item in child.leave:
                if item.adult_id not in known:
                    raise ValueError("Elternzeit verweist auf eine unbekannte Person.")
        if self.horizon is None:
            younger = min(self.adults, key=lambda adult: (adult.birth, adult.id))
            self.horizon = Horizon(adult_id=younger.id, age=100)
        elif self.horizon.adult_id not in known:
            raise ValueError("Der Horizont verweist auf eine unbekannte Person.")
        if self.extra_rent is not None and self.extra_rent.until <= self.extra_rent.start:
            raise ValueError("Die höhere Miete endet nach ihrem Beginn.")
        for adult in self.adults:
            if adult.church_tax and not adult.church_tax_consent:
                raise ValueError(
                    "Kirchensteuer braucht zuerst die ausdrückliche Einwilligung auf der Seite."
                )
            if not adult.church_tax_consent:
                adult.church_tax = False
        if self.beliefs.church_tax:
            for adult in self.adults:
                if adult.church_tax_consent:
                    adult.church_tax = True
        from buy_vs_rent.bounds import validate_scenario

        validate_scenario(self)
        return self


def label_for(adult: Adult, index: int) -> str:
    text = adult.label.strip()
    if text:
        return text
    return "Du" if index == 0 else "Zweite Person"


def labels(scenario: Scenario) -> dict[str, str]:
    return {adult.id: label_for(adult, index) for index, adult in enumerate(scenario.adults)}


def retire_month(adult: Adult) -> date:
    return month_turning(adult.birth, adult.retire_age)


def care_month(adult: Adult) -> date:
    return month_turning(adult.birth, adult.care_age)


def horizon_end(scenario: Scenario) -> date:
    assert scenario.horizon is not None
    adult = next(item for item in scenario.adults if item.id == scenario.horizon.adult_id)
    return month_turning(adult.birth, scenario.horizon.age)


def care_start(scenario: Scenario) -> date:
    return min(care_month(adult) for adult in scenario.adults)


def kindergeld_window(child: Child) -> tuple[date, date]:
    """Inclusive start month and exclusive end, the month of the 25th birthday."""
    start = first_of_month(child.birth)
    return start, month_turning(child.birth, 25)


def age_years(birth: date, month: date) -> int:
    years = month.year - birth.year
    if month.month < birth.month:
        years -= 1
    return years


def load_scenario(path: Path) -> Scenario:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)
    return Scenario.model_validate(data)


def parse_property_link(payload: dict) -> dict:
    """Keep the dwelling fields a shared link may carry. Everything else is dropped."""
    if not isinstance(payload, dict):
        raise ValueError("Der Wohnungslink enthält kein Objekt.")
    kept = {key: payload[key] for key in LINK_FIELDS if key in payload}
    if "purchase_price" not in kept or "bundesland" not in kept:
        raise ValueError("Der Wohnungslink braucht Preis und Bundesland.")
    dwelling = Dwelling.model_validate({**kept})
    return {key: getattr(dwelling, key) for key in LINK_FIELDS if key in kept}

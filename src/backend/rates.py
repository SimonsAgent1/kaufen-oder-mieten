"""Bundesbank new-business mortgage rates, plus a Beleihungsauslauf spread."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

FLOW = "BBIM1"
SERIES = {
    "to_1": "M.DE.B.A2C.F.R.A.2250.EUR.N",
    "to_5": "M.DE.B.A2C.I.R.A.2250.EUR.N",
    "to_10": "M.DE.B.A2C.O.R.A.2250.EUR.N",
    "over_10": "M.DE.B.A2C.P.R.A.2250.EUR.N",
}
CACHE_PATH = Path(__file__).resolve().parents[2] / ".cache" / "bundesbank.json"
LAST_RESORT_RATE = 0.035


@dataclass(frozen=True)
class MarketRate:
    annual_rate: float
    period: str
    series: str
    source: str
    effective_rate: float = 0.0


def nominal_from_effective(effective: float) -> float:
    """Monthly-compounded nominal rate whose effective annual rate is `effective`."""
    if effective <= 0:
        return 0.0
    return 12 * ((1 + effective) ** (1 / 12) - 1)


def series_for_fixation(years: float) -> str:
    if years <= 1:
        return SERIES["to_1"]
    if years <= 5:
        return SERIES["to_5"]
    if years <= 10:
        return SERIES["to_10"]
    return SERIES["over_10"]


def parse_observations(payload: str) -> list[tuple[str, float]]:
    """Accept Bundesbank CSV. Semicolon rows may use a comma as the decimal mark."""
    rows: list[tuple[str, float]] = []
    for raw in payload.splitlines():
        line = raw.strip()
        if not line:
            continue
        delimiter = ";" if ";" in line else ","
        parts = [part.strip().strip('"') for part in line.split(delimiter)]
        if len(parts) < 2:
            continue
        period, value = parts[0], parts[1]
        if period.lower() in {"time_period", "date"} or "OBS" in value:
            continue
        if not value or value in {"-", "."}:
            continue
        try:
            number = float(value.replace(",", ".").replace("%", ""))
        except ValueError:
            continue
        # Effective rates are published in percent, for example 3.72 or 1.00.
        if number >= 1:
            number = number / 100
        rows.append((period, number))
    return rows


def beleihung_spread(ltv: float) -> float:
    """Documented model, not a bank quote. Around 80% matches the average."""
    if ltv <= 0.60:
        return -0.0015
    if ltv <= 0.90:
        return 0.0
    return 0.0030


def household_spread(adults: int) -> float:
    """Small discount versus the LTV-adjusted average. Not a bank quote.

    A second adult widens the discount. Gender and any degree are not used.
    """
    return -0.0010 if adults >= 2 else -0.0005


def _read_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def _write_cache(data: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data), encoding="utf-8")


def fetch_market_rate(fixation_years: float, *, opener=None) -> MarketRate:
    series = series_for_fixation(fixation_years)
    url = f"https://api.statistiken.bundesbank.de/rest/data/{FLOW}/{series}?lastNObservations=8&format=csv"
    cache = _read_cache()
    try:
        open_url = opener or urlopen
        with open_url(url, timeout=8) as response:
            payload = response.read().decode("utf-8")
        observations = parse_observations(payload)
        if not observations:
            raise ValueError("Bundesbank-Antwort ohne Wert")
        period, effective = observations[-1]
        nominal = nominal_from_effective(effective)
        cache[series] = {"period": period, "rate": nominal, "effective": effective}
        _write_cache(cache)
        return MarketRate(nominal, period, series, "bundesbank", effective)
    except (URLError, TimeoutError, ValueError, OSError):
        cached = cache.get(series)
        if cached:
            stored = float(cached["rate"])
            effective = float(cached["effective"]) if "effective" in cached else stored
            nominal = stored if "effective" in cached else nominal_from_effective(stored)
            return MarketRate(nominal, str(cached["period"]), series, "cache", effective)
        return MarketRate(LAST_RESORT_RATE, "kein Stand", series, "fallback", LAST_RESORT_RATE)

"""HTTP API and the static page."""

from __future__ import annotations

import base64
import binascii
import json
import logging
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from buy_vs_rent.catalog import render_rules_html
from buy_vs_rent.profile import load_profile
from buy_vs_rent.rates import beleihung_spread, fetch_market_rate, household_spread
from buy_vs_rent.scenario import Scenario, load_scenario, parse_property_link
from buy_vs_rent.simulate import compare
from buy_vs_rent.tax_rates import TRANSFER_TAX

FRONTEND = Path(str(files("buy_vs_rent").joinpath("frontend")))
DEMO = Path(str(files("buy_vs_rent").joinpath("profile.example.yaml")))

logger = logging.getLogger("buy_vs_rent.access")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _frontend_dir() -> Path:
    repo = _repo_root() / "src" / "frontend"
    if repo.is_dir():
        return repo
    return FRONTEND


def _demo_path() -> Path:
    example = _repo_root() / "private" / "profile.example.yaml"
    if example.is_file():
        return example
    staged = Path(__file__).resolve().parent / "profile.example.yaml"
    if staged.is_file():
        return staged
    return DEMO

app = FastAPI(title="Kaufen oder mieten")
app.mount("/static", StaticFiles(directory=_frontend_dir()), name="static")


@app.middleware("http")
async def log_compare_without_body(request: Request, call_next):
    response = await call_next(request)
    if request.method == "POST" and request.url.path == "/api/compare":
        host = request.client.host if request.client else "-"
        logger.info("compare status=%s client=%s", response.status_code, host)
    return response


def _validation_message(exc: RequestValidationError) -> str:
    for item in exc.errors():
        if item.get("type") == "value_error":
            msg = str(item.get("msg", ""))
            if msg.startswith("Value error, "):
                return msg.removeprefix("Value error, ")
            return msg
        if item.get("type") == "missing":
            return "Bitte alle Pflichtfelder ausfüllen."
    return "Die Eingaben sind unvollständig oder ungültig."


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": _validation_message(exc)})


def _de_number(value: float, signed: bool = False) -> str:
    text = f"{value:+.2f}" if signed else f"{value:.2f}"
    return text.replace(".", ",")


def evaluate(scenario: Scenario) -> dict:
    """Fill an untouched mortgage rate from the Bundesbank series, then compare."""
    market = fetch_market_rate(scenario.beliefs.zinsbindung_years)
    user_soll = scenario.beliefs.sollzins
    user_anschluss = scenario.beliefs.anschlusszins
    probe_soll = user_soll if user_soll is not None else market.annual_rate
    probe_anschluss = user_anschluss if user_anschluss is not None else probe_soll
    probe = scenario.model_copy(
        update={
            "beliefs": scenario.beliefs.model_copy(
                update={"sollzins": probe_soll, "anschlusszins": probe_anschluss}
            )
        }
    )
    probed = compare(probe)
    suggested = market.annual_rate
    effective = market.effective_rate or market.annual_rate
    nominal_note = ""
    if market.effective_rate and abs(market.effective_rate - market.annual_rate) > 1e-6:
        nominal_note = f" Als Sollzins zählt der nominale Satz {_de_number(market.annual_rate * 100)} %."
    steps = [
        f"Marktüblicher Effektivzins {_de_number(effective * 100)} % "
        f"(Bundesbank {market.period}, Quelle: {market.source}). "
        "Das ist ein bundesweiter Durchschnitt, kein Angebot."
        + nominal_note
    ]
    ltv = None
    if user_soll is None and probed.purchase_date and probed.price_at_purchase:
        ltv = probed.loan_at_purchase / probed.price_at_purchase
        spread = beleihung_spread(ltv)
        suggested += spread
        steps.append(
            f"Beleihungsauslauf {ltv * 100:.0f} %: {_de_number(spread * 100, signed=True)} Prozentpunkte."
        )
    elif user_soll is None:
        steps.append("Kein Kauf im Horizont, daher kein Beleihungsauslauf-Abschlag.")
    if user_soll is None and scenario.beliefs.household_rate:
        personal = household_spread(len(scenario.adults))
        suggested += personal
        who = "zwei Personen" if len(scenario.adults) == 2 else "eine Person"
        steps.append(
            f"Lage: {_de_number(personal * 100, signed=True)} Prozentpunkte, {who}, kein weiterer Kredit. "
            "Geschlecht und Abschluss gehen nicht in den Zins ein."
        )
    soll = user_soll if user_soll is not None else suggested
    anschluss = user_anschluss if user_anschluss is not None else soll
    steps.append(f"Sollzins {_de_number(soll * 100)} %, Anschlusszins {_de_number(anschluss * 100)} %.")
    result = compare(
        scenario.model_copy(
            update={"beliefs": scenario.beliefs.model_copy(update={"sollzins": soll, "anschlusszins": anschluss})}
        )
    )
    payload = result.as_dict()
    payload["sollzins_used"] = soll
    payload["anschlusszins_used"] = anschluss
    payload["rate_steps"] = steps
    payload["beleihungsauslauf"] = ltv
    payload["market_period"] = market.period
    payload["market_source"] = market.source
    return payload


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_frontend_dir() / "index.html")


@app.get("/impressum")
def impressum_page() -> FileResponse:
    return FileResponse(_frontend_dir() / "impressum.html")


@app.get("/regeln", response_class=HTMLResponse)
def rules_page() -> str:
    return render_rules_html()


def app_version() -> str:
    return version("buy-vs-rent")


@app.get("/api/version")
def api_version() -> dict[str, str]:
    return {"version": app_version()}


@app.get("/api/defaults")
def defaults() -> dict:
    return {
        "bundeslaender": TRANSFER_TAX,
        "kindergeld": 259,
        "basiszins": 0.032,
        "law": "de-2026",
        "app_version": app_version(),
    }


@app.get("/api/demo")
def demo() -> dict:
    return load_scenario(_demo_path()).model_dump(mode="json", by_alias=True)


@app.get("/api/profile")
def profile() -> dict:
    scenario = load_profile()
    if scenario is None:
        raise HTTPException(status_code=404, detail="Keine gespeicherten Angaben.")
    return scenario.model_dump(mode="json", by_alias=True)


@app.get("/api/market-rate")
def market_rate(zinsbindung_years: int = 15) -> dict:
    rate = fetch_market_rate(zinsbindung_years)
    return {
        "annual_rate": rate.annual_rate,
        "period": rate.period,
        "series": rate.series,
        "source": rate.source,
    }


@app.get("/api/wohnung")
def wohnung(data: str) -> dict:
    pad = "=" * (-len(data) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(data + pad))
        return parse_property_link(payload)
    except (ValueError, json.JSONDecodeError, binascii.Error, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Der Wohnungslink ist ungültig.") from exc


@app.post("/api/compare")
def compare_route(body: Scenario) -> dict:
    return evaluate(body)

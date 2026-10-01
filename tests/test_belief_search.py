"""Belief search synonyms (client-only, mirrors belief-search.js)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SYNONYMS = {
    "gehalt": "gross",
    "einkommen": "gross",
    "lohn": "gross",
    "hausgeld": "owner_costs_rate",
    "miete": "kaltmiete",
    "zins": "sollzins",
    "depot": "etf_return",
}


def normalize_query(query: str) -> str:
    text = query.strip().lower().replace("ß", "ss")
    return text


def synonym_target(query: str) -> str | None:
    normalized = normalize_query(query)
    if not normalized or re.fullmatch(r"\d+([.,]\d+)?", normalized):
        return None
    return SYNONYMS.get(normalized)


def test_synonym_maps_match_js_catalog():
    js = (ROOT / "src" / "frontend" / "belief-search.js").read_text(encoding="utf-8")
    for key, target in SYNONYMS.items():
        assert f"{key}: \"{target}\"" in js or f"{key}: '{target}'" in js


def test_synonym_maps_gehalt_to_gross():
    assert synonym_target("Gehalt") == "gross"


def test_synonym_depot_maps_to_etf_return():
    assert synonym_target("depot") == "etf_return"


def test_numeric_query_is_not_a_synonym():
    assert synonym_target("1200000") is None


def test_synonym_search_collects_all_matching_controls():
    js = (ROOT / "src" / "frontend" / "belief-search.js").read_text(encoding="utf-8")
    assert "function findBeliefControls" in js
    assert "function controlsForTarget" in js
    assert "return controls.filter((control) => match(control.dataset.controlName" in js


def test_belief_search_opens_collapsed_slider_groups():
    app = (ROOT / "src" / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "findBeliefControls" in app
    assert 'closest("details.slider-group")?.setAttribute("open", "")' in app

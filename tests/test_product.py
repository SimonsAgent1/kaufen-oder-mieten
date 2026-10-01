import math
import re
import subprocess
from pathlib import Path

from buy_vs_rent.api import _demo_path, evaluate
from buy_vs_rent.rates import MarketRate
from buy_vs_rent.scenario import load_scenario

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "private" / "profile.example.yaml"


def test_profile_example_runs_in_the_page_and_terminal(monkeypatch):
    monkeypatch.setattr(
        "buy_vs_rent.api.fetch_market_rate",
        lambda years: MarketRate(0.03, "2026-08", "series", "bundesbank"),
    )
    assert EXAMPLE.is_file()
    assert _demo_path().resolve() == EXAMPLE.resolve()
    result = evaluate(load_scenario(EXAMPLE))
    assert math.isfinite(result["buy_final_nominal"])
    assert math.isfinite(result["rent_final_nominal"])
    assert result["purchase_date"]


def test_save_row_hidden_beats_result_action_button_display():
    css = (ROOT / "src" / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert ".result-actions button[hidden]" in css
    assert "display: none !important" in css.split(".result-actions button[hidden]")[1].split("}")[0]


def test_git_tracks_no_plan_or_private_profile():
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    assert "PLAN.md" not in tracked
    assert "examples/demo.yaml" not in tracked
    assert "src/backend/frontend" not in tracked
    private = [line for line in tracked if line.startswith("private/")]
    assert set(private) <= {"private/profile.example.yaml"}
    ignored = subprocess.check_output(
        [
            "git",
            "check-ignore",
            "PLAN.md",
            "private/profile.yaml",
            ".cursor/rules/agent-board.mdc",
        ],
        cwd=ROOT,
        text=True,
    ).split()
    assert ignored == [
        "PLAN.md",
        "private/profile.yaml",
        ".cursor/rules/agent-board.mdc",
    ]


def test_public_tree_has_no_personal_names():
    paths = [
        ROOT / "README.md",
        ROOT / "src" / "backend" / "simulate.py",
        ROOT / "src" / "frontend" / "index.html",
        ROOT / "src" / "frontend" / "app.js",
        EXAMPLE,
    ]
    impressum = ROOT / "src" / "frontend" / "impressum.html"
    name_checks = (
        (re.compile(r"\bSimon\b"), "Simon"),
        (re.compile(r"\bNatalie\b"), "Natalie"),
    )
    literal_banned = ("Arheilgen", "TU Darmstadt")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if path.name == "index.html":
            assert 'href="/impressum">Impressum</a>' in text
            assert "privacy-notice" not in text
            assert "<title>Kaufen oder mieten – Vergleich für einen Haushalt</title>" in text
            assert 'name="description"' in text
            assert "Keine Empfehlung." in text
            assert 'id="horizon-month"' in text
            assert 'id="horizon-month-year"' in text
            assert 'href="/favicon.svg"' in text
            assert "Kostenlos, ohne Werbung, ohne Cookies." in text
            assert "ohne Tracking" not in text
            assert 'id="complete-rent"' in text
            assert 'id="complete-buy"' in text
            assert 'class="path-view"' not in text
            assert "start-surface" in text
            assert 'class="start-limit"' in text
            assert 'href="/regeln">Rechenregeln</a>' in text
            assert 'href="/modell">Modell</a>' in text
            assert 'id="beliefs-search"' in text
            assert 'id="save-row"' in text
            assert "ausschließlicher Eigennutzung bis dahin" in text
            assert "nicht jede deutsche Vorschrift" in text
            assert "Welcher Haushalt" not in text
            assert "Wähle einen gespeicherten" not in text
            assert "günstiger" not in text.lower()
        if path.name == "app.js":
            assert "Die Zahlen gelten für diesen Haushalt" in text
        if path == impressum:
            text = re.sub(
                r'<main class="legal-body impressum-notice">.*?</main>',
                "",
                text,
                count=1,
                flags=re.DOTALL,
            )
        for pattern, label in name_checks:
            assert not pattern.search(text), (path, label)
        for banned in literal_banned:
            assert banned not in text, path

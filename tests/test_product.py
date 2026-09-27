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
        EXAMPLE,
    ]
    name_checks = (
        (re.compile(r"\bSimon\b"), "Simon"),
        (re.compile(r"\bNatalie\b"), "Natalie"),
    )
    literal_banned = ("Arheilgen", "TU Darmstadt")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if path.name == "index.html":
            text = re.sub(
                r'<div class="privacy-notice">.*?</div>',
                "",
                text,
                count=1,
                flags=re.DOTALL,
            )
        for pattern, label in name_checks:
            assert not pattern.search(text), (path, label)
        for banned in literal_banned:
            assert banned not in text, path

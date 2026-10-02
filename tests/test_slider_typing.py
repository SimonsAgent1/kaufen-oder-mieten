from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_slider_values_are_editable_in_app_js():
    app = (ROOT / "src" / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "function parseTypedValue" in app
    assert "function clampSnap" in app
    assert 'out.contentEditable = "true"' in app
    assert 'event.key === "Enter"' in app
    assert "applySliderValue" in app

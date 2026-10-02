from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_buy_flow_chart_does_not_stack_living_rent():
    app = (ROOT / "src" / "frontend" / "app.js").read_text(encoding="utf-8")
    assert '["buy_living_rent", "Kaltmiete im eigenen Haus"' not in app.split("const BUY_FLOW =")[1].split("];")[0]
    assert '["buy_living_rent", "Kaltmiete im eigenen Haus"]' in app


def test_chart_hover_omits_zero_rows():
    app = (ROOT / "src" / "frontend" / "app.js").read_text(encoding="utf-8")
    assert ".filter((item) => Math.abs(item.values[index]) > 0.5)" in app

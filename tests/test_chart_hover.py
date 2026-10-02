from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_buy_flow_chart_does_not_stack_living_rent():
    app = (ROOT / "src" / "frontend" / "app.js").read_text(encoding="utf-8")
    assert '["buy_living_rent", "Kaltmiete im eigenen Haus"' not in app.split("const BUY_FLOW =")[1].split("];")[0]
    assert '["buy_living_rent", "Kaltmiete im eigenen Haus"]' in app


def test_chart_hover_omits_zero_rows():
    app = (ROOT / "src" / "frontend" / "app.js").read_text(encoding="utf-8")
    assert ".filter((item) => Math.abs(item.values[index]) > 0.5)" in app


def test_buy_flow_ubrig_scale_ignores_living_rent_extent():
    app = (ROOT / "src" / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "function flowUbrigChartValue(" in app
    assert 'chartKey !== "buy-flow" || leftKey !== "buy_left"' in app
    assert "flowUbrigChartValue(point, leftLayerKey, real, chartKey)" in app
    assert "function flowStackAxisMax(" in app
    assert 'if (chartKey === "buy-flow") return max' in app
    assert 'if (chartKey === "buy-flow") continue' in app


def test_profile_row_refreshes_from_api():
    scenario = (ROOT / "src" / "frontend" / "scenario.js").read_text(encoding="utf-8")
    assert "existing.scenario = scenario" in scenario
    assert "if (rows.some((row) => row.id === PROFILE_ROW_ID)) return" not in scenario

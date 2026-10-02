from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_buy_flow_chart_does_not_stack_living_rent():
    app = (ROOT / "src" / "frontend" / "app.js").read_text(encoding="utf-8")
    assert '["buy_living_rent", "Kaltmiete im eigenen Haus"' not in app.split("const BUY_FLOW =")[1].split("];")[0]
    assert '["buy_living_rent", "Kaltmiete im eigenen Haus"]' in app


def test_chart_hover_omits_zero_rows():
    app = (ROOT / "src" / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "if (Math.abs(value) <= 0.5) return false" in app


def test_buy_flow_ubrig_includes_living_rent_in_band():
    app = (ROOT / "src" / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "function flowUbrigChartValue(" in app
    assert "return flowAmount(point, leftKey, real)" in app
    assert "flowUbrigChartValue(point, leftLayerKey, real, chartKey)" in app
    assert "function flowStackAxisMax(" in app
    assert "(totals[index] || 0) + Math.max(0, left)" in app


def test_charts_use_step_lines_between_years():
    app = (ROOT / "src" / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "function chartStepLineD(" in app
    assert "function chartStackLayerStepD(" in app
    assert 'chartStepLineD(x, values, y)' in app
    assert "if (isEtf && leftVal < -1) return false" in app


def test_profile_row_refreshes_from_api():
    scenario = (ROOT / "src" / "frontend" / "scenario.js").read_text(encoding="utf-8")
    assert "existing.scenario = scenario" in scenario
    assert "if (rows.some((row) => row.id === PROFILE_ROW_ID)) return" not in scenario

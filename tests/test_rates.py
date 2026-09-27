import json

import pytest

from buy_vs_rent.rates import (
    CACHE_PATH,
    beleihung_spread,
    fetch_market_rate,
    nominal_from_effective,
    parse_observations,
    series_for_fixation,
)


def test_one_percent_is_scaled():
    rows = parse_observations("TIME_PERIOD;OBS_VALUE\n2026-01;1,00\n")
    assert rows == [("2026-01", 0.01)]


def test_parse_bundesbank_csv_uses_last_observation():
    payload = "TIME_PERIOD;OBS_VALUE\n2026-06;3,21\n2026-07;\n2026-08;3.45\n"
    rows = parse_observations(payload)
    assert rows[-1] == ("2026-08", 0.0345)
    assert rows[0] == ("2026-06", 0.0321)


def test_series_follows_zinsbindung():
    assert series_for_fixation(1).endswith("F.R.A.2250.EUR.N")
    assert series_for_fixation(5).endswith("I.R.A.2250.EUR.N")
    assert series_for_fixation(10).endswith("O.R.A.2250.EUR.N")
    assert series_for_fixation(15).endswith("P.R.A.2250.EUR.N")


@pytest.mark.parametrize(
    ("ltv", "spread"),
    [(0.60, -0.0015), (0.80, 0.0), (0.95, 0.003)],
)
def test_beleihung_spread(ltv, spread):
    assert beleihung_spread(ltv) == spread


def test_cached_fallback_when_client_fails(tmp_path, monkeypatch):
    cache = tmp_path / "bundesbank.json"
    series = series_for_fixation(15)
    cache.write_text(json.dumps({series: {"period": "2026-08", "rate": 0.0362}}), encoding="utf-8")
    monkeypatch.setattr("buy_vs_rent.rates.CACHE_PATH", cache)

    def boom(url, timeout=8):
        raise TimeoutError("down")

    rate = fetch_market_rate(15, opener=boom)
    assert rate.source == "cache"
    assert rate.effective_rate == 0.0362
    assert rate.annual_rate == nominal_from_effective(0.0362)
    assert rate.period == "2026-08"
    assert CACHE_PATH == cache or rate.source == "cache"

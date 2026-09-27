import pytest

from buy_vs_rent.etf import Portfolio, capital_gains_rate


def _portfolio(**kwargs) -> Portfolio:
    defaults = dict(annual_return=0.0, ter=0.0, basiszins=0.02, allowance=1_000, tax_rate=capital_gains_rate())
    defaults.update(kwargs)
    return Portfolio(0, **defaults)


def test_monthly_sparplan_matches_hand_calculation():
    pot = _portfolio(annual_return=0.12, allowance=0)
    for _ in range(12):
        pot.deposit(100)
        pot.grow_month()
    expected = 0.0
    for _ in range(12):
        expected = (expected + 100) * (1.12 ** (1 / 12))
    assert pot.value == expected


def test_trim_to_leaves_the_target_and_pays_tax_from_the_gain():
    pot = Portfolio(10_000, annual_return=0, ter=0, basiszins=0, allowance=0, tax_rate=0.25)
    pot.value = 12_000
    tax, cash = pot.trim_to(10_000)
    assert pot.value == 10_000
    assert pot.basis == pytest.approx(10_000 * 10_000 / 12_000)
    gain_fraction = 2_000 / 12_000
    taxable = 2_000 * gain_fraction * 0.7
    assert tax == pytest.approx(taxable * 0.25)
    assert cash == pytest.approx(2_000 - tax)


def test_trim_to_does_nothing_below_the_target():
    pot = Portfolio(10_000, annual_return=0, ter=0, basiszins=0, allowance=0, tax_rate=0.25)
    tax, cash = pot.trim_to(11_000)
    assert (tax, cash) == (0.0, 0.0)
    assert pot.value == 10_000


def test_ter_reduces_growth():
    plain = Portfolio(10_000, annual_return=0.07, ter=0.0, basiszins=0, allowance=0, tax_rate=0)
    costly = Portfolio(10_000, annual_return=0.07, ter=0.002, basiszins=0, allowance=0, tax_rate=0)
    plain.grow_month()
    costly.grow_month()
    assert costly.value < plain.value
    assert costly.value == 10_000 * (1.068 ** (1 / 12))


def test_no_tax_without_a_gain():
    pot = Portfolio(10_000, annual_return=0, ter=0, basiszins=0.03, allowance=0, tax_rate=0.26)
    assert pot.vorabpauschale_tax() == 0
    tax, net = pot.liquidation()
    assert tax == 0
    assert net == 10_000


def test_vorabpauschale_teilfreistellung_and_allowance():
    pot = Portfolio(100_000, annual_return=0, ter=0, basiszins=0.02, allowance=1_000, tax_rate=capital_gains_rate())
    pot.value = 110_000
    # Gain is 10,000. Basisertrag is 100,000 * 0.02 * 0.7 = 1,400.
    # Taxable after 30% exemption is 980, which the 1,000 € allowance covers.
    assert pot.vorabpauschale_tax() == 0
    assert pot.basis == 100_000 + 1_400


def test_sale_does_not_tax_vorabpauschale_twice():
    rate = capital_gains_rate()
    pot = Portfolio(100_000, annual_return=0, ter=0, basiszins=0.02, allowance=0, tax_rate=rate)
    pot.value = 110_000
    vorab_tax = pot.vorabpauschale_tax()
    vorab = 1_400
    taxable = vorab * 0.7
    assert vorab_tax == taxable * rate
    sale_tax, _ = pot.liquidation()
    gain = pot.value - pot.basis
    assert gain == pot.value - (100_000 + vorab)
    assert sale_tax == gain * 0.7 * rate


def test_capital_gains_rate_is_abgeltung_plus_soli():
    assert capital_gains_rate() == 0.25 * 1.055


def test_forced_sale_pays_tax_on_the_gain():
    rate = capital_gains_rate()
    pot = Portfolio(110_000, annual_return=0, ter=0, basiszins=0, allowance=0, tax_rate=rate)
    pot.basis = 100_000
    tax = pot.deposit(-50_000)
    assert tax > 800
    assert pot.value < 60_000


def test_september_purchase_uses_four_twelfths():
    rate = capital_gains_rate()
    pot = Portfolio(100_000, annual_return=0, ter=0, basiszins=0.032, allowance=0, tax_rate=rate, acquired_month=9)
    pot.value = 120_000
    full = 100_000 * 0.032 * 0.7
    assert pot.vorabpauschale_tax() == pytest.approx(full * 4 / 12 * 0.7 * rate)


def test_allowance_is_not_used_twice_in_one_year():
    rate = capital_gains_rate()
    pot = Portfolio(200_000, annual_return=0, ter=0, basiszins=0.02, allowance=1_000, tax_rate=rate)
    pot.value = 220_000
    pot.vorabpauschale_tax()
    sale_tax, _ = pot.liquidation()
    gain = pot.value - pot.basis
    assert sale_tax == pytest.approx(gain * 0.7 * rate)

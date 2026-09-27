"""Monthly equity-ETF sparplan with Teilfreistellung, Vorabpauschale, and sale tax."""

from __future__ import annotations

EQUITY_EXEMPTION = 0.30


def capital_gains_rate() -> float:
    """25% Abgeltungsteuer plus 5.5% Soli on that tax."""
    return 0.25 * 1.055


def _months_held_fraction(month: int) -> float:
    """Share of the year after an acquisition in `month` (1 = January). §18 Abs. 2 InvStG."""
    return max(0.0, 13 - month) / 12


class Portfolio:
    def __init__(
        self,
        value: float,
        *,
        annual_return: float,
        ter: float,
        basiszins: float,
        allowance: float,
        tax_rate: float,
        acquired_month: int = 1,
    ) -> None:
        self.value = value
        self.basis = value
        self.annual_return = annual_return
        self.ter = ter
        self.basiszins = basiszins
        self.allowance = allowance
        self.allowance_used = 0.0
        self.tax_rate = tax_rate
        self.year_start = value
        self.year_fraction = _months_held_fraction(acquired_month)
        self.contributions_ytd = 0.0
        self.acquisition_weight = 0.0

    def reset_allowance(self) -> None:
        self.allowance_used = 0.0

    def deposit(self, amount: float, month: int = 1) -> float:
        """Add cash, or sell enough to raise `amount` after tax. Returns the tax paid."""
        if amount >= 0:
            self.value += amount
            self.basis += amount
            self.contributions_ytd += amount
            self.acquisition_weight += amount * _months_held_fraction(month)
            return 0.0
        return self._sell_for_cash(-amount)

    def _sell_for_cash(self, needed: float) -> float:
        if self.value <= 1e-9 or needed <= 0:
            return 0.0
        gain_fraction = max(0.0, self.value - self.basis) / self.value
        taxable_per_euro = gain_fraction * (1 - EQUITY_EXEMPTION)
        remaining = max(0.0, self.allowance - self.allowance_used)
        if taxable_per_euro <= 1e-15 or self.tax_rate <= 0:
            withdraw = min(self.value, needed)
            tax = 0.0
            taxable = 0.0
        else:
            covered = remaining / taxable_per_euro
            if needed <= covered:
                withdraw = min(self.value, needed)
                taxable = withdraw * taxable_per_euro
                tax = 0.0
            else:
                net_factor = 1 - taxable_per_euro * self.tax_rate
                withdraw = (needed - remaining * self.tax_rate) / net_factor if net_factor > 1e-9 else self.value
                withdraw = min(self.value, max(0.0, withdraw))
                taxable = withdraw * taxable_per_euro
                tax = max(0.0, taxable - remaining) * self.tax_rate
        if self.value > 1e-9:
            self.basis *= 1 - withdraw / self.value
        self.value -= withdraw
        self.allowance_used += min(remaining, taxable)
        return tax

    def trim_to(self, target: float) -> tuple[float, float]:
        """Sell so the portfolio value equals `target`. Returns tax and cash after tax."""
        if self.value <= target + 1e-9 or self.value <= 1e-9:
            return 0.0, 0.0
        withdraw = self.value - target
        gain_fraction = max(0.0, self.value - self.basis) / self.value
        taxable = withdraw * gain_fraction * (1 - EQUITY_EXEMPTION)
        remaining = max(0.0, self.allowance - self.allowance_used)
        tax = max(0.0, taxable - remaining) * self.tax_rate
        self.basis *= target / self.value
        self.value = target
        self.allowance_used += min(remaining, taxable)
        return tax, withdraw - tax

    def trim_to_net(self, target_net: float) -> tuple[float, float]:
        """Sell so the after-tax liquidation value equals `target_net`."""
        if self.liquidation()[1] <= target_net + 1e-6 or self.value <= 1e-9:
            return 0.0, 0.0
        lo, hi = 0.0, self.value
        for _ in range(60):
            mid = (lo + hi) / 2
            clone = self.snapshot()
            clone.trim_to(mid)
            if clone.liquidation()[1] > target_net:
                hi = mid
            else:
                lo = mid
        return self.trim_to(hi)

    def grow_month(self) -> None:
        monthly = (1 + self.annual_return - self.ter) ** (1 / 12) - 1
        self.value *= 1 + monthly

    def vorabpauschale_tax(self) -> float:
        """Tax the year's deemed return. New shares count for the months after purchase."""
        gain = max(0.0, self.value - self.year_start - self.contributions_ytd)
        base = self.year_start * self.year_fraction + self.acquisition_weight
        basisertrag = base * self.basiszins * 0.7
        vorab = max(0.0, min(basisertrag, gain))
        taxable = vorab * (1 - EQUITY_EXEMPTION)
        remaining = max(0.0, self.allowance - self.allowance_used)
        tax = max(0.0, taxable - remaining) * self.tax_rate
        self.allowance_used += min(remaining, taxable)
        self.value -= tax
        self.basis += vorab
        self.year_start = self.value
        self.year_fraction = 1.0
        self.contributions_ytd = 0.0
        self.acquisition_weight = 0.0
        return tax

    def liquidation(self) -> tuple[float, float]:
        """Return sale tax and after-tax proceeds. Uses only the allowance left this year."""
        gain = max(0.0, self.value - self.basis)
        taxable = gain * (1 - EQUITY_EXEMPTION)
        remaining = max(0.0, self.allowance - self.allowance_used)
        tax = max(0.0, taxable - remaining) * self.tax_rate
        return tax, self.value - tax

    def wipe(self) -> None:
        self.value = 0.0
        self.basis = 0.0
        self.year_start = 0.0
        self.year_fraction = 1.0
        self.contributions_ytd = 0.0
        self.acquisition_weight = 0.0

    def snapshot(self) -> "Portfolio":
        clone = Portfolio(
            self.value,
            annual_return=self.annual_return,
            ter=self.ter,
            basiszins=self.basiszins,
            allowance=self.allowance,
            tax_rate=self.tax_rate,
        )
        clone.basis = self.basis
        clone.year_start = self.year_start
        clone.year_fraction = self.year_fraction
        clone.contributions_ytd = self.contributions_ytd
        clone.acquisition_weight = self.acquisition_weight
        clone.allowance_used = self.allowance_used
        return clone

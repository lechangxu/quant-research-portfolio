"""Factors: cross-sectional signals computed from price history.

A factor maps a price panel to a same-shaped panel of scores where
*higher = more attractive to hold long*. The framework handles
cross-sectional standardization and portfolio construction; a factor is
responsible only for its own lookback math and for never using future data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Factor(ABC):
    name: str

    @abstractmethod
    def compute(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Return factor scores, same index/columns as `prices`.

        The value at (date t, symbol s) must be computable from data at or
        before the close of day t. The backtester applies scores with a
        one-day execution lag, so factors must *not* shift internally.
        NaN = "do not rank this asset on this day".
        """


class MomentumFactor(Factor):
    """Simple trailing return over `lookback` days."""

    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self.name = f"mom_{lookback}d"

    def compute(self, prices: pd.DataFrame) -> pd.DataFrame:
        return prices / prices.shift(self.lookback) - 1.0


class LowVolFactor(Factor):
    """Negative trailing realized volatility (higher score = calmer asset).

    Included as the canonical *candidate* in the demo because low-vol style
    factors are the classic "strong standalone IC, dies at the portfolio
    gate" case — see docs/03-negative-results-log.md.
    """

    def __init__(self, window: int = 20):
        self.window = window
        self.name = f"lowvol_{window}d"

    def compute(self, prices: pd.DataFrame) -> pd.DataFrame:
        return -prices.pct_change().rolling(self.window).std()

"""Risk-adjusted metrics. Daily-return in, statistics out.

Annualization uses 365 periods — these are crypto series that trade every
day. If you plug in equity-market data, pass `periods=252` explicitly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sharpe(returns: pd.Series, periods: int = 365) -> float:
    r = returns.dropna()
    if len(r) < 2 or r.std() < 1e-15:
        return np.nan
    return float(r.mean() / r.std() * np.sqrt(periods))


def max_drawdown(returns: pd.Series) -> float:
    """Most negative peak-to-trough move of the cumulative curve, e.g. -0.35."""
    r = returns.dropna()
    if r.empty:
        return np.nan
    curve = (1 + r).cumprod()
    return float((curve / curve.cummax() - 1).min())


def yearly_sharpe(returns: pd.Series, periods: int = 365) -> pd.Series:
    """Sharpe computed independently per calendar year."""
    return returns.groupby(returns.index.year).apply(
        lambda g: sharpe(g, periods), include_groups=False
    )

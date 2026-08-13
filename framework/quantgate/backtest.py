"""Portfolio construction and simulation.

Deliberately plain: equal-weight top-K long / bottom-K short, fixed
rebalance cadence, linear fees on traded turnover, one-day execution lag
(scores from close of day t-1 drive positions earning the return of day t).

Simplifications, stated so nobody mistakes this for a production engine:
- fees charge on |Δweight| at rebalance only (drift between rebalances
  is not charged);
- no slippage model, no borrow costs, no funding — the 2x-fee window in
  the A/B gate exists precisely because this list is incomplete;
- positions are marked on daily closes only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def cross_sectional_z(scores: pd.DataFrame) -> pd.DataFrame:
    """Row-wise z-score. Rows with <2 valid assets or zero dispersion → NaN."""
    mu = scores.mean(axis=1)
    sd = scores.std(axis=1)
    z = scores.sub(mu, axis=0).div(sd.where(sd > 0), axis=0)
    return z


def combine(
    factor_scores: dict[str, pd.DataFrame], weights: dict[str, float]
) -> pd.DataFrame:
    """Weighted sum of cross-sectionally z-scored factors.

    Assets missing any factor with nonzero weight are excluded for that day
    (intersection rule — treating a missing factor as "neutral" let
    incomplete names sneak into the top of the book; see docs/01, #6).
    """
    zs = []
    for name, w in weights.items():
        if w == 0:
            continue
        zs.append(cross_sectional_z(factor_scores[name]) * w)
    if not zs:
        raise ValueError("all factor weights are zero")
    combined = zs[0]
    for z in zs[1:]:
        combined = combined.add(z, fill_value=np.nan)
    return combined.dropna(how="all")


def backtest(
    prices: pd.DataFrame,
    factor_scores: dict[str, pd.DataFrame],
    weights: dict[str, float],
    top_k: int = 3,
    bottom_k: int = 3,
    rebalance_every: int = 5,
    fee_bps: float = 10.0,
) -> pd.Series:
    """Simulate and return daily portfolio returns (net of fees).

    Positions for day t are chosen from scores at close of day t-1 and
    earn the close-to-close return of day t. Gross exposure is 1.0
    (0.5 long + 0.5 short).
    """
    rets = prices.pct_change()
    score = combine(factor_scores, weights).reindex_like(rets)

    dates = rets.index
    positions = pd.DataFrame(0.0, index=dates, columns=rets.columns)
    current = pd.Series(0.0, index=rets.columns)

    last_rebal = None
    for i in range(1, len(dates)):
        sig_day = i - 1
        if last_rebal is None or sig_day - last_rebal >= rebalance_every:
            s = score.iloc[sig_day].dropna()
            if len(s) >= top_k + bottom_k:
                new = pd.Series(0.0, index=rets.columns)
                new[s.nlargest(top_k).index] = 0.5 / top_k
                new[s.nsmallest(bottom_k).index] = -0.5 / bottom_k
                current = new
                last_rebal = sig_day
        positions.iloc[i] = current

    gross = (positions * rets.fillna(0.0)).sum(axis=1)

    turnover = positions.diff().abs().sum(axis=1)
    fee = turnover * (fee_bps / 1e4)
    fee.iloc[0] = positions.iloc[0].abs().sum() * (fee_bps / 1e4)

    return gross - fee

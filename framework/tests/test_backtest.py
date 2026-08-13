import numpy as np
import pandas as pd
import pytest

from quantgate.backtest import backtest, combine, cross_sectional_z


def _panel(days=60, seed=3):
    """Five synthetic assets with distinct drifts, so ranks are knowable."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=days, freq="D", tz="UTC")
    drift = np.linspace(-0.001, 0.001, 5)
    rets = rng.normal(drift, 0.005, (days, 5))
    prices = pd.DataFrame(
        100 * np.exp(np.cumsum(rets, axis=0)),
        index=idx,
        columns=[f"A{i}" for i in range(5)],
    )
    return prices


class _ConstantFactor:
    """Score = fixed rank per asset: A4 best, A0 worst, every day."""

    def __init__(self, cols):
        self.scores = pd.Series(np.arange(len(cols), dtype=float), index=cols)

    def compute(self, prices):
        return pd.DataFrame(
            np.tile(self.scores.values, (len(prices), 1)),
            index=prices.index,
            columns=prices.columns,
        )


def test_combine_intersection_rule_drops_assets_missing_a_factor():
    prices = _panel()
    f1 = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
    f2 = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
    f2["A2"] = np.nan  # A2 missing from factor 2
    combined = combine({"f1": f1, "f2": f2}, {"f1": 0.5, "f2": 0.5})
    assert combined["A2"].isna().all()
    assert combined[["A0", "A1"]].notna().all().all()


def test_cross_sectional_z_zero_dispersion_is_nan_not_zero():
    df = pd.DataFrame({"x": [1.0, 1.0], "y": [1.0, 1.0]})
    assert cross_sectional_z(df).isna().all().all()


def test_backtest_holds_known_winners_and_losers():
    prices = _panel()
    scores = {"c": _ConstantFactor(prices.columns).compute(prices)}
    rets = backtest(
        prices, scores, {"c": 1.0}, top_k=1, bottom_k=1, rebalance_every=5
    )
    # long A4, short A0, gross 1.0 — portfolio return ≈ ret(A4)/2 - ret(A0)/2
    implied = 0.5 * prices["A4"].pct_change() - 0.5 * prices["A0"].pct_change()
    # fees make net <= gross on rebalance days; elsewhere they match
    assert (rets <= implied.fillna(0) + 1e-12).all()
    assert (implied.fillna(0) - rets).max() < 0.005  # fees small


def test_backtest_uses_lagged_scores_no_lookahead():
    prices = _panel()
    # factor that flips sign exactly once, mid-sample
    cols = prices.columns
    sig = np.ones((len(prices), len(cols)))
    sig[:30] *= np.arange(len(cols))
    sig[30:] *= np.arange(len(cols))[::-1]
    scores = {"flip": pd.DataFrame(sig, index=prices.index, columns=cols)}
    rets = backtest(prices, scores, {"flip": 1.0}, top_k=1, bottom_k=1,
                    rebalance_every=1)
    # On day 31 the position must reflect the *new* signal from day 30's close.
    # The full flip long A4/short A0 → long A0/short A4 trades turnover 2.0,
    # so net = gross − 2.0 × 10bps.
    day31 = rets.index[31]
    expected = 0.5 * prices["A0"].pct_change() - 0.5 * prices["A4"].pct_change()
    assert rets.loc[day31] == pytest.approx(expected.loc[day31] - 0.002, abs=1e-9)


def test_zero_weight_factors_are_ignored():
    prices = _panel()
    f = _ConstantFactor(prices.columns)
    with pytest.raises(ValueError):
        backtest(prices, {"c": f.compute(prices)}, {"c": 0.0})

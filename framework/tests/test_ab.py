import numpy as np
import pandas as pd

from quantgate.ab import run_ab


class _TrendFactor:
    """Score = trailing N-day return (so we can build a knowable edge)."""

    def __init__(self, n):
        self.n = n

    def compute(self, prices):
        return prices / prices.shift(self.n) - 1.0


def _persistent_momentum_panel(days=900, seed=11):
    """Cross-sectional momentum is real here by construction: each asset's
    daily mean return is constant, so past winners keep winning."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=days, freq="D", tz="UTC")
    drift = np.linspace(-0.0008, 0.0008, 8)
    rets = rng.normal(drift, 0.004, (days, 8))
    prices = pd.DataFrame(
        100 * np.exp(np.cumsum(rets, axis=0)),
        index=idx,
        columns=[f"A{i}" for i in range(8)],
    )
    return prices


def test_genuinely_better_candidate_passes():
    """In this synthetic world each asset's drift is constant, so a factor
    equal to the true drift ranking is real edge, not luck. Adding it must
    PASS — a gate that blocks genuine improvement is as broken as one that
    waves noise through."""
    prices = _persistent_momentum_panel()
    mom = _TrendFactor(20).compute(prices)
    drift_rank = np.linspace(-1.0, 1.0, prices.shape[1])  # matches construction
    true = pd.DataFrame(
        np.tile(drift_rank, (len(prices), 1)),
        index=prices.index, columns=prices.columns,
    )
    scores = {"mom": mom, "true": true}
    v = run_ab(
        prices, scores,
        {"mom": 1.0},
        {"mom": 0.3, "true": 0.7},
        oos_start="2024-01-01",
    )
    assert v.passed, v.render()


def test_identical_candidate_fails_no_improvement():
    prices = _persistent_momentum_panel()
    scores = {"mom": _TrendFactor(20).compute(prices)}
    v = run_ab(prices, scores, {"mom": 1.0}, {"mom": 1.0}, oos_start="2024-01-01")
    assert not v.passed  # ΔSharpe = 0 < 0.15 → gate holds


def test_inverted_signal_fails():
    """Candidate = the committed factor with flipped sign: deterministically
    harmful in a world where momentum works. The gate must hold."""
    prices = _persistent_momentum_panel()
    scores = {"mom": _TrendFactor(20).compute(prices)}
    v = run_ab(
        prices, scores,
        {"mom": 1.0},
        {"mom": -1.0},
        oos_start="2024-01-01",
    )
    assert not v.passed
    assert v.oos_sharpe_a > v.oos_sharpe_b


def test_verdict_renders_all_four_checks():
    prices = _persistent_momentum_panel()
    scores = {"mom": _TrendFactor(20).compute(prices)}
    v = run_ab(prices, scores, {"mom": 1.0}, {"mom": 1.0}, oos_start="2024-01-01")
    text = v.render()
    assert text.count("PASS") + text.count("FAIL") >= 4
    assert "VERDICT" in text

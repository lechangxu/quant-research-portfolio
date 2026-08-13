import numpy as np
import pandas as pd
import pytest

from quantgate.metrics import max_drawdown, sharpe, yearly_sharpe


def _daily(returns, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(returns), freq="D", tz="UTC")
    return pd.Series(returns, index=idx)


def test_sharpe_of_constant_positive_return_is_infinite_scale_free():
    # constant nonzero return → zero std → NaN by definition (no free lunch flag)
    assert np.isnan(sharpe(_daily([0.001] * 30)))


def test_sharpe_sign_follows_mean():
    rng = np.random.default_rng(7)
    up = _daily(rng.normal(0.002, 0.01, 365))
    down = _daily(rng.normal(-0.002, 0.01, 365))
    assert sharpe(up) > 0
    assert sharpe(down) < 0


def test_max_drawdown_known_path():
    # +10% then -20%: curve 1.0 → 1.10 → 0.88; dd = 0.88/1.10 - 1 = -0.2
    r = _daily([0.0, 0.10, -0.20])
    assert max_drawdown(r) == pytest.approx(-0.20, abs=1e-9)


def test_max_drawdown_empty_is_nan():
    assert np.isnan(max_drawdown(pd.Series(dtype=float)))


def test_yearly_sharpe_splits_by_calendar_year():
    r = _daily(np.random.default_rng(1).normal(0.001, 0.01, 800))
    ys = yearly_sharpe(r)
    assert set(ys.index) == {2024, 2025, 2026}
    assert ys.notna().all()

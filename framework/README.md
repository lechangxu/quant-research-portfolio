# framework/ — quantgate

A minimal, runnable implementation of the A/B acceptance gate from
[docs/02](../docs/02-factor-ab-protocol.md). ~400 lines, one job: answer
"does this candidate factor earn weight in the committed book?" with a
PASS/FAIL backed by four hard out-of-sample thresholds.

This is the **discipline layer, not a strategy**. It ships no alpha: two
toy factors (momentum, low-vol) exist only to demonstrate the gate.

## Install & run

```bash
cd framework
pip install -e ".[dev]"
pytest                        # 13 tests: metrics, backtester, gate logic
python examples/run_ab_demo.py  # real Binance public data, no API key
```

The demo downloads daily closes for ten liquid USDT pairs (cached after
first run), then tests whether adding a low-volatility tilt to a momentum
book survives the gate, with IS = 2022–2024 and OOS = 2025→present.

Actual output at last run (2026-08-13; re-run to refresh — numbers move as
the OOS window grows):

```
data: 1685 days × 10 symbols (2022-01-01 → 2026-08-12)

IS   Sharpe  A +0.964 → B +1.084
OOS  Sharpe  A +0.075 → B +0.821

check                                      value  threshold   result
OOS ΔSharpe                                0.745  >= +0.15    PASS
OOS MaxDD deterioration                   -0.052  <= 0.03     PASS
OOS ΔSharpe @ 2x fees                      0.511  >= +0.10    PASS
OOS yearly improvement share               1.000  >= 0.67     PASS

VERDICT: PASS
```

Worth reading the numbers the way the gate reads them: the candidate did
not just pass, it passed *because the committed book was flat OOS* — the
gate's job is not to flatter incumbents. On other candidates it says no,
and keeps the receipt (see docs/03-negative-results-log.md).

## Layout

| file | role |
|---|---|
| `quantgate/data.py` | `DataAdapter` seam + keyless Binance adapter (CSV cache; drops the unfinished current bar — see docs/01 #2) |
| `quantgate/factors.py` | `Factor` interface + two example factors |
| `quantgate/backtest.py` | equal-weight top-K/bottom-K, 5-day rebalance, fees on turnover, one-day execution lag (no lookahead) |
| `quantgate/metrics.py` | Sharpe / MaxDD / per-year Sharpe (365-day annualization) |
| `quantgate/ab.py` | the four thresholds as constants + `run_ab()` → PASS/FAIL |
| `tests/` | metrics, no-lookahead and fee logic of the backtester, gate verdict logic |

## Deliberate simplifications

- Fees on rebalanced turnover only; no slippage, borrow, or funding model.
  The 2×-fee window is the designated shock absorber for everything this
  list omits.
- Daily closes only; no intraday risk layer.
- The gate's thresholds are the point of the exhibit, and they are
  constants in `ab.py` — changing them without changing
  `docs/02-factor-ab-protocol.md` is the failure mode this protocol exists
  to prevent.

## Extending

Other venues/asset classes implement `DataAdapter.daily_closes()` and plug
in without touching the gate. New factors implement `Factor.compute()` with
the no-future-data contract documented in `factors.py`.

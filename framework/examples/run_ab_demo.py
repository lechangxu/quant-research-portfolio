"""End-to-end demo of the A/B gate on real public data.

Downloads daily closes for ten liquid USDT pairs from Binance's public API
(no key), then asks the only question the gate cares about:

    committed book  = 100% 20-day momentum
    candidate       = 70% momentum + 30% low-volatility

    Does the candidate earn weight? Four OOS thresholds decide, not opinion.

Run:
    python examples/run_ab_demo.py

The demo is designed so the *process* is the exhibit, not the outcome:
if the candidate FAILs, the gate is doing its job (see
docs/03-negative-results-log.md — low-vol factors have died here before).
"""

from quantgate.ab import run_ab
from quantgate.data import BinanceAdapter
from quantgate.factors import LowVolFactor, MomentumFactor

SYMBOLS = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", "LINK", "DOT"]
START = "2022-01-01"
OOS_START = "2025-01-01"  # IS = 2022–2024, OOS = 2025→now

prices = BinanceAdapter().daily_closes(SYMBOLS, START)
print(f"data: {len(prices)} days × {prices.shape[1]} symbols "
      f"({prices.index[0].date()} → {prices.index[-1].date()})\n")

factors = {"mom": MomentumFactor(20), "lowvol": LowVolFactor(20)}
scores = {name: f.compute(prices) for name, f in factors.items()}

verdict = run_ab(
    prices,
    scores,
    weights_a={"mom": 1.0},                  # committed
    weights_b={"mom": 0.7, "lowvol": 0.3},   # the one variable that changed
    oos_start=OOS_START,
    fee_bps=10.0,
    top_k=3,
    bottom_k=3,
    rebalance_every=5,
)
print(verdict.render())

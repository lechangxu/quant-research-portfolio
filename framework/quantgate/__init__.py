"""quantgate — a minimal, honest factor A/B acceptance gate.

Implements the portfolio-level OOS A/B protocol described in
../docs/02-factor-ab-protocol.md:

    Any new factor passes four hard out-of-sample thresholds at the
    portfolio level before it earns weight. No exceptions.

This package is deliberately small. It is the *discipline* layer, not a
strategy — you bring your own factors and see whether they survive.
"""

__version__ = "0.1.0"

# Factor A/B Acceptance Protocol

**The rule:** *Any new factor, weight change, or direction change passes a portfolio-level out-of-sample A/B before anyone discusses wiring it into live trading. No exceptions.*

Cheap tests (factor-level IC research) can run freely. Expensive commitments (execution wiring, risk integration, monitoring, observation periods) do not begin until the cheap gate has been passed.

## Why this protocol exists

**Factor-level strength does not imply portfolio-level usefulness.** Both directions of the failure have been paid for:

- A low-volatility factor with strong standalone IC failed the portfolio A/B — the third orthogonal-factor candidate in a row to die at this gate.
- A supply-growth factor with positive cross-sectional IC both in-sample (+0.029) and out-of-sample (+0.044) moved portfolio Sharpe from −1.48 to −1.35 with no year-over-year consistency — noise, rejected, weight stays 0.
- Reverse tuition: an earlier system's regime parameters drifted between live and backtest (OOS Sharpe 1.82 → 1.08) because "obviously fine, ship it" skipped the check. A funding-rate factor carried 43% dead weight for a full week unnoticed for the same reason.

"This one is obviously fine" is exactly why the protocol exists.

## The gate

A/B at the **portfolio** level, one command:

```bash
python3 t_ab.py --candidate '{"new_factor": 0.15, ...}'
```

- **Arm A** = currently committed weights. **Arm B** = identical except the candidate change. One variable.
- **Four windows:** FULL / IS / OOS / OOS at 2× fees.

**Four hard thresholds** (constants at the top of the script; changing a threshold requires changing this document in the same commit):

| Check | Threshold |
|---|---|
| OOS ΔSharpe | ≥ +0.15 |
| OOS MaxDD deterioration | ≤ 3pp |
| OOS ΔSharpe at 2× fees | ≥ +0.10 — the edge must survive costs doubling |
| OOS year-by-year improvement | ≥ 2/3 of years |

All four pass → PASS, and only then does live-integration discussion start. Any one fails → FAIL, weight stays 0.

**"Improved IS, didn't improve OOS" is printed by the script as what it is: an in-sample hallucination.**

## What happens to FAILed factors

The code may stay in the repo — with weight 0 — and the rejection is written into the persistent research log with its numbers. This is deliberate: without a written graveyard, the same factor gets rediscovered and re-proposed six months later. (See [03 — Negative Results Log](03-negative-results-log.md).)

## Scope

- Applies to the fixed-weight multi-factor book and, with the same windows and thresholds, to wide-universe variants — the comparison method is identical.
- Factor-level research (IC, ICIR, regime-conditional IC matrices, correlation to incumbent factors) is unchanged and encouraged: it is cheap, and it decides what is *worth* an A/B. It just doesn't decide what ships.
- **No exception clause.** The protocol's entire value is that "just this once" is not available.

## Design notes

- **Portfolio level, not factor level.** A factor can have excellent IC and still add nothing once correlated with incumbents, sized by vol-targeting, and charged fees. The only question that matters is what the committed book gains.
- **2× fees as a robustness axis, not a forecast.** An edge that dies when costs double is an edge that dies on the next fee-tier change, the next liquidity regime, or the next venue migration. The threshold is lower at 2× (+0.10, not +0.15) — we ask for survival, not improvement.
- **Year-by-year consistency** blocks a single lucky year from carrying the verdict. Two-thirds of OOS years must improve.
- **Thresholds are versioned with the document.** Discipline that can be silently relaxed after a disappointing result is not discipline.

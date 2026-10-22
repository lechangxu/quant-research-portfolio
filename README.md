# Quant Research Portfolio

[![tests](https://github.com/lechangxu/quant-research-portfolio/actions/workflows/tests.yml/badge.svg)](https://github.com/lechangxu/quant-research-portfolio/actions/workflows/tests.yml)
[English](README.md) | [简体中文](README.zh-CN.md)

**Production-grade systematic trading methodology — the parts that survive contact with live money.**

This repository publishes the *research process* behind quantitative trading systems I have run in production (crypto perpetual futures and China A-shares): how live-vs-backtest divergence is audited, how new factors are gated before they can touch capital, and what the graveyard of rejected ideas looks like.

> **What this is:** evidence of engineering and research rigor.
> **What this is not:** strategy code, factor recipes, parameters, weights, or anything that reproduces a live portfolio. Those stay private.

---

## Why publish methodology instead of code?

Open-source backtesting frameworks are abundant and excellent — [vectorbt](https://github.com/polakowo/vectorbt), [QLib](https://github.com/microsoft/qlib), [freqtrade](https://github.com/freqtrade/freqtrade), [Lean](https://github.com/QuantConnect/Lean). They give you an engine. What they cannot give you is what happens when the engine meets production:

- The live equity curve goes flat while the backtest OOS says the strategy should be making money. **Why?**
- A new factor shows a beautiful in-sample IC. **Does it survive an out-of-sample A/B at the portfolio level, at 2× fees?**
- A risk layer that looks conservative on paper turns out to be an absorbing state that permanently locks 87% of your positions. **Would your framework's test suite catch that?**

These documents are my answers, written at the time the work was done, against live systems.

## Stack

| Layer | What it is |
|---|---|
| Language | Python 3.10+ (`requires-python` in `framework/pyproject.toml`) |
| Package | `quantgate` — `pip install -e "framework[dev]"` |
| Runtime dependencies | pandas >= 2.0, numpy >= 1.24, requests >= 2.28 |
| Dev dependencies | pytest >= 7.0 |
| Tests | pytest — 14 tests in `framework/tests` |
| CI | GitHub Actions, Python 3.12 |

## Contents

| Doc | Topic |
|---|---|
| [01 — Live-vs-Backtest Divergence Audit](docs/01-live-vs-backtest-divergence-audit.md) | Nine divergences between a production crypto-perp system and its backtest, ranked by severity. Includes: an absorbing-state trailing stop (86.8% of rolling-origin backtest paths permanently locked, median survival 59 days), a tail-dependency screen (remove the best 1.4% of in-sample days and returns go to zero), and a dimension-mismatch root cause that unit tests never caught. |
| [02 — Factor A/B Acceptance Protocol](docs/02-factor-ab-protocol.md) | The four hard thresholds any new factor must pass at the *portfolio* level before it earns weight. One command, PASS/FAIL, no exceptions. In-sample improvement that does not survive OOS is classified as what it is: an in-sample hallucination. |
| [03 — Negative Results Log](docs/03-negative-results-log.md) | Factors and design changes that were *rejected* — with the numbers that killed them. Published because a research process that only shows winners is marketing, not research. |
| [`framework/` — quantgate](framework/README.md) | The A/B gate as ~400 lines of tested, runnable Python: keyless Binance data adapter, no-lookahead backtester, the four thresholds as constants, `run_ab()` → PASS/FAIL. Docs prove the thinking; this proves the delivery. `pip install -e ".[dev]" && pytest && python examples/run_ab_demo.py` |

## Methodology highlights

- **Rolling-origin survival analysis** to detect absorbing states in risk overlays (a state your position enters and never leaves is indistinguishable from a bug, even when it was "designed").
- **Perturbation testing** for partial-bar / data-timing fidelity — measuring how much of the live signal turnover is noise vs. real edge, and where rank-overlap (Jaccard) metrics miscalibrate.
- **Tail-dependency screening**: strip the best *k* days and see whether anything is left. If not, you have a lottery ticket, not a strategy.
- **Isolation-matrix divergence audits**: change one component at a time between backtest and live config, measure the ΔSharpe of each, rank, fix in severity order.
- **Portfolio-level OOS A/B gating** for every candidate factor, at realistic and 2× fees, with year-by-year consistency requirements.

## Positioning vs. the giants

I build *on* the open-source ecosystem rather than re-implementing it. The comparative claims I make are explicit and benchmarked:

- **vs. vectorbt / backtrader**: these give you event simulation; the docs here cover what they don't — divergence auditing between your research config and your production execution layer.
- **vs. QLib**: QLib gives you an ML pipeline and factor zoo; doc 02 is the governance layer that decides whether any factor (ML-discovered or hand-built) is allowed to touch capital.
- **vs. freqtrade / Lean**: they give you live plumbing; doc 01 is what to do when the plumbing and the research disagree.

Nothing here is copied from those projects; where their ideas are used, they are credited. The divergence-audit and A/B-gating write-ups are original work from my own production systems.

## Disclaimer

All figures in these documents are **research artifacts**, published for methodology demonstration only. They are **not investment advice**, not a solicitation, and not a representation of any product's expected performance. Past performance — live or simulated — does not guarantee future results. Absolute return figures and identifying strategy details have been deliberately removed; risk-adjusted statistics are retained because they are the methodological evidence.

## Contact

Open to quantitative research, backtesting-infrastructure, and trading-system reliability work. GitHub issues on this repo are the best way to reach me.

# Negative Results Log

A research process that only publishes winners is marketing. This is the graveyard: candidates that looked good at the factor level and were **rejected** at the portfolio gate, with the numbers that killed them. Each entry exists so the idea is never re-litigated from scratch six months later.

Related: [02 — Factor A/B Acceptance Protocol](02-factor-ab-protocol.md) (the gate), [01 — Live-vs-Backtest Divergence Audit](01-live-vs-backtest-divergence-audit.md) (risk-layer failures).

---

## Rejected factors

### Low-volatility factor — REJECTED

- **Factor-level evidence:** strong standalone IC. Looked like the best orthogonal candidate in its batch.
- **Portfolio A/B:** FAIL. The 2026 segment contributed −0.65 Sharpe at the portfolio level.
- **Context:** third consecutive orthogonal-factor candidate to die at the portfolio gate. Three strong-IC factors in a row added nothing once correlated with incumbents, sized, and charged fees.
- **Lesson that stuck:** factor-level IC is a screening tool, not evidence. The portfolio is the unit of account.

### Buy/sell-imbalance as a third signal — REJECTED

- **Proposal:** add a taker buy/sell imbalance factor at 0.20 weight alongside momentum and volume-flow.
- **Isolation result:** ΔIS **−0.646** Sharpe, ΔOOS **+0.044**.
- **Verdict:** the only large effect was in-sample damage; the OOS effect was noise. Weight set to 0.00 and left there.
- **Note:** the same candidate later passed through the divergence audit's isolation matrix (doc 01, #1) and reproduced the identical conclusion — independent confirmation.

### Supply-growth factor — REJECTED (2026-08-11)

- **Factor-level evidence:** positive cross-sectional IC both IS (+0.029) *and* OOS (+0.044) — the strongest factor-level case of any candidate here.
- **Portfolio A/B:** baseline Sharpe −1.48 → −1.35 with the candidate; improvement inconsistent across years.
- **Verdict:** FAIL — a +0.13 move on a negative-Sharpe book with no year-over-year consistency is noise, not edge. Weight stays 0.
- **Lesson:** positive OOS IC is *necessary*, not sufficient. This is the cleanest illustration of why the gate lives at the portfolio level.

### Equal-signed wide-pool weighting — REJECTED

- **Proposal:** widen the book and weight all same-sign signals equally, rather than rank-concentrating.
- **Killer evidence (tail-dependency screen):** remove the best 10 days and +107.8% cumulative becomes **+2.4%**. The entire return lived in a handful of days.
- **Verdict:** rejected on tail shape alone, before finer metrics. This rejection established the tail-dependency screen as a first-class filter (doc 01).

### Drawdown-compression variants, three attempts — ALL REJECTED

- **Proposal (3×):** parameter and overlay variants aimed at compressing the flagship configuration's MaxDD.
- **Result:** three independent A/B rounds, three rejections — every variant paid more Sharpe than it bought drawdown.
- **Standing decision recorded:** *stop trying to compress this configuration's MaxDD.* The drawdown is a property of the strategy's return distribution, not a parameter away from gone. Future effort goes to other axes.

## Rejected risk designs

### "Maximally defensive" overlay floor — REMOVED

- Setting the exposure-control floor to 0.0 (full de-risk in stress) produced the **worst** OOS Sharpe in the comparison table (1.033 vs 1.82–2.17 for saner floors) by deadlocking the book at floor for ~35% of the OOS window.
- Conservative-looking knobs can be absorbing states. Full analysis: doc 01, #3 and #4.

### Trailing-stop account layer, as originally wired — REJECTED AND REBUILT

- A 15% trailing stop against a strategy whose ordinary OOS MaxDD is −47.7% fired on schedule, not on risk events, and — due to frozen cash + non-decaying HWM — became an absorbing state that permanently locked **86.8%** of OOS rolling origins (median survival 59 days).
- Rebuilt with trigger-time rebasing; post-fix the layer is *neutral*, not protective, and that is recorded honestly. Full analysis: doc 01, #4.

## Process failures (kept as tuition records)

- **Dual-written parameters drifted** between live and backtest copies of the same regime config: OOS Sharpe 1.82 → 1.08. Fix: single source of truth, live imports the research engine instead of re-implementing it.
- **A funding-rate factor carried 43% dead weight for a week** unnoticed — nobody was checking that live weights matched committed weights. Fix: weight-parity checks in the monitoring path.
- **A "tested" hypothesis that was never run** — an audit document claimed a layer had no test coverage; a grep of the scripts directory found an existing, purpose-built test whose results had simply never been written down. Standing rule: grep for an existing test before writing a new one, and *persist results* — an unrecorded experiment is indistinguishable from an unrun one.

---

*Dates refer to decision records in the private research log. Figures are research artifacts, not performance representations. See the repository [README](../README.md#disclaimer).*

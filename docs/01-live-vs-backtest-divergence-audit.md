# Live-vs-Backtest Divergence Audit

**Context.** A production crypto-perpetual-futures long/short system (multi-factor, regime-scaled, ~70-name universe, 5-day rebalance) showed a stark gap: the backtest's out-of-sample window compounded to a large multiple of capital, while the live account's equity was essentially flat (+0.2%) over the same period.

An earlier version of this system had already been scrapped once because the live implementation silently shipped a *different classifier* than the backtest — two different strategies wearing the same name. So before any parameter tuning, we ran a full read-only audit of the live execution path against the research path.

**Method.** Line-by-line comparison of the live engine vs. the backtest engine across three layers — execution, risk overlay, data handling. (The signal layer had been audited separately and already closed.) Every candidate divergence was then *quantified in isolation*: change exactly one component in the backtest to match live, measure ΔSharpe/ΔMaxDD, rank by severity. Nine divergences found, five initially rated severe.

**Headline result: the three tested "severe" signal-side divergences all turned out to be harmless — and that is itself the finding.** Live and backtest were the *same* strategy at the signal layer (regime-label agreement 98.6%, blended-score rank correlation 0.955, identical total exposure). The flat live equity was not signal distortion. It was an execution-observability failure (#5) plus an absorbing state in the risk layer (#4). This is why you audit before you optimize: the obvious suspect was innocent.

---

## Severity table (final verdicts)

| # | Divergence | Initial rating | Measured verdict |
|---|---|---|---|
| 1 | Live had no regime-switch hysteresis (backtest required 2 consecutive confirmations) | Severe | ✅ Harmless. ΔIS +0.000 / ΔOOS −0.012 Sharpe |
| 2 | Live computed factors on the *unfinished* current bar | Severe | ✅ Inside noise. Perturbation ≈ half the strategy's own natural turnover |
| 3 | Risk-overlay (exposure-control) function form differed: SMA-binary (backtest) vs EMA-continuous (live) | Severe | ✅ Actually *favorable*. Live variant: +0.33 Sharpe, MaxDD 13.6pp better |
| 4 | Entire account-level RiskManager layer absent from backtest | Severe | 🔧 **Real bug, fixed.** Trailing stop was an absorbing state: 86.8% of OOS rolling origins permanently locked, median survival 59 days |
| 5 | Order failures silent (log-and-continue, no retry, no alert) | Severe | ⬜ Engineering fix, requires live-code change + approval |
| 6 | z-score: live took union + fillna(0), backtest took intersection | Medium | ⬜ Untested at time of writing |
| 7 | Vol-target: BTC single-name proxy, 252 vs 365 annualization, applied before position cap | Medium | ⬜ Untested |
| 8 | ATR stop covered longs only — while the OOS window's entire edge came from the short leg | Medium | ⬜ Untested |
| 9 | Momentum window polluted by the unfinished bar (consequence of #2) | Low | ⬜ Subsumed by #2 |

None of the nine is a *parameter* problem. All are structural implementation differences — the same failure class as the earlier version's "live shipped a different classifier."

---

## #1 — Missing regime hysteresis: a controlled experiment that came back empty

The backtest's regime detector required two consecutive identical signals before switching (hysteresis); the live engine switched instantly on the raw signal. Regime determines the three exposure scalars for the whole portfolio, so a systematically different regime sequence = a systematically different strategy. Rated severe on inspection.

Isolation matrix (one variable changed at a time):

| Config | IS Sharpe | OOS Sharpe | ΔIS | ΔOOS |
|---|---:|---:|---:|---:|
| A — backtest baseline (confirm=2) | 1.590 | 1.840 | — | — |
| **C — hysteresis only removed (confirm=1)** | 1.590 | 1.828 | **+0.000** | **−0.012** |

ΔOOS of −0.012 is noise. Post-hoc explanation: the regime boundaries sit far enough apart that the index rarely jitters across a boundary on consecutive days, so "wait for confirmation" and "switch immediately" produce nearly identical regime sequences.

**Lesson: rate divergences by measured impact, not by how scary they look in code review.** This one looked like a strategy-identity break and was worth −0.012 Sharpe.

---

## #2 — The unfinished-bar problem: measuring against the right baseline

Live fetched daily klines without an `endTime`, so the last bar was the *current, still-forming* day. All factors, moving averages, and entry prices were computed on it. The backtest strictly used completed bars. Rebalance ran ~8h before the UTC daily close, so every live rebalance used a bar that was ~2/3 formed.

Not lookahead (no future information leaks in) — but noise, plus a systematic offset vs. the backtest. Two opposing effects, sign unclear a priori:

| | Signal source | Execution price | Signal→exec gap |
|---|---|---|---|
| Backtest | Previous day's close | Next day's **open** | 24h |
| Live | Current partial bar | Same-minute market | ≈0 |

Live's signal-to-execution is 24h *fresher* — favorable; its factors stand on a 2/3-formed bar — unfavorable.

**Test design** (signal layer only, no P&L, does not consume an OOS unsealing): rebuilt the 08:00 UTC partial bar from hourly data (verified 24 hourly bars aggregate to the daily bar field-for-field, volume included). Arm A = backtest convention, arm B = live convention, in-sample year, 72 rebalance days:

| Metric | Value |
|---|---|
| Regime-label agreement | **98.6%** (1 of 72 days differs) |
| Blended-score rank correlation | **0.9553** |
| Total exposure, A/B median | **1.000 / 1.000** |
| Long-book overlap | 5/5 identical on 30.6% of days, 4/5 on 56.9%, 3/5 on 12.5% |

**The control group is the key move.** "1 of 5 names differs" is uninterpretable alone — top-K selection is inherently sensitive to small score perturbations. So measure the strategy's *own* churn between adjacent rebalance days:

```
Natural churn (arm A, adjacent rebalances):  2.0 of 5 names replaced   (Jaccard 0.429)
Partial-bar perturbation (A vs B):           1.0 of 5 names differ     (Jaccard 0.667)
```

The partial bar perturbs the portfolio by **half of what the strategy does to itself on a normal day**. Verdict: inside inherent noise, no live change needed.

**Metric-calibration note.** Our pre-registered pass threshold was "median Jaccard ≥ 0.80". For a 5-element set that is miscalibrated: k/(10−k) = 0.80 → k = 4.44, i.e. it demands near-perfect 5/5 overlap every day — a bar the strategy's own natural churn (Jaccard 0.429) would fail. For small sets, report the overlap-count distribution, not a Jaccard median.

---

## #3 — Same overlay name, two different functions — and live drew the better one

The exposure-control (EC) overlay — scales gross exposure down in drawdown regimes — existed in both engines but as *different functions*:

| | Backtest | Live |
|---|---|---|
| Smoothing | SMA (windowed mean) | EMA (recursive, α=2/(N+1)) |
| Trigger | Binary: equity < fast AND < slow | Three-zone: ≥slow → 1.0, ≤fast → floor, linear between |
| Output | 1.0 or 0.50 | Continuous, floor→1.0 |
| State | Recomputed fresh | Persisted across processes |

Not parameter drift — a different functional form. Measured across floor values (OOS):

| Variant | OOS Sharpe | MaxDD |
|---|---:|---:|
| No EC | 1.769 | −49.4% |
| SMA, floor 0.50 (backtest-verified) | 1.821 | −43.2% |
| **EMA, floor 0.25 (live, as shipped)** | **2.151** | **−29.6%** |
| EMA, floor 0.15 | 2.167 | −26.8% |
| EMA, floor 0.0 | 1.033 | −14.9% ← a deadlock configuration, since removed |

Live sat in a *better* cell than the backtest-verified config: +0.33 Sharpe, 13.6pp less drawdown. The divergence was the backtest being conservative, not live going rogue. Fast/slow sensitivity across 8 combinations: OOS Sharpe 2.05–2.25 — insensitive.

Residual gap (academic, deliberately left unisolated): the SMA-0.50 and EMA-0.25 cells differ in *both* smoothing form and floor value, so the +0.33 is not decomposed. Live already sits in the better cell and the comparison is OOS, so the decomposition would change no decision. Knowing when *not* to run an experiment is part of the discipline.

Also note the floor=0.0 row: a "fully defensive" setting that produced the *worst* Sharpe in the table — a deadlock state where the overlay locked the book at floor for a third of the OOS window. Conservative-looking knobs can be absorbing states in disguise (see #4).

---

## #4 — The risk layer that was an absorbing state (the main event)

The live engine carried an account-level RiskManager that the backtest never simulated:

- **trailing_stop**: drawdown from high-water mark > 15% → halt trading 24h
- **stop_loss**: equity below −15% from reference capital → halt 24h
- **circuit_breaker**: below −20% from *static initial* capital → locked until equity recovers above initial capital
- State persisted to disk.

The backtest's circuit-breaker was a different animal (drawdown → *position scaling*, not a trading halt). So "24h of no trading" and "permanent lock" had never been backtested at all.

### First measurement (wrong), and the correction

Initial simulation treated the trailing stop as "cool down 24h, then resume" — each cooldown expiry let the book catch one baseline day and escape. Conclusion: "only −0.04 Sharpe drag." **This was wrong.**

Reviewing the 100 OOS triggers showed they were not independent: **84% occurred exactly 5 days apart**, in 9 clusters (largest: 48 triggers; longest lockout ≈ 237 days; ~486 of 948 OOS days sealed). A 5-minute-granularity replay of live semantics answered the real question:

```
Within 10 days of a trigger, any opportunity to rebuild a position?  False
```

Mechanism: `close_all()` freezes equity into cash → equity can't rise → the HWM never decays → drawdown vs. HWM stays permanently below −15% → the *next* 5-minute risk check after each cooldown expiry immediately writes a fresh 24h cooldown → the daily rebalance forever hits `trading_allowed == False`.

**The trailing stop was not a cooldown. It was an absorbing state** — same structure as the EC deadlock in #3, but at a much lower threshold (−15% from HWM vs. CB's −20% from static initial capital).

### Rolling-origin survival analysis

A single path can get lucky. So ask the question that matters: *starting from any point in the window, how long until the account is permanently locked?* Origins every 5 days:

| Window | Origins | Eventually locked | Median survival | Fastest | Locked ≤30d |
|---|---:|---:|---:|---:|---:|
| IS (1y) | 73 | 22 (30.1%) | 62d | 34d | 0.0% |
| **OOS (2.6y)** | **190** | **165 (86.8%)** | **59d** | **4d** | 20.0% |

The 25 unlocked OOS origins are right-censored (median remaining window 62d ≈ median survival 59d) — the window ended before they locked, not evidence of safety.

The faithful-semantics simulation (arm D) vs. baseline (arm A):

| Window | Arm | Sharpe | MaxDD | Underwater % | Longest underwater |
|---|---|---:|---:|---:|---:|
| IS | A — no risk layer | 1.144 | −23.3% | 93.4% | 97d |
| | **D — faithful (absorbing)** | **0.113** | −16.8% | 96.7% | 301d |
| OOS | A — no risk layer | 1.612 | −47.7% | 93.5% | 272d |
| | **D — faithful (absorbing)** | **−0.469** | −16.3% | 99.7% | **944d** |

### Why the circuit breaker never fired — and why that's not reassuring

0 CB triggers across 67 IS + 184 OOS rolling origins. Not because the book never reached −20%: the trailing stop at −15%-from-HWM *always* triggered first and froze equity, and for a fresh origin HWM == initial capital, so trailing structurally pre-empts CB. The CB's own absorbing state (frozen cash can never recover above *static* initial capital, so its auto-reset condition was unreachable) remained a live landmine — just one that trailing always stepped in front of.

### Root cause: a dimension mismatch, not a bad parameter

The strategy's baseline OOS MaxDD is **−47.7%**, underwater 93.5% of days. The trailing threshold was **15%**. A stop threshold *smaller than the strategy's ordinary drawdown* does not fire on risk events — it fires on schedule. No threshold tuning fixes that; the layer was answering a question on the wrong scale.

The live account survived only because it had never yet drawn down 15% (worst live DD at the time: −3.4%). Two near-triggers were *phantom* reads — an equity-fetch timeout returning 0 — whose cooldowns simply expired. **No safety margin; it just hadn't been its turn yet.**

### The fix, verified against pre-registered criteria

On any of the three triggers, rebase both `equity_hwm` and a new `reference_capital` to current equity, and persist. The CB reset denominator moves from static initial capital to `reference_capital` (otherwise unreachable).

The verification script extracted and executed the *actual* RiskManager source from the live file (not a copy), with all three pass criteria written down before any output was seen:

1. After a real −16% drawdown, trading resumes at the rebalance 40 hours (1.7d) later — pre-fix: no re-entry within 10 days
2. After a CB trigger, reset is reachable even if equity never recovers
3. Regression: normal volatility (−3.6%) produces an all-`ok` state sequence; no spurious rebasing

Post-fix semantics (arm E), OOS: Sharpe 1.568 vs. baseline 1.612; triggers down from 100 → 11.

**And the honest footnote:** after the fix, this layer also no longer *protects* anything — post-fix OOS MaxDD −49.5% is slightly worse than baseline −47.7%. With a 15% threshold against a −47.7% strategy, the rebased layer simply walks down with the drawdown: it neither stops it nor locks the account. It is now neutral, not effective. That is recorded here because a fix report that omits it would be marketing.

---

## #5 — Silent order failures (observability)

The live order path caught `Exception`, logged, and returned — no raise, no retry, no alert. The caller received no failure signal; the rebalance continued as if it had executed. This is how "2 order calls, both ERROR, zero fills" persisted invisibly — and it is the actual proximate cause of the flat live equity that motivated the audit, together with the EC deadlock period during which no book was ever built.

The backtest fills every order by construction. **Any live-vs-backtest gap analysis that doesn't start with "did orders actually execute?" is answering a harder question before the easy one.**

---

## The tail-dependency screen (a first-class filter)

Alongside the divergence work we run a screen on every strategy: delete the best *k* days and see what remains.

**Removing the best 5 of 364 in-sample days (1.4% of days) reduced cumulative return to zero. Removing the best 20 of 947 OOS days (2.1%) turned it negative.**

This is the same shape that killed an earlier design ("remove best 10 days → +107.8% becomes +2.4%"). A strategy whose entire return lives in 1–2% of its days is a lottery ticket with a Sharpe ratio, not an edge. The screen is now a standard gate alongside Sharpe/MaxDD — it is cheap, parameter-free, and very hard to sweet-talk.

---

## Process lessons

1. **Audit before optimizing.** Three of five "severe" candidates dissolved under measurement. The gap's real causes were an observability hole and an absorbing state — neither visible in signal-layer metrics.
2. **Isolation matrices beat code review.** One variable at a time, Δ against a fixed baseline, and *state the baseline's convention* (two of our scripts used different short-side conventions — comparing Δ across them is fine, comparing absolute values is not).
3. **Pre-register pass criteria.** The Jaccard ≥ 0.80 threshold was written before the experiment and was wrong for a 5-name book; because it was pre-registered, the miscalibration was caught and reported rather than silently re-thresholded after seeing results.
4. **Rolling-origin survival analysis for stateful overlays.** Any rule with persistent state (halts, locks, cooldowns, HWMs) can be an absorbing state. Single-path backtests cannot see it; "start anywhere, measure time-to-lock" can. Beware right-censoring.
5. **Check the dimension of your thresholds.** A 15% stop on a −47.7% MaxDD strategy is not conservative; it is certain to fire. Compare every risk threshold to the strategy's own drawdown distribution before calling it protection.
6. **Publish the footnotes.** "Fixed the bug, and the fixed layer protects nothing" belongs in the report, not in a commit message nobody reads.

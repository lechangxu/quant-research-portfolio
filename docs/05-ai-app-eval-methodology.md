# 05 — Evaluating AI Applications: A Methodology Grown from a Production Judge Chain

**The claim.** The scarcest skill in last-mile AI delivery is not prompting, not RAG tuning — it is *evaluation engineering*: building the system that decides whether an AI output is good enough to ship, and keeping that system honest as both the model and the application drift. Most teams have a demo; very few have a verdict pipeline.

**My evidence base.** For two months I have run a production evaluation harness that gates AI-generated code changes: a three-judge chain (J1/J2/J3) with independence constraints, a golden set for calibration, an escape log, and metrics written back into the criteria. It lives in the *code* domain. This document is the generalization: what the incidents taught me, restated as a methodology that applies to any AI application — and what I would do in the first two weeks of a client engagement.

Everything below is anchored to a real failure. ([中文版](05-ai-app-eval-methodology.zh-CN.md))

## 1. The three-layer verifier stack

One lesson dominates all others: **no single verifier can cover the whole failure space.** The stack that works:

| Layer | Decides | Example from my harness |
|---|---|---|
| **Deterministic checks** | Exact conditions — machine-checkable, zero judgment | Machine criteria (L0): file exists, command output matches, schema reconciles |
| **LLM judges** | Stable semantic criteria — judgment that is consistent across runs | Independent review (L2): does the diff actually implement the card |
| **Human review** | Ambiguous or high-consequence decisions | Final gate (L3) with authority to reject anything |

The routing rule: **use the cheapest layer that can actually decide the question, and never let a layer judge what it cannot verify.** An LLM judge asked to verify "the cron job is installed on the server" is decoration — it cannot see the server. A deterministic script asked to judge "is this summary faithful" is noise.

## 2. Criteria must be verifiable — the mutation test

Every criterion must answer four questions, the last of which carries the weight:

1. What does it assert, and what do I actually care about — where is the gap?
2. When the asserted thing is false, does it *fail loudly* or silently pass?
3. When the criterion itself rots (the world changed, the checklist didn't), does anyone find out?
4. **If I deliberately break the thing being checked, does the criterion go red — have I actually tried?**

This is mutation testing applied to evaluation. A criterion that has never been shown to turn red is not a gate; it is a hope. In my harness, gate changes ship with a verification record: the broken case, the expected red, the observed red.

## 3. Case study: the day a degraded judge let two real defects through

The incident that taught me the most about LLM judges (2026-10-21, full record in my notes):

A task card's final review was run on a **degraded judge tier** (the primary model channel was down; the system fell back). The degraded judge returned PASS. Two real defects sailed through:

1. `check_results` compared a stats tuple with `== (2, 0, 0)` — but in Python `2.0 == 2` and `False == 0` are both true, so float/boolean counts could impersonate a green result.
2. A missing report file was reported as "unreadable file" — masking an eval *crash* as a file problem.

Both were caught only when the primary channel recovered and the review was **re-run on the real tier**. The fix added criterion #16: two discriminating negative cases that *must* go red, and a crash-vs-unreadable separation.

Three generalizable lessons:

- **A pass from a degraded verifier is "proceed, don't stop" — never a basis for closing.** Any evaluation produced under degradation must carry its issuer's label. Quality may degrade; honesty may not.
- **Exit codes are not evidence.** (The same incident: the eval runner's failure exit code was 100 — identical to a worker crash. We now parse the result payload, never the exit code.)
- **Escapes are the only criterion source that matters.** Every escaped defect becomes a new golden case *and* a new criterion. The suite is grown from failures, not designed in advance.

## 4. Judge independence and replay

LLM judges fail in a specific way: they share blind spots with the model that produced the work. Mitigations, all battle-tested:

- **Different model family.** The judge must not be the producer's sibling. When my execution tier and a judge tier temporarily converged on the same model family, the collision was caught by an independence probe and the chain was re-routed.
- **Blind to rationale.** The judge sees the artifact (the diff), not the producer's self-explanation. Self-reports are evidence of nothing (this is the same principle as doc 04's reconciliation gate, applied to judgment).
- **Replay for attribution.** When a verdict looks wrong, re-run it with instrumentation. A "ceiling" that looked like a judge quality limit turned out to be a logging artifact — only replay told the difference.

## 5. The metrics that keep an eval system honest

- **Escape rate** — defects found *after* a pass. The only north-star metric; everything else is a proxy.
- **Rework rounds per task** — rising trend = criteria unclear or judge miscalibrated.
- **False-completion rate** — "succeeded" runs where the downstream artifact does not exist or is stale.
- **Judge agreement / override rate** — how often the human gate overrides the chain. Too high: judges are noise. Too low: the human gate is rubber-stamping.

Beware Goodhart: the day a metric becomes a target, the harness starts optimizing for it. Metrics inform; gates decide.

## 6. What this looks like in a client engagement (first two weeks)

1. **Competency questions first.** Before any rubric: list the 10–20 questions the application must answer correctly for the business to accept it. These become the seed golden set — drawn from *real past failures* wherever possible.
2. **Stand up the three-layer stack at minimum scale.** Deterministic checks for the exact conditions; one calibrated LLM judge on a different model family than the producer; a human gate for the high-stakes slice.
3. **Wire the escape loop from day one.** Every production miss → new golden case + new criterion. Review the escape log weekly; the suite compounds.
4. **Label every verdict with its issuer.** Degraded evaluations are marked as such, and closes require full-tier verdicts.
5. **Mutation-test the top five criteria.** Deliberately break the output in the way each criterion claims to catch. No red, no gate.

## 7. Vocabulary mapping

| Standard term | My corresponding practice |
|---|---|
| Golden set / eval dataset | 34-case golden set, grown from escapes |
| LLM-as-judge | Three-judge chain, different model families, calibrated quarterly |
| Eval harness | The card → L0–L3 gate pipeline with metrics write-back |
| Mutation testing (for evals) | The four questions + verification record per gate |
| Online regression / drift watch | Freshness watchdog + daily route-health probes |
| Human-in-the-loop review | Risk-driven final gate, not per-step approval |

## Boundary

The evidence base above is from the code domain, where ground truth is relatively cheap (tests run, schemas reconcile). The methodology transfers; the *calibration cost* in open-ended domains (summaries, agent dialogs, research reports) is higher, and I say so in interviews rather than overselling. The offer stands: the first artifact I build in any engagement is the escape log — because the eval system that will keep the application honest is grown from its own failures, starting with the first one.

---

*Docs prove the thinking; the incidents prove it's not theory. Related: [04 — Domain Ontology](04-domain-ontology-operations-layer.md) (the reconciliation gate), `framework/` (the A/B gate as runnable code).*

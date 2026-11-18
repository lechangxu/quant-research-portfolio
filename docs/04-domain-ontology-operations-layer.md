# 04 — Domain Ontology as an Operations Layer: Registry + Manifest

**Incident first.** On 2026-09-06 I discovered that two factor tables (`alpha158_factors`, `extended_factors`) had been absent from four independently maintained literal checklists. Updates had silently stopped for 42 days; 92 of 182 cataloged factors no longer existed in the database, while every dashboard stayed green. The root cause was not "missing checks" — it was that the set of things being checked and the set of things that exist were maintained in four separate places, each assuming another was complete.

The fix was not more checks. It was modeling the domain as an **ontology**: one typed registry as the single source of truth, from which every checklist, monitor, catalog, and audit is *derived*. This document describes that model — the same paradigm Palantir calls an Ontology (typed objects / links / actions as an *operations layer*, not an analytics layer), implemented here at SQLite scale.

## Objects (typed)

| Object | Embodiment | Key attributes | Role |
|---|---|---|---|
| DataSource | tushare / akshare / cninfo / eastmoney | reachability, frequency, egress constraints | Raw feeds. Known constraint: these sources block overseas IPs → the mainland server is the *only* compute side |
| RawTable | `daily_data`, fundamentals, announcements, research reports | schema, `max(trade_date)` | Root of every derived artifact |
| FactorTable | `registry.py::FACTOR_TABLES` (8 registered tables) | `columns` (declared or schema-discovered), `max_lag`, `writer`, `category` | **Core object.** A table is a registry entry, not a file |
| Factor | table columns (258 declared + 5 schema-discovered tables) | label, category | Smallest unit for catalog / API / IC reports |
| ICStats | `factor_ic_stats.json` | IC, window, computed-at | Factor validity, computed on the mainland, read-only in HK |
| Manifest | `manifest.json` | `max_trade_date`, `created_at`, `degraded` | **Proof of completion for one sync.** Atomically written; the sole cross-machine trust token |
| IntelReport | `users.db::daily_intel_reports` | date, narrative | User-facing product object, generated on HK |
| Deployment | HK (nginx + FastAPI) / mainland relay | role, systemd unit, crontab | The two-machine topology is itself part of the ontology: mainland = sole computer, HK = pure consumer |

A registry entry is the single place a new factor table is born:

```python
# scripts/factors/registry.py — the single source of truth (excerpt)
FactorTable("price_factors",    tuple(PRICE_FACTOR_COLS), max_lag=2, writer="scripts.factors.cli update", category="technical")
FactorTable("alpha158_factors", tuple(ALPHA158_COLS),     max_lag=2, writer="scripts.factors.cli update", category="technical")
FactorTable("holder_factors",   None,                     max_lag=7, writer="scripts/backfill_holder.py", category="holders")
# columns=None → columns discovered from SQLite schema, still reconciled post-write
```

Register once, and the table is watched, cataloged, IC-computed, and deploy-audited — **nobody has to remember to edit a second list**. That is the difference between an ontology and a pile of config files.

## Links (lineage)

```
sources → RawTables → FactorTables (registry-derived) → ICStats → manifest.json
                                                                   │  (atomic)
                              HK: sync-db.sh validates manifest ──►│──► atomic DB swap → API / reports
mainland pipeline fails ⇒ exit 1 ⇒ no manifest written ⇒ HK stops pulling ⇒ watchdog alerts
freshness watchdog: every FactorTable's MAX(trade_date) vs daily_data, tolerance = max_lag
```

Every hop's "done" is proven by a downstream artifact (manifest, `max(trade_date)`, schema reconciliation) — never by the producing process's own exit code.

## Actions (permissioned operations)

An action is not a function; it is an operation with a pre-gate, completion evidence, and a failure path:

| Action | Gate | Completion evidence (self-report rejected) | Failure path |
|---|---|---|---|
| `daily-update` | flock, single launcher | manifest written atomically | exit 1 → no manifest → HK stops → alert |
| `sync-to-hk` | manifest freshness check | atomic DB swap + `ActiveState=active` asserted | check fails → old snapshot kept, service uninterrupted |
| `register-factor-table` | registry is the only entry point | schema reconciliation (declared vs actual) | reconcile fails → deploy audit red |
| `backfill-*` | must not race daily update | row counts + freshness re-check | exit 0 with 0 rows = **false completion**, caught next day |
| `deploy` | CI SQL gate green | post-deploy `--audit` live-fire | red → roll back to previous snapshot |
| `ic-recompute` | factor tables within `max_lag` | IC file mtime + window reconciliation | stale factors → IC marked `degraded` |

Three design principles:

- **The reconciliation gate (A2): never accept a process's self-reported success.** `systemctl restart` returning 0 ≠ the service is running; a backfill exiting 0 ≠ rows were written.
- **False completion is the primary enemy.** After the ontology refactor, *the watched set ≡ the registered set* — the failure mode "a new table escapes monitoring" ceases to exist structurally.
- **`degraded` is a first-class citizen.** The manifest carries an explicit degraded flag: shipping with known defects is allowed, but the defect must be declared and flow to consumers. Silent is not allowed.

## Governance (how the ontology changes itself)

- The registry is a PR object: changing it = changing the ontology; `test_registry.py` guards its internal consistency.
- Derived-identity is tested: drift checks prevent the code from wandering away from the model.
- Incident log reflows into the model: every ontology failure (the 42-day silent loss, an HK OOM, a disk+GFW double failure) produces a new gate or a new attribute (e.g., the manifest's `degraded` flag). **The ontology is grown, not designed.**

## Translation to Palantir vocabulary

| Palantir / FDE term | Here |
|---|---|
| Ontology | `registry.py` + `manifest.json` + this document |
| Ontology Proposal (branch → review → merge) | git PR + registry tests + CI gate |
| Actions (permissioned) | the action table above: pre-gate + evidence + failure path |
| False-completion defense | reconciliation gate + freshness watchdog |
| Action Log | deploy/sync history as queryable records |
| Durable execution | flock + atomic manifest + atomic snapshot swap (a hand-rolled equivalent; Temporal is the productized version) |

The point of this mapping is not name-dropping. It is that the *pattern* — model the nouns **and** the verbs, close the data model to include its own update paths — is achievable at any scale, and the governance philosophy ("security = preventing erroneous modification of reality, not hiding data") transfers directly.

**What this doc is:** a description of things that exist in production, with the incident that forced them. **What it is not:** strategy IP — no factor formulas, no weights, no signal logic. The full Chinese version with the mermaid lineage diagram is at [04 zh-CN](04-domain-ontology-operations-layer.zh-CN.md); a standalone HTML rendering is [here](quantmind-ontology.html).

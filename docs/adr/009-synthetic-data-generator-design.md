---
status: accepted
date: 2026-11-13
decision-makers: Sylwia Berent
consulted: Claude Code (AI assistant; proposed options and trade-offs)
---

# ADR-009: Synthetic data generator as a uv workspace package with deterministic, append-only output

## Context and Problem Statement

Phase 1 needs a Python generator for two years of OTT subscription data (customers with PII, subscriptions, payments, viewing, marketing) with realistic patterns and deliberate data-quality defects. It must run as a full backfill and as daily incremental batches, deterministically from a seed, and write Parquet files for the Snowflake stage in Phase 2. ADR-001 deferred the Python project layout and Dependabot to this phase.

## Decision Drivers

- Daily batches must contain exactly the rows a fresh backfill would contain, so the load path can be tested end to end.
- Reruns must be reproducible for tests, debugging, and idempotent Airflow tasks (Phase 4).
- Few, well-known dependencies; fast enough for a full backfill on a laptop.
- Later components (MCP server, deployment scripts) need their own dependencies without separate tooling.

## Considered Options

| # | Topic | Chosen | Alternatives |
|---|---|---|---|
| 1 | Project layout | uv workspace: the root holds developer tools, `data_generator/` is a package (`streampulse-generator`), one shared `uv.lock` | One root project; separate projects with separate lockfiles |
| 2 | Data libraries | polars (explicit types, native Parquet) and numpy (seeded generators) | pandas with pyarrow |
| 3 | Fake PII | Faker, seeded per customer, with PL/DE/SE/NO locales | Hand-made name lists |
| 4 | Command line | argparse: `generate backfill`, `generate daily --days N` | typer |
| 5 | Determinism | Output is a pure function of seed, settings, and end date; a daily batch is that day's slice | Persist simulation state between runs |
| 6 | Output layout | `data/raw/<table>/load_date=YYYY-MM-DD/*.parquet`; backfill = one batch, daily = one batch per day | One file per table and date |
| 7 | Dependabot | Enabled weekly for uv and GitHub Actions, grouped, with Conventional Commit titles | Not now |

## Decision Outcome

All options marked "Chosen" above, decided together on 2026-11-13.

Determinism works as follows (see `randomness.py`). Every random stream is derived from the seed and a fixed label, never from the end date, and is consumed in date order: one stream per sign-up day, one per customer lifecycle (one billing period at a time), one per campaign and currency, and one per viewing column with access periods sorted by start time. Running to a later end date therefore only appends rows. Defects (duplicates, late arrival, missing keys) are decided by a hash of the row id, so a row gets the same defect in every run. A test checks that a backfill plus three daily batches equals a later backfill.

### Consequences

- Good, because daily batches, reruns, and backfills are interchangeable, which keeps Airflow tasks idempotent and makes the load path testable.
- Good, because all synthetic assumptions live in one file (`config.py`) and every one of them is covered by a test with tolerances.
- Good, because adding a component later means adding a workspace member, not new tooling.
- Bad, because every run simulates the whole history (about 25 seconds at full scale), even for a single daily batch. Acceptable for a portfolio dataset; state persistence can be added if volumes grow.
- Bad, because the generated data changes when Faker or numpy change their algorithms; the lockfile pins the versions, and a test pins the seed derivation.

### Confirmation

`data_generator/tests` runs in `ci-python`: determinism, append-only behavior, backfill-versus-daily equivalence, referential integrity, rate tolerances, and the CLI.

## More Information

- Phase 1 in [PLAN.md](../../PLAN.md); the deferred items in [ADR-001](001-overall-architecture-and-tool-choices.md).
- Tables, columns, and defects: [data_generator/README.md](../../data_generator/README.md).

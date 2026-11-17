---
status: accepted
date: 2026-11-16
decision-makers: Sylwia Berent
consulted: Claude Code (AI assistant; proposed options and trade-offs)
---

# ADR-010: Airflow 3 on the Astro Runtime, thin DAGs over the project's tools, assets between ingestion and transformation

## Context and Problem Statement

Phase 4 orchestrates the daily pipeline (generate, load, dbt build, Power BI refresh and validation, notification), a parameterized backfill, and maintenance, with retries, alerts, and DAG tests in CI. The Power BI workspace does not exist until Phase 5 (ADR-008).

## Decision Drivers

- DAGs only orchestrate; logic stays in the tested packages (CLAUDE.md).
- Reproducible images from the repository's lockfile; no secrets in images.
- Airflow's many pinned dependencies must not constrain the rest of the project.
- Everything except the Power BI steps works and is tested now.

## Considered Options

| # | Topic | Chosen | Alternatives |
|---|---|---|---|
| 1 | Runtime | Astro CLI with Astro Runtime 3.3 (Airflow 3.3.2), Python 3.12 image pinned by digest, in `orchestration/airflow/` | Plain Airflow Docker Compose; Airflow 2 |
| 2 | Alerts | Slack incoming webhook (`SLACK_WEBHOOK_URL`) from `on_failure_callback` after the last retry, plus a success message | Email through SMTP |
| 3 | SLAs | Airflow 3 removed task SLAs; retries with exponential backoff and alerts now, deadline alerts once they are stable in the runtime | Custom duration checks |
| 4 | Packaging | Generator, loader, and Power BI client installed as wheels into a separate virtual environment, dbt into another, both from `uv.lock` with hashes; Airflow is its own uv project with its own lockfile for the DAG tests | Install everything into Airflow's environment |
| 5 | Credentials | The repository's `.env` is passed to the containers; the DEV key file is mounted read-only (`docker-compose.override.yml`) | Airflow connections stored in the metadata database |

## Decision Outcome

All options marked "Chosen" above, decided together on 2026-11-16.

**DAGs.** `daily_pipeline` (generate the previous day's batch, load) and `backfill` (parameters `mode`, `days`, `end_date`) end by updating the RAW asset; `transform_pipeline` is scheduled on that asset (data-aware scheduling), so both paths trigger the same dbt build without duplicating it. dbt runs through Cosmos from the dbt manifest, with one task per model followed by its tests. The Power BI refresh, status polling, and validation tasks call `streampulse-powerbi` and are skipped until `POWERBI_ENABLED=true`; the success notification runs either way. `maintenance` lists old CI schemas and drops them only when triggered with `execute=true`, because dropping objects needs an explicit decision.

**Idempotency.** Generating a day replaces that day's batch with identical files; the loader skips files already staged and loaded; dbt incremental models merge on natural keys. Rerunning any task is safe.

**Lessons from the first end-to-end runs.**

- Cosmos runs a model's tests right after the model. Tests that read several models (relationships, the MRR bridge) then ran against a parent that was not rebuilt yet. They now run as detached tasks after all their parents (`should_detach_multiple_parents_tests`), as in `dbt build`.
- The Snowflake connector refuses private key files that others can write to, and Docker Desktop on Windows shows bind mounts that way. The key is mounted read-only and copied with mode 600 by the container entrypoint; the connector's check stays on.

### Consequences

- Good, because the DAGs are thin and every step is a command that also runs and is tested outside Airflow.
- Good, because daily runs and backfills share one transformation path through the asset.
- Bad, because Airflow does not run on native Windows: DAG tests run in the image locally (`run_astro.py test`) and on Linux in CI.
- Bad, because every dbt model is a separate task, which adds scheduling overhead; acceptable for about 50 models.

### Confirmation

`orchestration/airflow/tests` (import integrity, task structure, retries and alerts on every task, one dbt task per model, Power BI switch) in the `pytest` CI job; an end-to-end local run and a forced failure that posts an alert (Phase 4 Definition of Done).

## More Information

- [orchestration/airflow/README.md](../../orchestration/airflow/README.md), [powerbi/README.md](../../powerbi/README.md).
- [ADR-008](008-power-bi-and-fabric-licensing.md) (licensing and the Power BI timing), [ADR-002](002-logic-split-between-dbt-and-power-bi.md) (dbt).

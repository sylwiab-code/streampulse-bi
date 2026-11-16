# StreamPulse Airflow (Astro)

Orchestration for StreamPulse with Airflow 3.3 on the Astro Runtime ([ADR-010](../../docs/adr/010-orchestration-with-airflow.md)). The DAGs only orchestrate: every step calls a command-line tool from this repository (generator, loader, dbt, Power BI client).

## DAGs

| DAG | Schedule | Steps |
|---|---|---|
| `daily_pipeline` | daily 05:00 UTC | generate the previous day's batch → load into RAW (updates the RAW asset) |
| `backfill` | manual (parameters: `mode`, `days`, `end_date`) | generate history or several daily batches → load into RAW (updates the RAW asset) |
| `transform_pipeline` | when the RAW asset changes | dbt build (Cosmos: one task per model, then its tests) → Power BI refresh → wait → validate → notify |
| `maintenance` | weekly, Monday 06:00 UTC | table statistics → list CI schemas older than 7 days (drops them only with `execute=true`) |

Every task retries twice with exponential backoff; a task that fails its last retry posts a Slack alert (`SLACK_WEBHOOK_URL`). The Power BI steps are skipped until `POWERBI_ENABLED=true` (Phase 5, [ADR-008](../../docs/adr/008-power-bi-and-fabric-licensing.md)).

## Running locally

Prerequisites: Docker Desktop, the [Astro CLI](https://www.astronomer.io/docs/astro/cli/install-cli) (`winget install -e --id Astronomer.Astro`), and the Snowflake setup in [docs/guides/snowflake-setup.md](../../docs/guides/snowflake-setup.md). From the repository root:

```bash
uv run python orchestration/airflow/run_astro.py start
```

The Airflow UI opens at http://localhost:8080. Stop it with:

```bash
uv run python orchestration/airflow/run_astro.py stop
```

`run_astro.py` exports pinned requirements and wheels from `uv.lock` into `build/` (gitignored), refreshes the dbt manifest, passes the repository's `.env` to the containers, and mounts `transform/dbt`, `data/`, and the DEV key file (read-only) into them (`docker-compose.override.yml`). Inside the image, dbt and the StreamPulse tools run in their own virtual environments, separate from Airflow's packages.

## Tests

```bash
uv run python orchestration/airflow/run_astro.py test
```

This builds the image and runs `tests/` inside it (Airflow does not run on native Windows). CI runs the same tests on Linux with the separate uv project in this folder (`pyproject.toml`, `uv.lock`).

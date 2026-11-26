# StreamPulse BI

End-to-end BI portfolio project for StreamPulse, a fictional subscription video-on-demand (OTT) service operating in Poland, Germany, Sweden, and Norway. Synthetic data flows through Snowflake, dbt, and Airflow into Power BI and Microsoft Fabric, with CI/CD, automated tests, and guarded AI-assisted development.

**Status:** Phase 5 (Power BI semantic model) is complete: the PBIP model in TMDL imports the Snowflake marts and KPIs, with dynamic RLS per market, OLS for financial columns, Polish translations, and incremental refresh; BPA is clean, and the optimization pass cut memory by 88% ([ADR-011](docs/adr/011-power-bi-semantic-model.md), [performance report](docs/performance/semantic-model.md)). Phase 4 (orchestration with Airflow) is complete; the `powerbi` command that its refresh tasks call refreshes the published model as a service principal, and the automated post-refresh checks follow in Phase 7 ([ADR-008](docs/adr/008-power-bi-and-fabric-licensing.md)); see [orchestration/airflow/README.md](orchestration/airflow/README.md). Phase 3 (dbt transformations and KPI layer) is complete: staging, intermediate, star-schema marts with contracts, and KPI models with their definitions build and test green on DEV; documentation at https://sylwiab-code.github.io/streampulse-bi/. Phase 2 (Snowflake platform with Liquibase) is complete: one Liquibase command builds the DEV environment from zero, the loader puts the generated batches into the raw layer, and integration tests verify masking per role; setup in [docs/guides/snowflake-setup.md](docs/guides/snowflake-setup.md). Phase 1 (synthetic data generator) is complete: `uv run generate backfill` and `uv run generate daily --days 1` write deterministic Parquet batches; see [data_generator/README.md](data_generator/README.md). Phase 0 (foundations) is complete: `main` is protected by a ruleset, and a pull request with a failing lint cannot be merged ([demo PR #8](https://github.com/sylwiab-code/streampulse-bi/pull/8)). The phases and their Definition of Done are in [PLAN.md](PLAN.md); design decisions are in [docs/adr](docs/adr/README.md).

## Local development

Prerequisites: Git and [uv](https://docs.astral.sh/uv/). uv installs Python 3.12 if it is missing.

```bash
uv sync
```

This creates `.venv` with the developer tools (pre-commit, pytest) and the project's Python packages, which form a uv workspace with one lockfile ([ADR-009](docs/adr/009-synthetic-data-generator-design.md)). Then install the git hook once per clone:

```bash
uv run pre-commit install
```

Every commit now runs ruff, yamllint, sqlfluff (Snowflake dialect), actionlint, gitleaks, and basic file checks, and commits to `main` are refused. To check the whole repository at any time:

```bash
uv run pre-commit run --all-files
```

The `ci-lint` workflow runs the same hooks on every pull request and on `main`, scans the full git history for secrets, and checks that the PR title follows Conventional Commits. The history scan can also be run locally:

```bash
uv run pre-commit run gitleaks-history --hook-stage manual
```

Run the tests with `uv run pytest`; the `ci-python` workflow runs them on every pull request and on `main`.

`.claude/` holds the shared Claude Code settings and a command guard for AI-assisted work; see [docs/ai-workflow.md](docs/ai-workflow.md#guardrails).

For local settings, copy `.env.example` to `.env` and fill in the DEV values. `.env` is gitignored; never put TEST or PROD credentials in it.

## Contributing

Every change goes through a pull request. Reviews follow [docs/standards/review-checklist.md](docs/standards/review-checklist.md).

`main` is protected by the ruleset in [.github/rulesets/main.json](.github/rulesets/main.json): the `pre-commit`, `gitleaks`, `pr-title`, and `pytest` checks must pass, merges are squash-only with linear history, force pushes and deletion are blocked, and nobody can bypass the rules. The file is applied with the GitHub API:

```bash
gh api --method POST repos/sylwiab-code/streampulse-bi/rulesets --input .github/rulesets/main.json
```

To change the rules, edit the file and send it with `--method PUT` to `repos/sylwiab-code/streampulse-bi/rulesets/<id>`.

## Snowflake

The platform is defined in [database/](database/) and applied with Liquibase in Docker; the loader in [loader/](loader/) puts generated batches into the raw layer. One-time setup and the commands to build DEV, load data, and verify masking: [docs/guides/snowflake-setup.md](docs/guides/snowflake-setup.md).

## dbt

The transformation layer is in [transform/dbt/](transform/dbt/): staging, intermediate, marts (star schema), and KPI models, following [docs/standards/dbt.md](docs/standards/dbt.md). Which logic lives in dbt and which in Power BI, and the KPI definitions, are in [ADR-002](docs/adr/002-logic-split-between-dbt-and-power-bi.md).

```bash
uv run python transform/run_dbt.py deps
```

```bash
uv run python transform/run_dbt.py build
```

The documentation site (lineage, tests, KPI definitions) is published to GitHub Pages on every merge: https://sylwiab-code.github.io/streampulse-bi/.

## Airflow

The daily pipeline, backfill, and maintenance run on Airflow 3 (Astro) in [orchestration/airflow/](orchestration/airflow/) ([ADR-010](docs/adr/010-orchestration-with-airflow.md)):

```bash
uv run python orchestration/airflow/run_astro.py start
```

## Power BI

The semantic model is a Power BI project (PBIP) in [semantic/powerbi/](semantic/powerbi/README.md), following [docs/standards/semantic-model.md](docs/standards/semantic-model.md). Before opening it in Power BI Desktop, set the Snowflake host locally (Git keeps a placeholder):

```bash
uv run python semantic/powerbi/connection.py set
```

The Best Practice Analyzer runs locally on Windows:

```bash
uv run python semantic/powerbi/run_bpa.py
```

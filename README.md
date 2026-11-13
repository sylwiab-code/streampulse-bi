# StreamPulse BI

End-to-end BI portfolio project for StreamPulse, a fictional subscription video-on-demand (OTT) service operating in Poland, Germany, Sweden, and Norway. Synthetic data flows through Snowflake, dbt, and Airflow into Power BI and Microsoft Fabric, with CI/CD, automated tests, and guarded AI-assisted development.

**Status:** Phase 1 (synthetic data generator) complete: `uv run generate backfill` and `uv run generate daily --days 1` write deterministic Parquet batches; see [data_generator/README.md](data_generator/README.md). Phase 0 (foundations) is complete: `main` is protected by a ruleset, and a pull request with a failing lint cannot be merged ([demo PR #8](https://github.com/sylwiab-code/streampulse-bi/pull/8)). The phases and their Definition of Done are in [PLAN.md](PLAN.md); design decisions are in [docs/adr](docs/adr/README.md).

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

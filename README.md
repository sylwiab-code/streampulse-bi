# StreamPulse BI

End-to-end BI portfolio project for StreamPulse, a fictional subscription video-on-demand (OTT) service operating in Poland, Germany, Sweden, and Norway. Synthetic data flows through Snowflake, dbt, and Airflow into Power BI and Microsoft Fabric, with CI/CD, automated tests, and guarded AI-assisted development.

**Status:** Phase 0 (foundations) in progress. The phases and their Definition of Done are in [PLAN.md](PLAN.md); design decisions are in [docs/adr](docs/adr/README.md).

## Local development

Prerequisites: Git and [uv](https://docs.astral.sh/uv/). uv installs Python 3.12 if it is missing.

```bash
uv sync
```

This creates `.venv` with the developer tools (pre-commit, pytest). Then install the git hook once per clone:

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

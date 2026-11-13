# StreamPulse BI

End-to-end BI portfolio project for StreamPulse, a fictional subscription video-on-demand (OTT) service operating in Poland, Germany, Sweden, and Norway. Synthetic data flows through Snowflake, dbt, and Airflow into Power BI and Microsoft Fabric, with CI/CD, automated tests, and guarded AI-assisted development.

**Status:** Phase 0 (foundations) in progress. The phases and their Definition of Done are in [PLAN.md](PLAN.md); design decisions are in [docs/adr](docs/adr/README.md).

## Local development

Prerequisites: Git and [uv](https://docs.astral.sh/uv/). uv installs Python 3.12 if it is missing.

```bash
uv sync
```

This creates `.venv` with the developer tools (pre-commit, pytest).

For local settings, copy `.env.example` to `.env` and fill in the DEV values. `.env` is gitignored; never put TEST or PROD credentials in it.

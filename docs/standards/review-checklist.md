# Review Checklist

Use this list when reviewing a pull request, in addition to the checklist in the PR template. Not every item applies to every PR. Conventions are in [CLAUDE.md](../../CLAUDE.md).

## Every PR

- One logical change; the title is a Conventional Commit and reads well as the squash commit message.
- The description explains what, why, and how it was tested.
- No secrets, keys, tokens, or real personal data in code, docs, logs, or test fixtures.
- Nothing runs against PROD outside the CD workflow.
- Docs and ADRs are updated in the same PR; no unused boilerplate is added.

## Python

- Type hints, small modules, and pytest tests for new behavior.
- New dependencies were agreed before they were added.

## SQL and dbt

- The model name follows the layer prefix; one model per file, CTE style.
- The YAML entry has a description; primary keys are tested for unique and not_null.
- Marts have contracts; KPI models carry `meta` (owner, definition, grain, formula, scope).
- Business rules come from an agreed definition, not from assumptions.

## Database changes (Liquibase)

- One logical change per changeset, with a rollback where possible.
- The `updateSQL` preview was reviewed.
- Changes that drop objects were agreed before they were made.

## CI and automation

- Actions are pinned to commit SHAs; permissions are as narrow as possible.
- Untrusted input (PR titles, branch names) reaches scripts only through environment variables.
- Airflow DAGs only orchestrate; tasks are idempotent.

## Power BI

- Measures have business names, display folders, descriptions, and format strings.
- BPA is clean, or the exception is documented.
- Screenshots are attached for report changes.

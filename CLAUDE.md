# CLAUDE.md — StreamPulse

## Project

End-to-end BI portfolio project for a fictional OTT subscription service. Full plan, phases, and Definition of Done are in `PLAN.md`. Read it before starting any task and work on one phase at a time.

Stack: Python (uv), Snowflake, Liquibase, dbt, Airflow (Astro CLI, Cosmos), Power BI (PBIP: TMDL + PBIR), Microsoft Fabric, GitHub Actions, MCP (Python).

## Roles

- Sylwia is the architect and decision-maker. Claude proposes and implements.
- For any design choice with real alternatives, present options with trade-offs and wait for a decision. Record the decision as an ADR in `docs/adr/`.
- Do not invent business rules. If a KPI definition or rule is unclear, ask.

## Workflow Rules

- Plan before code: for each task, state the approach and the files to change, then implement.
- One branch per task (`feat/`, `fix/`, `docs/`, `chore/` prefixes); small commits; Conventional Commits.
- Never commit directly to `main`.
- Every change includes tests or a stated reason why none apply.
- Run linters and relevant tests before proposing a commit.
- Update docs in the same PR as the code (README sections, standards, ADRs, KPI metadata).
- Keep the repo free of unused boilerplate.

## Safety Rules

- Never run anything against PROD (Snowflake `PROD` database, Prod workspace). PROD changes go only through the CD workflow with approval.
- Liquibase `update` only against DEV locally. Use `updateSQL` to preview.
- Never print, log, or commit secrets, keys, or tokens. Use `.env` (gitignored) locally and GitHub Environments in CI.
- Never query PII columns unmasked. Use the `AI_READONLY` role for exploratory queries.
- Ask before: deleting files, dropping objects, changing CI/CD workflows, changing tenant or workspace settings, installing new dependencies.
- Suspend Snowflake warehouses and avoid long-running queries; prefer small samples.

## Conventions

### General
- All code, comments, docs, and commit messages in clear, neutral international English.

### Python
- uv for environments; ruff for lint and format; pytest; type hints; small modules.

### SQL / dbt
- sqlfluff (Snowflake dialect), lowercase keywords, CTE-based style, one model per file.
- Layers and prefixes: `stg_<source>__<entity>`, `int_<entity>_<verb>`, `fct_<process>`, `dim_<entity>`, `kpi_<name>`.
- Every model has a YAML entry with description; marts have contracts; primary keys tested (unique, not_null).
- KPI models carry `meta`: `owner`, `definition`, `grain`, `formula`, `scope` (global/local).
- Business logic lives in dbt unless ADR-002 says otherwise.

### Liquibase
- Changelogs per object type; one logical change per changeset; include rollback where possible; contexts per environment.

### Power BI (PBIP)
- TMDL: NO TMDL-level comments (`///` or `//` outside expressions are not accepted). Use the `description` property instead. Comments only inside DAX or M expressions.
- Measures: clear business names, display folders, descriptions, format strings.
- Prefer pre-calculated KPIs from dbt; DAX for time intelligence, ratios at query grain, and what-if.
- Keep BPA clean; document any accepted exception.
- Reports in PBIR format; follow `docs/standards/report-design.md`.

### Airflow
- DAGs are thin: orchestration only, no business logic. Idempotent tasks. Connections from environment variables.

## Definition of Done (every PR)

- CI green.
- Tests added or updated.
- Docs updated.
- ADR written if a design decision was made.
- PR description: what, why, how tested, screenshots for reports.

## Documentation of AI Use

- Notable AI suggestions that were rejected or significantly changed go into `docs/ai-workflow.md` with a short reason.
- Performance work goes into `docs/performance/` with before/after numbers.
- Real incidents go into `docs/postmortems/`.

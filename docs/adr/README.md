# Architecture Decision Records

Every design choice with real alternatives is recorded here as an ADR (see `CLAUDE.md`, section Roles). An ADR states the context, the options that were considered, the decision, and its consequences. ADRs are never edited to change a decision; a new ADR supersedes the old one.

The format is based on [MADR](https://adr.github.io/madr/).

## Process

1. Copy [`template.md`](template.md) to `NNN-short-slug.md`, using the next free number.
2. Fill it in with `status: proposed` and open a PR (`docs/` branch prefix).
3. The decision-maker reviews the options and decides. AI-proposed options that were rejected are also logged in [`docs/ai-workflow.md`](../ai-workflow.md).
4. Set `status: accepted` and the decision date, then merge.
5. To change a decision later, write a new ADR and set the old one to `status: superseded by ADR-NNN`.

## Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [001](001-overall-architecture-and-tool-choices.md) | Overall architecture and tool choices | Accepted | 2026-11-12 |
| [002](002-logic-split-between-dbt-and-power-bi.md) | Logic split between dbt and Power BI, dbt setup, and KPI definitions | Accepted | 2026-11-15 |
| [003](003-snowflake-environments-and-liquibase-boundary.md) | Snowflake environments, roles, masking, and the Liquibase/dbt boundary | Accepted | 2026-11-14 |
| [008](008-power-bi-and-fabric-licensing.md) | Power BI and Fabric licensing: trials on an own tenant, started with Phase 5 | Accepted | 2026-11-16 |
| [009](009-synthetic-data-generator-design.md) | Synthetic data generator design | Accepted | 2026-11-13 |
| [010](010-orchestration-with-airflow.md) | Orchestration with Airflow 3 on the Astro Runtime | Accepted | 2026-11-16 |
| [011](011-power-bi-semantic-model.md) | Power BI semantic model in TMDL, Import from Snowflake with a key-pair service user, dynamic RLS per market | Accepted | 2026-11-18 |

Planned ADRs and the phases that produce them are listed in [`PLAN.md`](../../PLAN.md), section 10.

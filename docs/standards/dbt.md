# dbt Standard

How the dbt project in `transform/dbt` is built ([ADR-002](../adr/002-logic-split-between-dbt-and-power-bi.md)). Names follow [naming.md](naming.md).

## Running

```bash
uv run python transform/run_dbt.py deps
```

```bash
uv run python transform/run_dbt.py build
```

The runner loads `.env` and connects as `TRANSFORMER_DEV`; only the DEV target exists locally. `dbt build` runs models, snapshots, data tests, and unit tests in dependency order.

## Layers

| Layer | Schema | Materialization | Purpose |
|---|---|---|---|
| Staging | `STAGING` | view; incremental merge for event tables | One model per source table: rename, cast, deduplicate, take the latest snapshot version. No joins and no business logic. |
| Intermediate | `INTERMEDIATE` | table | Business logic: subscription spells, daily state, MRR, movements, flags. Not exposed to reporting roles. |
| Marts | `MARTS` | table with an enforced contract | Star schema for Power BI: `dim_*` and `fct_*` with stable, typed columns. |
| KPI | `KPI` | table (local extensions: view) | One model per KPI family with its definition in `meta`; the source of the KPI catalog. |

Rules:

- **One model per file**, CTE style: one CTE per input (`select * from {{ ref(...) }}`), then named steps, then `select * from final` (or the last step).
- **Staging is the only layer that reads sources.** Every other layer reads `ref()`.
- Late-arriving and duplicated rows are handled in staging: incremental models read rows with a newer `_loaded_at` and merge on the natural key.
- Marts read intermediate and staging models, never other marts' internals. KPI models read marts; a KPI model may reuse another KPI model to keep one definition (for example LTV reuses churn and ARPU).
- **Global vs local:** local extensions (`kpi_<market>_*`) select from the global KPI model and only add local columns; they never recompute global logic.
- Column order follows meaning (keys, attributes, measures); sqlfluff rule ST06 is disabled for that reason.

## Required YAML

- Every model has a `description`.
- Marts: an enforced contract with a `data_type` and description for every column.
- Every mart and KPI model tests its grain (`unique` or `dbt_utils.unique_combination_of_columns`); foreign keys use `relationships`; categorical columns use `accepted_values`; ranges use `dbt_expectations`.
- KPI models carry `meta`: `owner`, `definition`, `grain`, `formula`, `scope` (`global` or `local`). Expose numerators and denominators next to ratios so that Power BI can recompute ratios at any grain.
- Generic test arguments go under `arguments:`.

`tests/dbt/test_project_conventions.py` checks these rules on every pull request.

## Testing

| Kind | Where | Example |
|---|---|---|
| Unit tests | `models/**/_*__unit_tests.yml` | every MRR movement type, churn classification, late rows in incremental runs |
| Data tests | model YAML | grain, relationships, accepted values, ranges |
| Singular tests | `tests/assert_*.sql` | the MRR bridge reconciles in local currency and EUR |
| Source freshness | `_streampulse__sources.yml` | warn after 26 hours, error after 50 |

Unit tests and data tests need DEV; CI runs `dbt parse` and the convention tests until Phase 7 adds a CI connection.

## Security

dbt runs as `TRANSFORMER_<ENV>`, which reads PII through masking policies: names and email arrive as SHA-256 hashes (email normalized), so no clear-text PII enters dbt models. Marts and KPI models are readable by `REPORTER`, `AI_READONLY`, and `PII_READER`; staging and intermediate are not. The schemas are created by Liquibase with managed access ([ADR-003](../adr/003-snowflake-environments-and-liquibase-boundary.md)).

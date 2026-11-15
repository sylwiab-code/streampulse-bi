---
status: accepted
date: 2026-11-14
decision-makers: Sylwia Berent
consulted: Claude Code (AI assistant; proposed options and trade-offs)
---

# ADR-003: One database per environment, Liquibase for platform and security objects, dbt for transformations

## Context and Problem Statement

Phase 2 builds the Snowflake platform: environments, roles, warehouses, the raw landing layer, PII masking, service users, and a loader for the generator's Parquet batches. A fresh environment must be created from zero with one Liquibase command, and masking must be verified per role. We need to decide how environments are laid out, which tool owns which objects, and how roles, masking, raw tables, and authentication work.

## Decision Drivers

- DEV must never be able to change TEST or PROD; PROD changes only through CD (CLAUDE.md).
- One command recreates an environment; changes are reviewable and reversible.
- PII (names, email) is masked by default, but dbt must still deduplicate customers.
- Low cost on a trial account; no secrets in the repository or on the command line.

## Considered Options

| # | Topic | Chosen | Alternatives |
|---|---|---|---|
| 1 | Environment layout | One database per environment (`STREAMPULSE_DEV`, `_TEST`, `_PROD`) in one account; schema `RAW` now, dbt schemas from Phase 3 | A database per layer per environment |
| 2 | Tool boundary | Liquibase owns security and ingestion objects (databases, `RAW` tables, stage, file format, warehouses, roles, grants, masking policies, service users); dbt owns models and its own schemas | dbt also manages grants |
| 3 | Roles | Functional account roles per environment (`LOADER_DEV`, `TRANSFORMER_DEV`, `REPORTER_DEV`, `AI_READONLY_DEV`, `PII_READER_DEV`, `DEPLOYER_DEV`) on top of database roles as access roles (`RAW_READ`, `RAW_WRITE`) | Environment-agnostic roles; account roles only |
| 4 | Masking | One policy on `first_name`, `last_name`, `email`: clear text for `PII_READER`, SHA-256 of the trimmed lowercase value for `TRANSFORMER`, `***MASKED***` for everyone else | Mask for every non-privileged role |
| 5 | Warehouses and cost | X-Small per environment and workload (`WH_LOAD`, `WH_TRANSFORM`, `WH_REPORT`), auto-suspend 60 s; account resource monitor of 25 credits per month (notify 75%, suspend 100%) | Warehouses shared across environments |
| 6 | Raw tables | Typed columns matching the Parquet files, loaded with `COPY ... MATCH_BY_COLUMN_NAME`, plus `_file_name`, `_file_row_number`, `_loaded_at`; source schema changes become Liquibase changesets | One `VARIANT` column per table |
| 7 | Liquibase setup | Formatted SQL changelogs per object type, linted by sqlfluff with the placeholder templater; the official Docker image (pinned by digest) plus the Snowflake JDBC driver (pinned by checksum); one properties file and change log table per environment in `STREAMPULSE_ADMIN.LIQUIBASE` | Local Java and Liquibase install; XML or YAML changelogs |
| 8 | Loader | Workspace package `streampulse-loader`: PUT batches to `@RAW.LANDING`, then COPY into the raw tables; idempotent through Snowflake load history | Loader inside the generator package |
| 9 | Masking verification | Opt-in pytest integration tests against DEV that compare counts per role, never values | Manual checks |

## Decision Outcome

All options marked "Chosen" above, decided together on 2026-11-14.

**Bootstrap.** Objects that only `ACCOUNTADMIN` can create, or that Liquibase needs before its first run, are created once by `database/bootstrap/bootstrap_dev.sql`, run by a human in Snowsight: the resource monitor, `WH_DEPLOY`, `STREAMPULSE_ADMIN.LIQUIBASE`, the `DEPLOYER_DEV` role with `CREATE DATABASE / WAREHOUSE / ROLE / USER`, and the key-pair user `SVC_DEPLOYER_DEV`. Everything else is in Liquibase. TEST and PROD get the same bootstrap with their own deployer in Phase 7.

**Authentication.** Service users have `TYPE = SERVICE` (no password) and key-pair authentication. The private key stays on the developer machine outside the repository; tools receive only its path. On developer machines the DEV deployer user also runs the loader and the integration tests, switching to each functional role, so one key pair is enough locally. Service users have no default secondary roles, and connections run `USE SECONDARY ROLES NONE`, because masking checks the roles in the session.

**Managed access.** The `RAW` schema is created `WITH MANAGED ACCESS`, so its owner (the deployer) can define future grants. A regular schema would need the account-wide `MANAGE GRANTS` privilege, which would let the DEV deployer change grants in TEST and PROD. Managed access must be set at creation: enabling it later also needs `MANAGE GRANTS`. dbt schemas follow the same rule in Phase 3.

**Parquet types.** The file format sets `USE_LOGICAL_TYPE = TRUE`; without it, Parquet timestamps (INT64 microseconds) load as far-future dates. An integration test checks the loaded date ranges.

**Guardrails.** `database/liquibase/run.py` and the loader refuse TEST and PROD outside GitHub Actions.

**Linting.** ADR-001 (D7) planned the jinja templater for `database/`. Liquibase parameters (`${env}`) are not jinja, so `database/` is linted with the placeholder templater through its own config file; `transform/` keeps jinja.

### Consequences

- Good, because environments are isolated by database and role names, and one `liquibase update` builds an environment.
- Good, because dbt can deduplicate customers and detect trial abuse on hashed values without seeing PII.
- Good, because a source schema change is an explicit, reviewable changeset.
- Bad, because the bootstrap is a manual step per environment; it is short and documented.
- Bad, because typed raw tables need a changeset before a file with new columns arrives; unknown columns are not loaded until then.

### Confirmation

- `tests/database`: every environment has a properties file, every changeset has a rollback, and the runner refuses non-DEV environments locally.
- `loader/tests/test_snowflake_dev.py` (opt in with `STREAMPULSE_SNOWFLAKE_TESTS=1`): masking per role, access denied for roles without read access, and every local file loaded.

## More Information

- Setup steps: [docs/guides/snowflake-setup.md](../guides/snowflake-setup.md).
- [ADR-002](002-logic-split-between-dbt-and-power-bi.md) refines the tool boundary for dbt: Liquibase creates the dbt schemas (managed access), dbt owns the objects inside them.
- Phase 2 in [PLAN.md](../../PLAN.md); generator output in [data_generator/README.md](../../data_generator/README.md).

# Naming Standard

Names in StreamPulse are lowercase `snake_case` in English. Snowflake stores unquoted identifiers in uppercase, so case never matters in queries.

## Models (dbt)

| Layer | Pattern | Example |
|---|---|---|
| Staging | `stg_<source>__<entity>` (double underscore) | `stg_streampulse__payments` |
| Intermediate | `int_<entity>_<verb in past tense>` | `int_mrr_movements_classified` |
| Marts | `dim_<entity>`, `fct_<process>` | `dim_customer`, `fct_mrr_movements` |
| KPI | `kpi_<name>[_<grain>]` | `kpi_churn_monthly` |
| Local extensions | `kpi_<market>_<name>` | `kpi_de_mrr_net_of_vat` |
| Snapshots | `snap_<entity>` | `snap_plan_prices` |
| Seeds | `<area>_<entity>` | `security_market_access` |
| Singular tests | `assert_<expectation>` | `assert_mrr_bridge_reconciles` |

## Columns

**Never use an SQL keyword as a column name.** Bare keywords break linting (sqlfluff RF04) or force quoted identifiers, and some are reserved in Snowflake. Use a descriptive, suffixed name instead:

| Instead of | Use |
|---|---|
| `date` | `calendar_date`, `date_day`, or `<event>_date` |
| `value`, `amount` | `<measure>_amount`, `<measure>_local`, `<measure>_eur` |
| `name`, `type` | `<entity>_name`, `<entity>_type` |
| `timestamp` | `<event>_at` |
| `role`, `user`, `comment`, `order`, `group`, `table` | a name with the entity, for example `user_role`, `order_number` |

Further rules:

- **Never quote identifiers.**
- Timestamps end in `_at` (`created_at`), dates in `_date` (`signup_date`), months in `_month` (`cohort_month`, the first day of the month), and booleans start with `is_` or `has_`.
- Amounts carry their currency: `_local` (market currency, with `currency_code` in the same row) or `_eur`.
- Counts are plural nouns (`active_subscribers`, `trials_started`); ratios end in `_rate` or name the ratio (`ltv_to_cac`).
- Keys are `<entity>_id`; codes are `<entity>_code`.

**Exception:** source columns we do not control keep their names in RAW and staging. The sqlfluff `ignore_words` list in `.sqlfluff` is only for those (currently `first_name`, `last_name`, `email`). Rename them in staging where the meaning changes, for example `email` → `email_hash`.

`tests/dbt/test_project_conventions.py` checks model prefixes and keyword column names on every pull request.

## Snowflake objects

| Object | Pattern | Example |
|---|---|---|
| Database | `STREAMPULSE_<ENV>` | `STREAMPULSE_DEV` |
| Schema | layer name | `RAW`, `STAGING`, `MARTS`, `KPI` |
| Warehouse | `WH_<WORKLOAD>_<ENV>` | `WH_TRANSFORM_DEV` |
| Functional role | `<FUNCTION>_<ENV>` | `REPORTER_DEV` |
| Database role | `<SCHEMA OR AREA>_<READ/WRITE>` | `ANALYTICS_READ` |
| Service user | `SVC_<SERVICE>_<ENV>` | `SVC_LOADER_DEV` |
| Masking policy | `PII_<KIND>` in `GOVERNANCE` | `PII_EMAIL` |

## Power BI

Business names in the semantic model; the full rules are in [semantic-model.md](semantic-model.md#names).

| Object | Pattern | Example |
|---|---|---|
| Table | Business process or entity, title case | `Viewing Sessions`, `Customer` |
| Visible column | Business name, title case | `Billing Period`, `Market Code` |
| Hidden key or measure input | dbt column name | `customer_id`, `active_subscribers` |
| Measure | Business name, currency in brackets | `MRR (EUR)`, `Monthly Churn Rate` |
| Role | Audience | `Market`, `Global`, `Content Analyst` |
| Workspace | `StreamPulse <ENV>` | `StreamPulse DEV` |

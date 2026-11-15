---
status: accepted
date: 2026-11-15
decision-makers: Sylwia Berent
consulted: Claude Code (AI assistant; proposed options and trade-offs)
---

# ADR-002: dbt computes states, movements, and KPI components; Power BI computes time intelligence and ratios at query grain

## Context and Problem Statement

Phase 3 builds the transformation layer and the KPI definitions that Power BI (Phase 5) consumes. We need to decide which logic lives in dbt and which in DAX, how the dbt project is run and secured, and how the KPIs are defined.

## Decision Drivers

- One definition per KPI, reusable by Power BI, the KPI catalog, and the MCP server (Phase 10).
- Ratios must stay correct when a report slices them at a different grain.
- No clear-text PII in models; least privilege for reporting roles.
- Testable logic, including late-arriving data.

## Considered Options

| # | Topic | Chosen | Alternatives |
|---|---|---|---|
| 1 | dbt runtime | dbt Core 1.12 with dbt-snowflake, pinned in the uv lockfile; project in `transform/dbt` | dbt Fusion engine; dbt Cloud |
| 2 | Connection | Committed `profiles.yml` with `env_var()` only; key pair; `TRANSFORMER_DEV` on `WH_TRANSFORM_DEV` | Profiles outside the repository |
| 3 | dbt schemas | Created by Liquibase with managed access (`STAGING`, `INTERMEDIATE`, `MARTS`, `KPI`, `SNAPSHOTS`); dbt owns the objects inside. This refines the boundary in ADR-003: dbt owns its objects, not its schemas | dbt creates schemas (needs account-wide `MANAGE GRANTS` for future grants) |
| 4 | Repeat-trial detection | TRANSFORMER's email hash is computed on the normalized address (lowercase, `+tag` removed) | Hash of the raw address (repeat trials invisible) |
| 5 | Incremental models | Event staging models and `fct_viewing_sessions`: merge on the natural key, new rows by `_loaded_at` | Full rebuilds |
| 6 | Packages | `dbt_utils` 1.4.1, `dbt_expectations` 0.10.10 | Hand-written macros |
| 7 | Documentation | Built in CI without a warehouse connection, published to GitHub Pages on merge | Live catalog with a CI key (Phase 7) |
| 8 | CI | `dbt parse` and convention tests in the `pytest` job; `dbt build` against DEV locally until Phase 7 | A new required check |
| 9 | Logic split | See below | More logic in DAX |

## Decision Outcome

All options marked "Chosen" above, decided together on 2026-11-15.

**In dbt:** daily subscription state (`fct_subscription_daily`), MRR and MRR movements, churn classification, cohort retention, CAC and LTV inputs, the repeat-trial flag, and all currency conversion. KPI models expose numerators and denominators (for example `churned_subscribers` and `active_at_month_start`) next to the ratio at the model's grain.

**In Power BI (DAX):** time intelligence (YoY, MTD, rolling periods), ratios at the grain of the visual (ARPU, churn rate, conversion, LTV/CAC, recomputed from the components), and what-if analysis.

**KPI definitions** (decided by the owner; stored in each KPI model's `meta`):

| KPI | Definition |
|---|---|
| Active subscriber | Paid subscription not ended on the day, including payment-retry days; trials are counted separately |
| MRR, ARR | Plan price paid, normalized to a month (annual / 12), local currency and EUR at the day's rate; before the first successful payment, the plan's list price. ARR = MRR x 12 |
| MRR movements | Month-end vs previous month-end per customer: new, reactivation, expansion (upgrade or price increase), contraction (downgrade), churn; an fx_effect line reconciles the EUR bridge |
| Churn rate | Churned in the month / active at the first day of the month; voluntary and involuntary; expired trials are not churn |
| ARPU | MRR / active subscribers at month end |
| Trial-to-paid conversion | Converted / started, by trial start month, channel, campaign |
| Cohort retention | Cohort = first payment month; retained in month k if active at its end; months 0-24 |
| CAC | Paid-channel spend / new paying customers from that channel |
| LTV, LTV/CAC | LTV = ARPU / monthly churn rate (revenue-based) |
| Watch hours, engagement | Watch minutes / 60 per subscriber, title, genre |
| Content performance | Completion = watched / runtime (capped at 100%); reach = distinct viewers |
| Repeat-trial flag | An earlier customer with the same normalized email had an expired trial |
| Global vs local | Global KPIs in EUR and local currency; example local extension: DE MRR net of 19% VAT |

### Consequences

- Good, because each KPI has one tested definition and Power BI only aggregates and divides.
- Good, because the MRR bridge reconciles by construction and is checked by a singular test.
- Good, because late and duplicated source rows are handled once, in staging, and unit-tested.
- Bad, because `fct_subscription_daily` is large (about 10 million rows for two years) and rebuilt on every run; it can become incremental if the volume grows.
- Bad, because the churn rate is not meaningful in the launch month (November 2024), when the starting base is tiny.

### Confirmation

`dbt build` on DEV (data tests, unit tests for every MRR movement type, churn, and late rows), the singular bridge test, and `tests/dbt/test_project_conventions.py` in CI.

## More Information

- Standards: [docs/standards/dbt.md](../standards/dbt.md), [docs/standards/naming.md](../standards/naming.md).
- Phase 3 in [PLAN.md](../../PLAN.md); platform boundary in [ADR-003](003-snowflake-environments-and-liquibase-boundary.md).

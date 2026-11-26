---
status: accepted
date: 2026-11-18
decision-makers: Sylwia Berent
consulted: Claude Code (AI assistant; proposed options and trade-offs, built and measured the model)
---

# ADR-011: Power BI semantic model in TMDL, Import from Snowflake with a key-pair service user, dynamic RLS per market

## Context and Problem Statement

Phase 5 builds the semantic model that the Phase 6 reports and the Phase 7 deployment use. It needs decisions on how the model is authored and connected, which dbt models it loads, how much logic goes into DAX (within [ADR-002](002-logic-split-between-dbt-and-power-bi.md)), security, refresh, and how its quality is checked. The workspace is `StreamPulse DEV` on Power BI Pro, without a capacity (see the update in [ADR-008](008-power-bi-and-fabric-licensing.md)).

## Decision Drivers

- The model is reviewable text in Git and checked in CI, like the rest of the project.
- No secrets and no account host in the repository.
- Ratios stay correct at any grain; KPI definitions stay in dbt (ADR-002).
- Market users see only their markets; content analysts see no financial data.
- The model fits Pro limits (1 GB, 8 scheduled refreshes, no XMLA endpoint).

## Considered Options

| # | Topic | Chosen | Alternatives |
|---|---|---|---|
| 1 | Authoring | PBIP with TMDL and PBIR in `semantic/powerbi/`, written as text; Power BI Desktop saves are accepted as the canonical format | Desktop only; Tabular Editor as the editor |
| 2 | Snowflake access | Service user `SVC_POWERBI_DEV` (type service, role `REPORTER_DEV`, warehouse `WH_REPORT_DEV`) with key-pair authentication | A person's account with SSO; password authentication |
| 3 | Scope | Dimensions, KPI models, and three facts (MRR movements, payments, viewing sessions) | KPI models only |
| 4 | Connection | Parameters for server, database, warehouse, and role; the host is a placeholder in Git (`connection.py`, pre-commit hook) | One hard-coded connection per environment |
| 5 | DAX | Few measures over pre-calculated components, a calculation group for time intelligence, field parameters for KPI and dimension selectors | Separate YTD/PY measures per KPI |
| 6 | Incremental refresh | `Viewing Sessions`: keep 2 years, refresh the last 7 days, filtered on `STARTED_AT` in the source query | Full refresh of all tables |
| 7 | Best Practice Analyzer | Tabular Editor 2 command line with Microsoft's rules (pinned by commit and hash) and project rules (`bpa-rules.json`); exceptions as `BestPracticeAnalyzer_IgnoreRules` annotations | No BPA; BPA in Fabric notebooks (needs a capacity) |
| 8 | CI checks | Offline pytest checks on the TMDL text (`tests/powerbi/`) in the `pytest` job; BPA runs locally (Windows) | BPA in CI on a Windows runner |
| 9 | Performance | VertiPaq Analyzer exports and DAX Studio benchmarks (cold and warm cache), before and after | Desktop Performance Analyzer only |
| 10 | Post-refresh checks | Postponed to Phase 7; the comparison queries are kept in `semantic/powerbi/reconciliation.json` and were run by hand against Desktop | `powerbi validate` in Airflow now |
| 11 | RLS | Roles `Market` (dynamic: `USERPRINCIPALNAME()` against the dbt seed `security_market_access`) and `Global` (all markets) | Static role per market |
| 12 | OLS | Role `Content Analyst` without access to revenue, payment amount, and spend columns | Separate model for content |
| 13 | Translations | `en-US` and `pl-PL` captions and display folders | English only |

## Decision Outcome

All options marked "Chosen" above, decided together on 2026-11-18. Option 10 was decided on 2026-11-19, when the Execute Queries limitation was confirmed.

**Tables.** Date, Market, Plan, Channel, Campaign, Content, and Customer from `MARTS`; Subscribers Daily, Churn, Trial Conversion, Cohort Retention, Acquisition Cost, and DE MRR Net of VAT from `KPI`; MRR Movements, Payments, and Viewing Sessions from `MARTS`; Security Market Access (hidden); the Time Intelligence calculation group; and the KPI Selector and Dimension Selector field parameters. Changed from the approved list during the build:

- Engagement and content measures read `fct_viewing_sessions` instead of `kpi_engagement_monthly` and `kpi_content_performance_monthly`: distinct viewers do not add up across months, genres, or titles, and the content KPI has no market for RLS.
- MRR movements read `fct_mrr_movements` instead of `kpi_mrr_movements_monthly`, so movements can be counted per customer and sliced by plan and channel. dbt adds `movement_type_rank` for the bridge order.

**Measures.** 36 measures in display folders, each with a description and a format string. Snapshot KPIs (active subscribers, trialists, MRR, ARR) take the last day of the selected period, capped at the last loaded day. Ratios are recomputed from their components with `DIVIDE` (ARPU, churn rate, conversion, retention, CAC, LTV, LTV/CAC). Local-currency measures return a value only for a single currency and show its code through a dynamic format string. Over several months, the churn rate is the sum of churned subscribers over the sum of subscribers at month start, a weighted average monthly rate.

**Security.** `Market` filters only `Market` and the user's own rows of the mapping table; every fact reaches Market through its own relationship path. `Global` reads everything. `Content Analyst` has `columnPermission none` on nine financial columns; measures that use them are unavailable to that role. Roles have no members in the repository. The mapping seed uses fictional addresses (`*.example`), and members are assigned in the service.

**Descriptions.** In TMDL, `///` directly above a declaration is the object's description; a `description:` property is rejected by the parser. Other comments are allowed only inside DAX and M expressions.

### Consequences

- Good, because every model change is a reviewable diff, and the conventions are tested on each pull request.
- Good, because the model is 47 MB in memory (from 397 MB before the optimization pass); see [docs/performance/semantic-model.md](../performance/semantic-model.md).
- Good, because the refresh runs as a service user that can only read the reporting schemas.
- Bad, because the service principal cannot run DAX queries on a model with RLS (Execute Queries API limitation), so automated post-refresh checks wait for Phase 7.
- Bad, because the 2-year rolling window drops the oldest year from `Viewing Sessions` on each 1 January (the launch months of 2024 go on 1 January 2027), while the other tables keep all history.
- Bad, because a market user can see the campaign names of other markets in a slicer, without data behind them (see below).
- Bad, because BPA needs Windows and runs only locally.

### Confirmation

- `tests/powerbi/test_tmdl_conventions.py` (descriptions, format strings, display folders, comments, name clashes, implicit summarization, financial columns secured, Market role scope, Polish captions, field parameters, host placeholder) and `tests/powerbi/test_connection.py` in the `pytest` CI job.
- `uv run python semantic/powerbi/run_bpa.py`: 0 violations.
- Reconciliation of 13 numbers between Snowflake and the model (`reconciliation.json`): all equal.
- RLS tested with "View as" for `de.analyst` and `nordics.manager` against per-market numbers from Snowflake; an unmapped user sees no data. OLS tested as `Content Analyst`.
- The service principal refreshes the published model through the REST API (`powerbi refresh`, `powerbi wait`).

## Lessons from the Build

- **Campaign filter in the Market role.** The first version also filtered `Campaign` by market. That filter reached Customer and removed every customer without a campaign (organic and referral), so market users saw about 59% of sessions. The owner found it with "View as"; a test now checks that the role filters only Market and the mapping table.
- **Names are case-insensitive.** A column `trialists` next to the measure `Trialists` stopped Desktop from loading the model. A test checks that measure names differ from all column names.
- **Desktop defaults.** Desktop turns on auto date/time and resets `summarizeBy` to sum on numeric columns unless `SummarizationSetBy = User` is set. Both are now covered by a BPA rule or a test.

## More Information

- [semantic/powerbi/README.md](../../semantic/powerbi/README.md): open, refresh, publish, test RLS, run BPA, measure.
- [docs/standards/semantic-model.md](../standards/semantic-model.md): TMDL and DAX conventions.
- [ADR-002](002-logic-split-between-dbt-and-power-bi.md) (logic split), [ADR-008](008-power-bi-and-fabric-licensing.md) (licensing), [ADR-010](010-orchestration-with-airflow.md) (refresh from Airflow).
- Phase 7 options for the post-refresh checks: a capacity with the XMLA endpoint and an effective user, or a service account (user identity) for Execute Queries.

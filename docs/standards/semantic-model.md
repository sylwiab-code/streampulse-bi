# Semantic Model Standard (TMDL and DAX)

Conventions for the Power BI semantic model in [`semantic/powerbi/`](../../semantic/powerbi/README.md). The design decisions behind them are in [ADR-011](../adr/011-power-bi-semantic-model.md); the split of logic between dbt and DAX is in [ADR-002](../adr/002-logic-split-between-dbt-and-power-bi.md). Items marked **(tested)** are checked by `tests/powerbi/test_tmdl_conventions.py` on every pull request; items marked **(BPA)** by `run_bpa.py`.

## TMDL

- `///` directly above a declaration is that object's description. Every table, column, measure, and calculation item has one **(tested)**. The `description:` property is not accepted by the TMDL parser.
- No other comments outside expressions: `//` is allowed only inside DAX and M **(tested)**.
- Power BI Desktop's save format is canonical (tabs, lineage tags, a blank line at the end of each file). After editing TMDL as text, open the project in Desktop and save it once.
- The Snowflake host is the placeholder `ACCOUNT.snowflakecomputing.com` in Git **(tested)**; `connection.py` sets it locally.
- Auto date/time is off **(BPA)**; the `Date` table is the only calendar.

## Names

- Visible objects have business names in English with spaces and title case: `Active Subscribers`, `'Plan'[Billing Period]`. Amounts name their currency: `MRR (EUR)`, `MRR (Local Currency)`.
- Hidden keys and measure inputs keep the dbt column name in lowercase (`customer_id`, `active_subscribers`), so a hidden name always points at its source column.
- A measure name never equals a column name in any table, ignoring case: Power BI compares names case-insensitively, and Desktop refuses to load such a model **(tested)**.
- Tables are named after the business process or entity, not the dbt model: `Viewing Sessions`, not `fct_viewing_sessions`.

## Columns

- `summarizeBy: none` with the annotation `SummarizationSetBy = User` on every column, so that Desktop does not turn numeric columns back into implicit sums **(tested)**. Implicit measures are off for the model.
- Hidden columns that are not attributes (keys, measure inputs) have `isAvailableInMdx: false`, unless they are a sort-by target.
- Load only the columns that a relationship, measure, filter, or visual uses. High-cardinality columns that are not needed (ids, timestamps) are left out; they dominate memory ([performance report](../performance/semantic-model.md)).
- Dates are `yyyy-mm-dd`, months `mmm yyyy`, years `0`.

## Measures

- Every measure has a description, a format string or a format string expression **(tested)**, and visible measures a display folder **(tested)**: Subscribers, Revenue, MRR Movements, Churn, Trials, Retention, Acquisition, Payments, Engagement, and `Local Views\<market>` for local extensions.
- Formats: whole numbers `#,0`; EUR `\€#,0`; percentages `#,0.0%;-#,0.0%;#,0.0%`; local currency through a format string expression with the currency code.
- Ratios are recomputed from their components at the grain of the query, with `DIVIDE`: never an average of a pre-calculated ratio (ADR-002).
- Snapshot KPIs (active subscribers, MRR, ARR) take the last day of the selected period, capped at the last loaded day, and return blank for periods after it.
- Time intelligence comes from the `Time Intelligence` calculation group (Current, MTD, QTD, YTD, PY, YoY, YoY %), not from separate measures per KPI.
- Quote table names that are DAX keywords: `'Content'[Title]`, `'Date'[Date]`.

## Relationships

- One filter path from each fact to each dimension; single direction **(BPA)**; one-to-many from the dimension.
- KPI tables at market grain relate to Market (and Plan, Channel, Campaign) directly. Customer-level facts (MRR Movements, Payments, Viewing Sessions) reach Market, Channel, and Campaign only through Customer, and Campaign is not related to Market or Channel.

## Security

- **RLS** filters only the `Market` table and the user's own rows of `Security Market Access` **(tested)**. A filter on another dimension also removes every fact row related to that dimension's blank member (a Campaign filter removed all customers without a campaign).
- **OLS:** every financial column (names ending in `_eur` or `_local`, or starting with `mrr_`) has `columnPermission none` in the `Content Analyst` role **(tested, BPA)**.
- Roles have no members in Git; members are assigned in the service. The mapping seed uses fictional `*.example` addresses.
- Test every RLS change with "View as" for a mapped user, an unmapped user, and a user with several markets ([README](../../semantic/powerbi/README.md#test-row-level-and-object-level-security)).

## Translations and Perspectives

- Every visible table, column, and measure has a `pl-PL` caption **(tested)**; display folders are translated too.
- Perspectives (`Executive`, `Content`) only narrow the field list; they are not a security feature.

## Accepted BPA Exceptions

| Object | Rule | Reason |
|---|---|---|
| Model | `DATECOLUMN_FORMATSTRING`, `MONTHCOLUMN_FORMATSTRING` | The project uses ISO dates (`yyyy-mm-dd`) and `mmm yyyy`, not the rules' US formats |
| Model | `INTEGER_FORMATTING` | Years and codes must not show thousand separators |
| Model | `RELATIONSHIP_COLUMNS_SHOULD_BE_OF_INTEGER_DATA_TYPE` | Market and channel keys are the dbt codes; those dimensions have fewer than ten rows, and the dates relate on `dateTime` |
| Model | `REMOVE_ROLES_WITH_NO_MEMBERS` | Members are assigned in the service, not in Git |
| `Security Market Access` | `ENSURE_TABLES_HAVE_RELATIONSHIPS` | Read only by the RLS filter |
| `Customer` | `SNOWFLAKE_SCHEMA_ARCHITECTURE` | Customer attributes reach the facts through Customer, one filter path each |
| `KPI Selector`, `Dimension Selector` | `ENSURE_TABLES_HAVE_RELATIONSHIPS`, `REDUCE_USAGE_OF_CALCULATED_TABLES`, `DAX_MEASURES_UNQUALIFIED` | Field parameters are calculated tables with `NAMEOF` references, by design |
| Their `Fields` columns | `UNNECESSARY_COLUMNS`, `ISAVAILABLEINMDX_FALSE_NONATTRIBUTE_COLUMNS` | Used by Power BI to switch fields |
| `Executive` perspective | `PERSPECTIVES_WITH_NO_OBJECTS` | False positive in Tabular Editor 2 for a perspective that includes all objects |

A new exception needs a row here and a `BestPracticeAnalyzer_IgnoreRules` annotation on the object.

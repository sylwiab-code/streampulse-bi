# StreamPulse — End-to-End BI Portfolio Project

## 1. Purpose

Demonstrate senior-level BI engineering across the full stack: data generation, Snowflake, dbt, Airflow, Power BI, Microsoft Fabric, CI/CD, automated testing, monitoring, and safe AI-assisted development with MCP.

The project is built for a role in media / telecom / subscription businesses. It favors depth of reasoning (documented decisions, measurements, tests) over volume of code.

## 2. Business Scenario

StreamPulse is a fictional subscription video-on-demand (OTT) service operating in several markets (PL, DE, SE, NO).

- **Plans:** Basic / Standard / Premium, monthly and annual billing, free trial.
- **Events:** sign-ups, trials, conversions, upgrades, downgrades, cancellations, failed payments, reactivations, price increases.
- **Engagement:** viewing sessions per title, device, and time of day.
- **Acquisition:** marketing campaigns and channels, with spend.
- **Global vs local:** a central team owns global KPIs. Local markets need extensions such as local currency, local promotions, and local reporting requirements.

### Core KPIs (owned in dbt, consumed in Power BI)

| KPI | Notes |
|---|---|
| Active subscribers | Daily snapshot |
| MRR, ARR | Normalized for annual plans; in EUR and local currency |
| MRR movements | New, expansion, contraction, churn, reactivation |
| ARPU | Per market, plan, cohort |
| Churn rate | Voluntary vs involuntary (failed payment) |
| Trial-to-paid conversion | By channel and campaign |
| Cohort retention | Monthly cohorts, 1–24 months |
| LTV, CAC, LTV/CAC | CAC from marketing spend |
| Watch hours, engagement | Per subscriber, title, genre |
| Content performance | Completion rate, reach |

## 3. Architecture

```
Python data generator (daily batches, late-arriving data, duplicates)
   │  Parquet → Snowflake internal stage
   ▼
Snowflake RAW ◄──── Liquibase (databases, schemas, roles, warehouses, grants,
   │                 stages, file formats, raw tables, masking policies)
   ▼
dbt: staging → intermediate → marts (star schema) → KPI layer
   │  tests: generic, singular, unit, contracts, dbt-expectations
   ▼
Airflow (Astro CLI, Cosmos):
   load → dbt build → Power BI refresh (REST API) → validate → alert
   │
   ├──► Power BI semantic model (PBIP / TMDL), Import mode on Snowflake
   │      RLS per market, OLS, incremental refresh, calculation groups
   │      Reports (PBIR): Executive, Churn, Cohorts, Content, Market
   │
   └──► Microsoft Fabric
          Snowflake mirroring → OneLake → Direct Lake semantic model (variant)
          Lakehouse + notebook for external enrichment files
          Fabric pipeline as alternative orchestration

GitHub Actions: lint → slim CI dbt → Liquibase validate → BPA → tests
                → deploy Dev → Test → Prod (fabric-cicd, environment approvals)

AI layer: Claude Code (CLAUDE.md, hooks), Power BI Modeling MCP server,
          custom StreamPulse MCP server (KPI catalog, lineage, guarded read-only queries)
```

## 4. Requirement Traceability

| Requirement (job posting) | Where it is demonstrated | Phase |
|---|---|---|
| Power BI, Service, semantic models | PBIP model, workspaces, deployment | 5, 6, 7 |
| DAX and model/report optimization | Calculation groups, VertiPaq before/after report | 5 |
| Production PBI incl. security and access | RLS/OLS, workspace access automation, SP auth | 5, 7 |
| SQL, dbt | Full dbt project | 3 |
| Snowflake | Liquibase-managed platform, RBAC, cost control | 2 |
| Dimensional modeling, shared KPIs, reusable models | Marts, KPI layer, KPI catalog | 3 |
| Logic split between data and report layers | ADR-002 and the "add a KPI end-to-end" guide | 3, 11 |
| Independent BI solution design | ADRs, architecture docs | All |
| Git, code review, CI/CD, testing, deployment | GitHub flow, PR reviews, Actions | 0, 7 |
| API, Python, PowerShell | Generator, deployment, tests; PS access management | 1, 7 |
| Fabric: PBI, Semantic Models, Lakehouse, Warehouse, Direct Lake, Pipelines | Fabric variant | 8 |
| Airflow | DAGs with Cosmos | 4 |
| Liquibase | Snowflake change management | 2 |
| AI-assisted development | Documented Claude Code workflow | 10 |
| MCP | Custom MCP server and PBI Modeling MCP | 10 |
| Safe use of AI agents | Guardrails, hooks, read-only role, approvals | 10 |
| Readable reports, data visualization | Report set, theme, design guidelines | 6 |
| Mentoring, knowledge sharing | Standards, onboarding, tutorials | 11 |
| Stakeholder and international collaboration | Global/local KPI design, translations, docs in English | 3, 5 |
| *Nice to have:* PBI deployment automation, Fabric APIs | fabric-cicd, REST API scripts | 7 |
| *Nice to have:* automated tests for data/models | dbt tests, DAX reconciliation tests, BPA | 3, 7 |
| *Nice to have:* media / telco / OTT / subscriptions | Business domain | All |
| *Nice to have:* platform modernization | Import → Direct Lake comparison | 8 |

## 5. Environment and Licensing Options

### Power BI / Fabric (open decision, resolved before Phase 4)

| Option | What you get | Pros | Cons |
|---|---|---|---|
| A. M365 Developer Program E5 sandbox | E5 tenant (incl. Power BI Pro), you are tenant admin | Free | Eligibility now limited (e.g. Visual Studio Pro/Enterprise subscribers); renews every 90 days only with detected dev activity; risk of expiry |
| B. Own tenant (JDG), M365 Business Basic or Entra ID only, plus Power BI Pro, plus Fabric F2 pay-as-you-go | Full control, permanent | Stable, real admin settings, SP, Git integration; F2 can be paused when idle | Monthly cost (Pro license plus F2 hours) |
| C. Fabric trial capacity on A or B | Trial capacity for a limited period | Free Fabric features for the trial window | Time-limited; plan Phase 8 inside the window |
| D. Premium Per User (PPU) | Premium features without capacity | Deployment pipelines, XMLA, larger models | No Fabric items (Lakehouse, Direct Lake) |

**Required regardless of option:** tenant admin rights, a service principal allowed in tenant settings, workspaces Dev/Test/Prod on a capacity (F-SKU or trial) for Fabric items and API deployment.

**Recommendation:** A if eligible, otherwise B. Use C for Phase 8 if it fits.

**Decision gate:** the option must be chosen before Phase 4 starts and recorded in ADR-008. It blocks the Power BI refresh task (Phase 4), the semantic model (Phase 5), deployment (Phase 7: fabric-cicd needs workspaces on a capacity and a service principal), and Phases 8–9. A Fabric trial alone cannot cover Phases 5–9. Phases 0–3 do not depend on it.

### Other services

| Service | Option |
|---|---|
| Snowflake | 30-day trial on Enterprise Edition (start once the generator is ready), then pay-as-you-go Enterprise. Enterprise is required for masking policies (Phase 2, Phase 10). X-Small warehouses, auto-suspend 60s, resource monitors. Verify current trial terms. |
| GitHub | Free. Public repo from day one (ADR-001): rulesets, environment approvals, and secret scanning push protection are free for public repos. Actions minutes and GitHub Pages. |
| Airflow | Astro CLI locally (Docker). No cloud cost. |
| Tabular Editor 2 CLI, PBI Inspector | Free, used in CI. |

### Cost control rules

- Snowflake: auto-suspend, resource monitor with hard quota, X-Small only.
- Fabric F2: pause outside work sessions (automate with an Azure runbook or a script).
- Generator volume: configurable. Default is roughly 50k subscribers and 2 years of history.

## 6. Repository Structure

```
streampulse-bi/
├─ README.md
├─ PLAN.md
├─ CLAUDE.md
├─ data_generator/            Python package (uv), pytest
├─ database/liquibase/        changelogs per object type, per environment properties
├─ transform/dbt/             dbt project
├─ orchestration/airflow/     Astro project, DAGs
├─ semantic/powerbi/          PBIP: *.SemanticModel (TMDL), *.Report (PBIR)
├─ fabric/                    Direct Lake model, notebooks, pipeline definitions
├─ deploy/                    fabric-cicd config, parameter files
├─ tests/                     pytest: DAX reconciliation, API smoke tests
├─ mcp_server/                custom MCP server (Python)
├─ scripts/powershell/        workspace and access management
├─ .github/                   workflows, PR template, CODEOWNERS, issue templates
├─ .claude/                   hooks, settings
└─ docs/
   ├─ adr/                    Architecture Decision Records
   ├─ standards/              SQL, dbt, DAX, TMDL, naming, review checklist
   ├─ guides/                 onboarding, add-a-KPI tutorial, runbooks
   ├─ postmortems/
   ├─ performance/            before/after measurements
   └─ ai-workflow.md
```

## 7. Phases

Each phase ends with a merged PR (or a series of PRs), updated docs, and green CI.

### Phase 0 — Foundations

- Public repo; `main` protected by a repository ruleset stored in `.github/rulesets/` (PR required, status checks, no bypass).
- PR template, review checklist, CODEOWNERS, issue templates, labels.
- Conventional Commits (squash merge, PR title checked in CI); pre-commit with ruff, sqlfluff, yamllint, actionlint, and gitleaks.
- Python toolchain with uv (Python 3.12); `.env.example`; secrets in GitHub Environments only (environments are created in Phase 2, when the first secret exists).
- Initial CI: `ci-lint` (pre-commit, gitleaks history scan, PR title check) and `ci-python` (pytest).
- `CLAUDE.md`, `.claude/` hooks (see Phase 10, minimal version now).
- ADR template; ADR-001 "Overall architecture and tool choices".
- The licensing option (Section 5) is resolved later, before Phase 4.

**DoD:** a PR with a failing lint is blocked; ADR-001 is merged.

### Phase 1 — Synthetic Data Generator

- Entities: customers (PII: name, email), markets, currencies and FX rates, plans and price history, subscriptions, subscription events, payments (including failures and retries), content catalog, viewing sessions, campaigns, campaign spend, acquisition attribution.
- Realistic behavior: seasonality, a price increase event with a churn spike, payment-failure dunning, reactivations, trial abuse, regional differences.
- Data quality defects on purpose: duplicates, late-arriving events, null keys, a schema change mid-history.
- Modes: full history backfill and daily incremental batch. Deterministic with a seed.
- Output: Parquet files on local disk. Uploading them to a Snowflake stage moves to Phase 2, where the stage is created.
- pytest: distributions, referential integrity, determinism.

**DoD:** `generate --days 1` and backfill both work; tests pass in CI.

### Phase 2 — Snowflake Platform with Liquibase

- Environments: `DEV`, `TEST`, `PROD` (databases or database-per-layer per environment; decide in ADR-003).
- Roles: `LOADER`, `TRANSFORMER`, `REPORTER`, `AI_READONLY`, `DEPLOYER`; functional and access role hierarchy.
- Warehouses per workload with auto-suspend; resource monitors.
- Stages, file formats, RAW tables, grants, masking policy on email and name (visible only to privileged roles).
- Loader module (moved from Phase 1): uploads the generated Parquet files to the RAW stage (PUT).
- Service users with key-pair authentication.
- Liquibase: changelog structure, contexts per environment, rollback blocks, `updateSQL` preview.
- ADR-003: "Liquibase for platform objects, dbt for transformations" (where the boundary is and why).

**DoD:** a fresh environment is created from zero with one Liquibase command; masking verified per role.

### Phase 3 — dbt Transformations and KPI Layer

- Sources with freshness checks; staging (cleaning, dedup, type casting, late-arriving handling).
- Intermediate: subscription spells, daily subscription state, MRR movement classification, FX conversion, attribution.
- Marts (star schema):
  - Dimensions: customer, plan, market, date, content, channel, campaign.
  - Facts: `fct_subscription_daily` (periodic snapshot), `fct_mrr_movements`, `fct_payments`, `fct_viewing_sessions`, `fct_campaign_spend`.
  - Cohort model: `fct_cohort_retention`.
- Snapshots: SCD2 for plan prices and customer attributes.
- Incremental models with `merge`, tested late-arriving behavior.
- KPI layer: `kpi_*` models with KPI definitions in YAML `meta` (owner, definition, grain, formula, global/local). This is the source for the KPI catalog.
- Global vs local: global KPI models plus a market extension pattern (for example DE-specific reporting view) without duplicating logic.
- Tests: generic, singular, unit tests (MRR movement logic, churn classification), model contracts on marts, dbt-expectations, source freshness.
- Exposures for Power BI reports.
- dbt docs published to GitHub Pages.
- ADR-002: "Logic split between dbt and Power BI" (what is pre-calculated vs what stays in DAX: time intelligence, ratios at query grain, what-if).

**DoD:** `dbt build` green on DEV; unit tests cover all MRR movement types; docs site live.

### Phase 4 — Orchestration with Airflow

- Astro CLI project; connections via environment variables.
- DAG `daily_pipeline`: generate batch → load to RAW → dbt build (Cosmos, task per model) → trigger Power BI refresh (REST API) → poll status → post-refresh validation → notify.
- DAG `backfill` with parameters; DAG `maintenance` (cleanup of CI schemas, stats).
- Retries, SLAs, failure callbacks (email or Slack webhook), data-aware scheduling.
- DAG tests (import tests, structure tests) in CI.

**DoD:** the full daily pipeline runs end to end locally; a forced failure produces an alert.

### Phase 5 — Power BI Semantic Model (PBIP / TMDL)

- Import mode on Snowflake marts; parameterized connection per environment.
- Minimal, well-named measures on top of pre-calculated KPIs; calculation group for time intelligence; field parameters.
- RLS: dynamic per market via a security mapping table; OLS for financial columns; tested with "View as".
- Incremental refresh on `fct_viewing_sessions`.
- Descriptions on all measures and columns, display folders, perspectives, translations (EN plus one local language) for the "adapt global to local" story.
- Optimization pass: VertiPaq Analyzer before/after, DAX Studio server timings; results in `docs/performance/`.
- Best Practice Analyzer rules file in the repo.

**DoD:** BPA clean (or documented exceptions); RLS tested; performance report written.

### Phase 6 — Reports and Dashboards (PBIR)

- Pages: Executive Overview, Subscriptions and Churn, Cohorts and Retention, Content Engagement, Market Deep Dive.
- Theme JSON and `docs/standards/report-design.md` (layout grid, colors, number formats, accessibility).
- Drillthrough, tooltips, bookmarks only where they add value.
- PBI Inspector rules for report standards.

**DoD:** the reports answer a written list of business questions (in `docs/guides/business-questions.md`).

### Phase 7 — CI/CD, Testing, Deployment Automation

- Auth: GitHub OIDC federated credentials to Entra service principal (no stored secrets where possible); Snowflake key pair in GitHub Environments.
- PR workflows:
  - `ci-python`: pytest (linting runs only in `ci-lint`, via pre-commit).
  - `ci-dbt`: slim CI (`state:modified+`, defer to prod manifest), PR-specific schema, cleanup on close.
  - `ci-liquibase`: validate and `updateSQL` preview posted as a PR comment.
  - `ci-semantic`: Tabular Editor 2 BPA on TMDL, PBI Inspector on reports.
- CD workflow on merge: Liquibase update → dbt build → fabric-cicd deploy to Dev → Test → Prod, with environment approvals; parameter files per environment.
- Post-deploy tests: pytest DAX reconciliation (semantic model totals vs Snowflake via executeQueries API), smoke tests on refresh.
- PowerShell: workspace provisioning and access management (roles assigned from a config file, idempotent).
- Rollback approach documented in a runbook.
- ADR-007: "Deployment strategy" (fabric-cicd vs deployment pipelines).

**DoD:** a change to one measure flows from PR to Prod with tests and approval; reconciliation test catches a planted error.

### Phase 8 — Microsoft Fabric

- Snowflake mirroring into OneLake (or Iceberg tables shared to OneLake; decide in ADR-005).
- Lakehouse with a notebook processing external enrichment files (for example content metadata, ratings).
- Warehouse for a cross-source view (mirrored data plus Lakehouse enrichment).
- Direct Lake semantic model variant, deployed via the same CI/CD.
- Fabric pipeline orchestrating notebook and refresh.
- ADR-004: "Import on Snowflake vs Direct Lake on OneLake" with measured comparison (refresh time, query performance, freshness, cost, fallback behavior).

**DoD:** both model variants deployed; comparison measured and written up.

### Phase 9 — Monitoring and Governance

- Persist dbt run results and test results to Snowflake (dbt artifacts package or Elementary).
- Collect Power BI refresh history and workspace inventory via REST / Scanner API into Snowflake.
- Snowflake cost monitoring (warehouse metering).
- Operations report in Power BI: pipeline health, test failures, refresh durations, costs.

**DoD:** operations report shows the last 30 days of runs, failures, and costs.

### Phase 10 — AI-Assisted Development and MCP

- `docs/ai-workflow.md`: how Claude Code is used, what is delegated, what is always human-decided, examples of rejected AI suggestions and why.
- Claude Code hooks: block commands that target PROD, block committing secrets, require tests to pass before commit.
- Use the Power BI Modeling MCP server for model development; document the review step before applying changes.
- Custom StreamPulse MCP server (Python):
  - `search_kpi_catalog`, `get_kpi_definition` (from dbt manifest `meta`)
  - `get_lineage` (dbt manifest plus exposures)
  - `run_readonly_query` (Snowflake `AI_READONLY` role, SELECT-only validation, row limit, timeout, masked PII)
  - `query_semantic_model` (DAX via executeQueries, read-only, Test workspace only)
  - Audit log of all tool calls.
  - Tests for guardrails (attempted writes, PII access, oversized results).
- Optional agent use case: PR review assistant in GitHub Actions that checks dbt and TMDL changes against `docs/standards/`; it only comments, never approves or merges.
- ADR-006: "Safe use of AI agents" (threat model: prompt injection, data leakage, destructive actions; mitigations).

**DoD:** MCP server works from Claude Code; guardrail tests pass; ADR-006 merged.

### Phase 11 — Standards and Mentoring Materials

- `docs/standards/`: SQL style, dbt conventions, DAX conventions, TMDL conventions, naming, code review checklist.
- `docs/guides/onboarding.md`: "first PR in one hour".
- `docs/guides/add-a-kpi.md`: end-to-end tutorial (dbt model → tests → KPI catalog → semantic model → report → deploy), showing the logic split in practice.
- `CONTRIBUTING.md`.

**DoD:** a person new to the repo could add a KPI by following the guide alone.

### Phase 12 — Showcase

- README: problem, architecture diagram, key decisions (links to ADRs), screenshots, how to run.
- Demo video (5–8 min): pipeline run, PR to Prod, RLS, MCP in action, Direct Lake comparison.
- Case study write-up (`docs/case-study.md`): challenges, trade-offs, measurements, lessons learned.

## 8. Authenticity Guidelines (avoid a "vibe-coded" look)

- Every non-trivial decision gets an ADR with considered alternatives.
- Optimizations are backed by before/after measurements.
- Real issues encountered get a short postmortem.
- Small commits, descriptive PRs, self-review comments on PRs, visible red and green CI runs.
- AI use is documented openly in `docs/ai-workflow.md`, including what was rejected.
- No unused boilerplate: every file in the repo has a reason to exist.

## 9. Risks

| Risk | Mitigation |
|---|---|
| Tenant or license unavailable or expires | Option B as fallback; keep all assets in Git so the tenant can be rebuilt by CI |
| Snowflake trial ends mid-project | Start trial after Phase 1; resource monitor; move to pay-as-you-go Enterprise |
| Fabric trial window too short | Prepare Phase 8 code before starting the trial |
| Licensing not decided in time | Decision gate before Phase 4 (Section 5); Phases 0–3 do not depend on it |
| Secret committed to the public repo | gitleaks in pre-commit and CI, GitHub push protection; if it happens, rotate the secret at once and write a postmortem |
| Scope creep | Each phase has a DoD; extras go to a `backlog` label |
| Cost overrun | Auto-suspend, F2 pause automation, resource monitors |

## 10. ADR Index (planned)

| ADR | Topic |
|---|---|
| 001 | Overall architecture and tool choices |
| 002 | Logic split between dbt and Power BI |
| 003 | Liquibase vs dbt boundary; Snowflake environment layout |
| 004 | Import on Snowflake vs Direct Lake on OneLake |
| 005 | Snowflake to Fabric integration (mirroring vs Iceberg) |
| 006 | Safe use of AI agents |
| 007 | Deployment strategy (fabric-cicd vs deployment pipelines) |
| 008 | Power BI and Fabric licensing |
| 009 | Synthetic data generator design (Phase 1; accepted) |

---
status: accepted
date: 2026-11-12
decision-makers: Sylwia Berent
consulted: Claude Code (AI assistant; proposed options and trade-offs)
---

# ADR-001: Overall architecture and tool choices

## Context and Problem Statement

StreamPulse is a portfolio project that must show senior-level BI engineering for a role in media, telecom, or subscription businesses (`PLAN.md`, sections 1 and 4). Before any code is written, the project needs a fixed stack, a layered architecture, and an engineering workflow (repository, review, linting, CI) that the later phases build on.

Which architecture, tools, and engineering workflow does the project use, and which decisions are deliberately left open?

## Decision Drivers

- **Coverage of the target role:** each requirement in `PLAN.md` section 4 must be demonstrated by a real component.
- **Low and controllable cost:** free tiers where possible; anything billed can be paused or capped.
- **Everything as code:** platform, transformations, semantic model, reports, and repository rules live in Git and are reviewed in PRs.
- **Reproducibility:** a reviewer can clone the repository and understand or rebuild each part.
- **Safe AI-assisted development:** AI tools work inside explicit guardrails and their use is documented.

## Considered Options

Each area below had its own alternatives; they are listed with the decision in the tables of the next section.

## Decision Outcome

The layered architecture in `PLAN.md` section 3 is adopted:

```
Python generator → Parquet → Snowflake RAW (Liquibase)
  → dbt (staging → intermediate → marts → KPI layer)
  → Airflow (Astro CLI, Cosmos) orchestration
  → Power BI semantic model (PBIP, Import) and reports (PBIR)
  → Microsoft Fabric variant (mirroring → OneLake → Direct Lake)
GitHub Actions for CI/CD; Claude Code with guardrails and a custom MCP server
```

### Component choices

| Area | Choice | Alternatives considered | Why this choice |
|---|---|---|---|
| Source data | Python synthetic data generator writing Parquet | Public datasets; Snowflake sample databases | Defects can be planted on purpose (duplicates, late-arriving data, schema change), output is deterministic with a seed, no data licensing issues |
| Data platform | Snowflake, Enterprise Edition | Fabric Warehouse or Lakehouse only; Databricks | Named in the target role. Enterprise Edition is required for masking policies on PII (Phase 2, Phase 10) |
| Platform change management | Liquibase | schemachange; Terraform Snowflake provider | Named in the target role; changelogs per object type with rollback blocks and contexts per environment. The boundary with dbt is decided in ADR-003 |
| Transformations | dbt Core | Snowflake stored procedures or dynamic tables; SQLMesh; dbt Cloud | Named in the target role; tests, contracts, documentation, and lineage in one tool. dbt Core runs inside Airflow (Cosmos) and GitHub Actions without a SaaS licence |
| Orchestration | Airflow via Astro CLI (local Docker) with Cosmos | Dagster; Fabric Data Factory pipelines; scheduled GitHub Actions | Named in the target role; Cosmos turns dbt models into Airflow tasks; no cloud cost. A Fabric pipeline is built as an alternative in Phase 8 |
| Semantic model and reports | Power BI PBIP (TMDL and PBIR), Import mode on Snowflake | `.pbix` files; DirectQuery on Snowflake | PBIP is plain text, so model and report changes are diffable and reviewable in PRs. Import mode keeps report queries off Snowflake warehouses (speed and cost). Direct Lake is compared in ADR-004 |
| Fabric | Variant built next to the Import model | No Fabric component | Named in the target role; the Snowflake-to-Fabric integration is decided in ADR-005 and measured in ADR-004 |
| CI/CD | GitHub Actions | Azure DevOps Pipelines | The repository is on GitHub; Actions minutes are free for public repositories. The Power BI deployment approach is decided in ADR-007 |
| Python tooling | uv, ruff, pytest | pip and venv; Poetry; black and flake8 | uv manages Python versions, environments, and lock files in one fast tool; ruff replaces several linters and the formatter |
| AI-assisted development | Claude Code with project hooks; custom MCP server | No AI tools; AI tools without guardrails | Named in the target role. Guardrails start minimal in Phase 0 and are completed in Phase 10 (ADR-006) |

### Engineering workflow (Phase 0)

| # | Topic | Decision | Alternatives considered | Reason |
|---|---|---|---|---|
| D1 | Repository visibility | Public from day one | Private with GitHub Pro; private on GitHub Free | Rulesets, environment required reviewers (needed in Phase 7), and secret scanning push protection are free for public repositories; the full history, including red CI runs, is visible to reviewers. Nothing secret is ever committed |
| — | Commit identity | GitHub noreply email (repository-local `user.email`) | Personal email | Keeps a personal address out of a public, permanent history |
| — | License | No license file (all rights reserved) | MIT; Apache-2.0 | Owner preference |
| D2 | Protection of `main` | Repository ruleset stored as JSON in `.github/rulesets/` and applied with `gh api`: PR required, 0 approvals, required status checks, no bypass, linear history, no force push | Classic branch protection set in the web UI | Reviewable as code. No bypass means the rules also apply to the repository admin. 0 approvals because a single maintainer cannot approve their own PRs |
| D3 | Merge strategy | Squash merge only; PR title must follow Conventional Commits (checked in CI) | Rebase merge with every commit checked; merge commits | One conventional entry per PR on `main`; the individual small commits stay visible in the PR |
| D4 | Python version | 3.12 for local, CI, and containers | 3.13; 3.14 | Broadest support across dbt, Astro Runtime, Cosmos, and the Snowflake connector. Re-checked against the Astro Runtime image in Phase 4 |
| D5 | Hook runner | pre-commit with hook versions pinned by `rev`; CI runs the same configuration | pre-commit with local hooks calling `uv run`; prek | One source of truth for tool versions, locally and in CI; widely known |
| D6 | Hook set | ruff (lint and format), sqlfluff, yamllint, gitleaks, actionlint, basic hygiene hooks, no commits to `main` | Only the hooks named in PLAN.md; additionally markdownlint and codespell | actionlint catches workflow errors before CI runs; markdownlint would add a Node.js dependency and noise |
| D7 | SQL linting | sqlfluff, Snowflake dialect, jinja templater, limited to `transform/` and `database/` | dbt templater, introduced in Phase 3 | Runs without a database connection or secrets, also in CI. The templater is revisited in Phase 3 |
| D8 | Secret scanning | gitleaks in pre-commit and as a full-history scan in CI, plus GitHub secret scanning with push protection | detect-secrets; TruffleHog | Fast, low noise, no baseline file to maintain |
| D9 | Phase 0 CI | `ci-lint` (pre-commit, gitleaks history scan, PR title check) and `ci-python` (pytest) | Lint only; additionally Dependabot and CodeQL | Meets the Phase 0 Definition of Done and tests the only code in Phase 0 (Claude Code hooks). Dependabot is reconsidered in Phase 1, when runtime dependencies exist |
| D10 | Claude Code guardrails | `permissions.deny` rules plus a `PreToolUse` guard in Python, covered by pytest | Deny rules only; additionally a hook that runs tests before each commit | The guard is testable now. Running tests before commits belongs to Phase 10 and overlaps with pre-commit |
| D11 | ADR format | MADR, files named `docs/adr/NNN-slug.md` | Nygard short form | MADR has a "considered options" section, which `PLAN.md` section 8 requires for every non-trivial decision |
| — | Line endings | `.gitattributes` with `* text=auto eol=lf` | Rely on each machine's `core.autocrlf` | Identical bytes on Windows, Linux CI runners, and in linters |
| — | Bootstrap | The first commit (`PLAN.md`, `CLAUDE.md`, `.gitignore`, `.gitattributes`) was pushed directly to `main` | — | A branch needs a base commit. This is the only direct commit to `main`; all later changes go through PRs |

### Deferred decisions

| Decision | Deadline | Recorded in |
|---|---|---|
| Power BI and Fabric licensing (`PLAN.md` section 5, options A–D) | Before Phase 4 starts. It blocks the Power BI refresh task (Phase 4), the semantic model (Phase 5), deployment (Phase 7), and Phases 8–9 | ADR-008 |
| Python project layout (one uv workspace or separate projects per component) | Phase 1 | Phase 1 PR; ADR if the choice is contested |
| Snowflake environment layout; Liquibase and dbt boundary | Phase 2 | ADR-003 |
| Logic split between dbt and Power BI | Phase 3 | ADR-002 |

### Consequences

- Good, because every component maps to a requirement of the target role and has a stated alternative.
- Good, because repository rules, linting, and secret scanning are enforced from the first PR, at no cost.
- Good, because Phases 1–3 do not depend on the open licensing decision.
- Bad, because the repository is public while it is incomplete; work in progress and mistakes are visible.
- Bad, because a single maintainer cannot get an independent review; self-review comments on PRs are used instead.
- Bad, because Snowflake Enterprise Edition costs more per credit than Standard after the trial.

### Confirmation

- The ruleset JSON in `.github/rulesets/` matches the live ruleset (`gh api repos/sylwiab-code/streampulse-bi/rulesets`).
- A PR with a lint error is blocked from merging (Phase 0 Definition of Done; demonstrated by a dedicated, unmerged PR).
- `ci-lint` and `ci-python` are required status checks on `main`.

## More Information

- `PLAN.md`: section 3 (architecture), section 4 (requirement traceability), section 5 (environment and licensing), section 10 (planned ADRs).
- [`docs/ai-workflow.md`](../ai-workflow.md): AI suggestions that were rejected during this decision.

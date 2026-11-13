# AI-Assisted Workflow

Claude Code proposes options and implements; Sylwia Berent decides (see `CLAUDE.md`, section Roles). This document grows with the project: the guardrails are added in Phase 0 and the full workflow description in Phase 10.

## Guardrails

The shared settings in `.claude/settings.json` add two guardrails (ADR-001, D10). Phase 10 extends them.

- **Deny rules:** Claude Code may not read `.env` files or private keys (`*.p8`, `*.pem`, `*.key`). The rules also cover shell file commands such as `cat`.
- **Command guard:** `.claude/hooks/guard_command.py` checks every Bash and PowerShell command before it runs and blocks:
  - data tool commands (dbt, snow, liquibase, uv, python, and others) or environment variables that mention PROD;
  - skipping git hooks with `--no-verify`;
  - force pushes and pushes to `main`;
  - Liquibase changes without an explicit DEV target, and Liquibase `drop-all`.

  Claude sees the reason for a blocked command and asks the user. The tests in `tests/claude_hooks/` run in the `ci-python` workflow.

These guardrails catch mistakes; they are not a security boundary, because string checks can be bypassed. The protection that matters is structural: no PROD credentials on developer machines, Snowflake roles such as `AI_READONLY` (Phase 2), and the ruleset on `main`.

## Rejected or Changed AI Suggestions

Notable suggestions from Claude Code that were rejected or significantly changed, with the reason.

| Date | Phase | AI suggestion | Decision | Reason |
|---|---|---|---|---|
| 2026-11-12 | 0 | Keep the repository private on GitHub Pro and make it public before Phase 7 | Public from day one | Rulesets, environment approvals, and push protection are free on public repositories, and the full history stays visible. See [ADR-001](adr/001-overall-architecture-and-tool-choices.md), D1 |
| 2026-11-12 | 0 | Add an MIT license in the first commit | No license file (all rights reserved) | Owner preference |
| 2026-11-13 | 0 | A separate PR for the blocked-lint demo, a postmortem for the skipped history scan (fixed in #5), and separate approvals for each diff and each merge | One review stop per PR; the demo is a step in the governance PR; no postmortem | The overhead did not match the value for a one-person project |

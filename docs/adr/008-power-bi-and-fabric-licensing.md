---
status: accepted
date: 2026-11-16
decision-makers: Sylwia Berent
consulted: Claude Code (AI assistant; summarized current Microsoft trial terms)
---

# ADR-008: Power BI Pro trial and Fabric trial capacity on an own tenant, started with Phase 5

## Context and Problem Statement

Phases 4-9 need a Power BI tenant: the refresh task (Phase 4), the semantic model and reports (Phases 5-6), deployment with a service principal (Phase 7), and Fabric items (Phases 8-9). PLAN.md section 5 lists four options and requires a decision before Phase 4.

## Decision Drivers

- No or minimal cost for a portfolio project.
- Tenant admin rights (service principal, tenant settings, workspaces on a capacity).
- The trial clocks should cover the phases that actually need them.

## Considered Options

1. M365 Developer Program E5 sandbox
2. Own tenant with paid Power BI Pro and Fabric F2 pay-as-you-go
3. Fabric trial capacity (with a Power BI Pro trial) on an own tenant
4. Premium Per User

## Decision Outcome

Chosen option: 3, an own tenant with a **Power BI Pro trial and a Fabric trial capacity**, because it costs nothing and gives tenant admin rights and Fabric items.

Current terms (Microsoft Learn, checked 2026-11-15):

- Power BI and Fabric require a work or school account; consumer email cannot sign up. The recommended route is a Microsoft 365 trial, which creates a new tenant and makes the creator its admin (credit card required; cancel within the trial period to avoid charges). Business Premium includes Power BI Pro.
- The Fabric trial lasts **60 days**, cannot be extended self-service, and another trial is not guaranteed. It runs on F4 or F64 (choose F64 if offered) and includes a Power BI individual trial similar to Premium Per User. When it ends, workspaces fall back to Pro, Fabric items become inactive, and Fabric data is kept for 7 days.
- Service principal and REST API support on trial capacity is not documented; it is verified first in Phase 5.

**Timing:** Phase 4 is built without the trials; its Power BI tasks are implemented against a simulated API and switched off. The trials start when Phase 5 begins, so Phases 5-9 get the full 60 days.

### Consequences

- Good, because there is no cost and full admin control.
- Bad, because Phases 5-9 must fit into 60 days, or the Fabric work continues on paid capacity.
- Bad, because a trial capacity is meant for evaluation, not production; acceptable for a portfolio.

### Confirmation

Phase 5 starts by checking that a service principal can refresh a semantic model through the REST API on the trial capacity.

## More Information

- Open follow-up, decided before day 60: buy Fabric F2 pay-as-you-go (pausable) to finish Phases 8-9, or let the Fabric items lapse and keep the PBIP files in Git plus screenshots.
- PLAN.md section 5 (licensing options).

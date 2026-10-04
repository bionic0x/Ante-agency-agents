# Phase 3 — Build, Validate & Learn

> **Status:** execution module subordinate to `strategy/STRATEGIC-CONTROL-PLANE.md`.

## Function

Implement the current bounded design while continuously testing whether the implementation, architecture, and underlying thesis remain valid.

Build is not where strategy stops. Production of code/content/artifacts generates new evidence that may require a return to discovery, architecture, or the governing object.

## Governing question

> Are we converting resources into the intended capability/effect, and can we detect failure of the mechanism before committing the remaining reserve?

## Entry conditions

- current strategic output permits the relevant implementation work;
- foundation is sufficient for the intended slice;
- acceptance criteria and authoritative constraints are available;
- material unknowns/risks that block implementation are resolved or explicitly accepted;
- validation and evidence paths exist.

## Main effort

The Orchestrator names one main effort for the iteration and limits parallel work accordingly.

Parallel tracks are useful only when they do not compete for an unresolved dependency or create incompatible decisions.

## Core loop

```text
bounded task / hypothesis
        │
        ▼
     implement
        │
        ▼
 independently validate
        │
   ┌────┴─────┐
   │          │
 evidence   failure / contradiction
   │          │
   ▼          ▼
 update     classify defect
 claims     execution / design / orientation
   │          │
   └────┬─────┘
        ▼
 continue / condition / hold / redesign / stop
```

### Validation outcomes

A technical validation uses `PASS`, `FAIL`, or `NOT_TESTED` for explicit criteria.

A material strategic gate still uses:

- `PROCEED`
- `PROCEED_WITH_CONDITIONS`
- `HOLD`
- `REDESIGN`
- `REJECT`

Do not confuse technical PASS with strategic permission.

## Retry / experiment budget

There is no universal three-attempt rule.

Set the budget from:

- cost per attempt;
- reversibility;
- learning generated;
- time window;
- risk of repeated failure;
- reserve consumed;
- external/user impact.

Repeated failure that no longer generates discriminating evidence is an escalation trigger, not an invitation to repeat the same method.

## Defect classification

When work fails, classify the failure before choosing another attempt:

### Execution defect
The design remains plausible; implementation deviated from it.

### Design defect
Implementation followed the design, but architecture/specification cannot satisfy the intended requirement or constraints.

### Orientation defect
The requirement/design may be executed correctly, but the causal thesis, user problem, priority, or governing object is wrong or materially incomplete.

The correction level must match the defect level.

## Evidence discipline

For every material increment record:

- what was implemented;
- which criterion/hypothesis it tests;
- observed result;
- evidence reference;
- claim-state changes;
- limitations / NOT_TESTED surfaces;
- new dependency or operational burden;
- reserve consumed.

## Scope control

Do not add “nice to have” work merely because implementation exposes an opportunity.

A scope expansion requires one of:

- it is necessary for the current governing object and authorized within the existing record;
- it is a reversible experiment explicitly approved inside the current bounds;
- the Strategic Decision Record is updated and the new commitment passes the relevant gate.

## Build-time review triggers

Return to strategic review when:

- the falsifier triggers;
- a critical dependency is not available or behaves differently than assumed;
- project-specific safety/compliance constraints cannot be met;
- implementation changes the authority or data perimeter;
- repeated defects indicate a design/orientation problem;
- the main effort no longer appears decisive;
- reserve consumption makes the remaining course fragile;
- user/system reaction changes the causal model;
- the culmination condition is reached.

## Gate

At a material build boundary, review:

- evidence supports the required capability/effect;
- material acceptance criteria are tested in the relevant environment;
- NOT_TESTED areas are visible and owned;
- unresolved defects are classified correctly;
- no summary upgrades a hypothesis to evidence without support;
- rollback and migration implications are known;
- remaining work still contributes to the governing object;
- the next commitment remains inside authority and reserve.

## Exit condition

This module is complete for the current release/experiment when:

- the bounded intended capability exists;
- evidence is sufficient for the next decision;
- unresolved limitations are explicit;
- hardening/release work is scoped by risk rather than ritual;
- the strategic output permits progression.

## Handoff

Use the v2 handoff templates and carry:

- Strategic Context Header;
- implementation refs/commits;
- validation evidence;
- claim-register updates;
- NOT_TESTED areas;
- known defects/debt;
- rollback/recovery notes;
- assumption/falsifier status;
- reserve state;
- recommended next decision.

> **Completion criterion:** the team has produced not only working output but decision-grade evidence about whether the current design and thesis deserve the next commitment.

# Phase 4 — Hardening & Independent Verification

> **Status:** execution module subordinate to `strategy/STRATEGIC-CONTROL-PLANE.md`.

## Function

Challenge the release/commitment under conditions proportionate to its real impact and verify that the evidence supports the claims being made.

Hardening is not a ritual “quality gauntlet,” and the Reality Checker is not a sovereign release authority. Independent validators produce evidence and findings; Strategic Assurance tests coherence; the authorized decision owner controls the commitment.

## Governing question

> What could still make this apparently successful implementation fail the governing object when exposed to realistic conditions?

## Entry conditions

- a bounded implementation or release candidate exists;
- material acceptance criteria and claims are explicit;
- risk/impact and deployment context are known enough to select appropriate tests;
- rollback/recovery expectations are explicit;
- current strategic output permits verification work.

## Verification posture

Independent review should be skeptical but not pre-committed to failure.

The burden of evidence grows with:

- irreversibility;
- blast radius;
- security/privacy/legal exposure;
- dependence on uncertain assumptions;
- external/public claims;
- concentration of critical dependencies;
- difficulty of recovery.

“Overwhelming evidence” is not a universal standard. **Decision-appropriate evidence** is.

## Candidate validators

| Risk / claim | Candidate function |
|---|---|
| acceptance / user-visible behavior | Evidence Collector, UX/design reviewer |
| API / integration correctness | API Tester |
| performance / capacity | Performance Benchmarker |
| security | security specialist / auditor |
| compliance | Legal Compliance Checker |
| data/model quality | Test Results Analyzer, AI/data specialist |
| workflow/reliability | Workflow Optimizer, Infrastructure Maintainer |
| claim integrity | Reality Checker, Proposition Citation Auditor |
| strategic coherence | Strategic Assurance Lead |

Use only applicable validators.

## Protocol

### 1. Build a risk-to-test map

```yaml
risk_or_claim: ""
materiality: ""
evidence_needed: ""
test_or_review: ""
environment: ""
pass_condition: ""
not_tested_condition: ""
owner: ""
```

### 2. Test the environment that matters

Do not claim production readiness from a test that omits the production condition responsible for the risk.

Where production-like testing is impossible, state the gap as `NOT_TESTED` or `ASSUMPTION`; do not silently infer equivalence.

### 3. Challenge the claims

For each material release claim, Reality Checker or an equivalent independent function should classify it as:

- `VERIFIED`
- `NOT_VERIFIED`
- `CONTRADICTED`
- `NOT_TESTED`

This classification updates the Claim Register; it does not independently authorize launch.

### 4. Test reversal and recovery

When material, verify:

- rollback or safe-state procedure;
- dependency failure behavior;
- degraded-mode behavior;
- data/integrity recovery;
- alerting/escalation path;
- authority needed to execute recovery.

### 5. Preserve dissent

A minority technical finding survives synthesis when material. It is recorded with evidence and the owner who accepts residual risk.

## Gate

Apply the seven coherence tests to the proposed release/commitment.

A technical test result and a strategic output are separate layers.

Example:

```text
API validation: PASS
Performance claim: NOT VERIFIED
Security review: PASS WITH LIMITATIONS
Strategic output: PROCEED_WITH_CONDITIONS
Decision-owner condition: staged release only; performance claim may not be published
```

## Release finding classes

- `FATAL_DEFECT` — necessary condition fails; cannot proceed as proposed.
- `ACCEPTED_RISK` — bounded residual risk explicitly owned within authority.
- `PENDING_EVIDENCE` — commitment waits or is narrowed until evidence is obtained.

## Exit condition

Hardening is complete for the current commitment when:

- material claims are verified, bounded, or explicitly not made;
- material risk surfaces are tested or visibly accepted as gaps;
- fatal defects are resolved or the plan is redesigned/rejected;
- recovery/rollback is proportionate and owned;
- the decision owner has the evidence needed for the next commitment;
- Strategic Assurance has issued the current bounded output.

## Handoff

Carry forward:

- Strategic Context Header;
- release/evidence bundle;
- verified and non-verified claims;
- NOT_TESTED surfaces;
- residual risks and owner;
- rollback/recovery evidence;
- launch/commitment conditions;
- termination/culmination triggers.

> **Completion criterion:** the organization knows what has actually been demonstrated, what has not, and what risk it is consciously carrying into the next commitment.

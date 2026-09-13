# Phase 2 — Foundation & Scaffolding

> **Status:** execution module subordinate to `strategy/STRATEGIC-CONTROL-PLANE.md`.

## Function

Create the minimum technical and operational foundation required for the current main effort to be built, tested, observed, and safely changed.

Foundation is not a contest to maximize infrastructure completeness. Overbuilding the platform before the thesis is tested consumes reserve and creates path dependency.

## Governing question

> What must exist before implementation can proceed without hiding critical dependency, security, evidence, or rollback risk?

## Entry conditions

- current strategic output permits foundation work;
- material architecture decisions are explicit enough for the bounded commitment;
- project-specific security/compliance constraints are available or gated;
- unresolved choices that would invalidate scaffolding are visible.

## Candidate workstreams

| Need | Candidate agents | Typical output |
|---|---|---|
| CI/CD / environment | DevOps Automator | reproducible build/deploy path |
| application skeleton | Frontend Developer, Backend Architect | minimum executable structure |
| data / auth foundation | Backend Architect, security specialist | scoped schema and access controls |
| design implementation | UX Architect, Frontend Developer | required tokens/components/layout foundation |
| observability | Infrastructure Maintainer, Analytics Reporter | logs/metrics/traces needed for decisions |
| process / collaboration | Studio Operations, Project Manager | workflow only where coordination requires it |
| independent verification | Evidence Collector, relevant tester | proof that foundation supports the intended thin slice |

No fixed agent count is required.

## Protocol

### 1. Build for the first bounded vertical slice

Prefer a foundation that can support the first meaningful end-to-end test over a generalized platform for hypothetical future needs.

### 2. Make dependencies explicit

Record:

- external services;
- versions/interfaces relied on;
- source of truth;
- authentication/authorization boundary;
- secret/key ownership;
- data retention assumptions;
- operational owner;
- recovery/fallback path.

### 3. Instrument the claims that matter

Observability should answer decision-relevant questions. Do not collect telemetry simply because it is available.

At minimum for material systems, determine what evidence is needed to establish:

- the critical path works;
- failures are detectable;
- rollback/recovery works to the declared standard;
- relevant security/compliance conditions hold;
- the next phase can test its causal/quality claims.

### 4. Preserve reversible choices

Do not commit to a more complex platform merely because it is fashionable or theoretically scalable. Where uncertainty is high, use interfaces and staging that keep substitution possible.

### 5. Do not automate away required human control

Human approval, dual control, legal review, manual recovery, or safety checks may be deliberate parts of the system. Automation must respect the authority model.

## Foundation evidence package

Applicable evidence may include:

- reproducible environment/build instructions;
- CI results;
- deployment to an authorized non-production environment;
- thin-slice execution evidence;
- authentication/authorization tests;
- schema/migration evidence;
- observability screenshots/log refs;
- recovery/rollback test;
- known limitations and deferred foundation work;
- updated Claim Register.

## Gate

The gate asks whether the foundation is **sufficient for the next bounded commitment**, not whether every future platform concern is solved.

Review:

- critical dependencies are named and owned;
- required security/compliance controls exist or are explicitly gated;
- build/test/deploy path is reproducible enough for the use case;
- the first meaningful slice can be observed;
- material failure has a safe state or recovery path;
- deferred foundation debt cannot silently invalidate the next step;
- reserve has not been consumed by speculative infrastructure.

Strategic output remains `PROCEED`, `PROCEED_WITH_CONDITIONS`, `HOLD`, `REDESIGN`, or `REJECT` as appropriate.

## Exit condition

Foundation work is complete for the current commitment when implementation can proceed without inventing missing critical controls or hiding an unowned dependency.

It may be revisited later. “Done for this commitment” is not “finished forever.”

## Handoff

Carry forward:

- Strategic Context Header;
- architecture references;
- environment/deploy instructions;
- authoritative project-specific targets;
- source-of-truth and access model;
- observability/evidence plan;
- known foundation debt;
- rollback/recovery path;
- open conditions before production or other irreversible action.

> **Completion criterion:** the next team can build and learn safely on a foundation proportionate to the actual commitment.

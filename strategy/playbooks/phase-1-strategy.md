# Phase 1 — Strategy Translation & Architecture

> **Status:** execution module subordinate to `strategy/STRATEGIC-CONTROL-PLANE.md`.

## Function

Translate a sufficiently coherent strategic decision into an implementable product, system, operating, and resource design without letting architecture or roadmap mechanics replace the governing object.

This module does not create the strategy by assembling slides. It converts the current strategic intent into choices that engineers, designers, operators, finance, security, and product specialists can execute and test.

## Governing question

> What architecture, scope, resource allocation, and operating constraints are sufficient to test or deliver the current strategic thesis while preserving options?

## Entry conditions

- a Strategic Decision Record exists;
- the current output permits architecture/design work;
- governing object, non-object, minimum sufficient result, and decision owner are explicit;
- decision-critical discovery unknowns are either reduced or explicitly accepted;
- hard legal/security/organizational constraints are visible.

A project may enter this module without completing every possible discovery activity.

## Main workstreams

Activate only those required by the decision.

| Workstream | Candidate agents | Decision-relevant output |
|---|---|---|
| strategic/product translation | Business Strategist, Product Manager, Studio Producer | product/system choices and explicit tradeoffs |
| task/dependency design | Senior Project Manager, Project Shepherd | executable dependency map and gates |
| UX / interaction architecture | UX Architect, UX Researcher | user-flow and interface architecture tied to evidence |
| system architecture | Backend Architect, Senior Developer, domain engineering specialist | technical architecture, boundaries, failure modes |
| AI/ML architecture | AI Engineer | model/data/inference design only where justified |
| financial/resource design | Finance Tracker | cost model, resource constraints, reserves |
| brand/message constraints | Brand Guardian | brand system where it affects the objective |
| independent challenge | Reality Checker, Strategic Assurance Lead | evidence challenge and coherence result |

## Protocol

### 1. Trace every major design choice to the strategic record

For material choices, record:

```yaml
decision: ""
governing_object_link: ""
requirement_or_evidence: ""
options_considered: []
chosen_option: ""
tradeoff: ""
assumptions: []
rollback_or_substitute: ""
review_trigger: ""
```

### 2. Distinguish requirement from proposal

Do not promote generic best practices into mandatory requirements without context.

Examples of values that require an authoritative source or explicit project decision:

- availability/SLO targets;
- latency targets;
- accessibility standard/version;
- model accuracy/fairness thresholds;
- scale assumptions;
- budget/ROI targets;
- specific architecture patterns;
- sprint velocity;
- release date.

If absent, mark the value `UNKNOWN` or propose a target with rationale.

### 3. Architecture must expose friction

A useful architecture identifies:

- critical dependencies;
- external services and failure modes;
- source-of-truth ownership;
- authority boundaries;
- rollback/safe states;
- observability needed to verify claims;
- maintenance burden;
- concentration/single-point risk;
- what must remain human-controlled.

### 4. Prioritize by causal contribution

RICE, MoSCoW, cost-of-delay, or another scoring method may be used as tools. They do not become the strategy.

The prioritized plan must state:

- the main effort;
- what receives minimum sufficient coverage;
- what is deferred or refused;
- reserve preserved;
- what evidence would reorder the backlog.

### 5. Preserve architectural alternatives where uncertainty is material

When a decision is expensive to reverse and evidence is weak, prefer bounded prototypes, interfaces, or staged commitments that preserve options where practical.

## Architecture package

The package contains only applicable artifacts, typically:

1. strategic/product translation and scope boundaries;
2. system/dependency architecture;
3. UX/interaction architecture;
4. data and source-of-truth model;
5. security/compliance constraints;
6. financial/resource model;
7. implementation task/dependency map;
8. evidence/observability plan;
9. rollback and transition assumptions;
10. updated Claim Register and Strategic Decision Record.

## Gate

There is no universal requirement for “100% of the spec” if the governing decision is a bounded experiment; equally, a material mandatory requirement cannot be omitted because the MVP is small.

Review instead:

| Test | Evidence expected |
|---|---|
| governing-object | architecture and scope trace to the valuable result |
| causal | system can generate the mechanism/evidence the thesis requires |
| interactive | foreseeable user/system/adversarial responses are represented |
| conversion | resources, dependencies, and authority can make the architecture real |
| legitimacy | applicable stakeholder, legal, security, and governance constraints are preserved |
| epistemic | assumptions and unknowns remain visible |
| exit | rollback, redesign, migration, or termination path exists |

Strategic Assurance returns the bounded output. Reality Checker or specialist validators provide evidence; they are not sole strategic authorities.

## Exit condition

This module is complete for the next bounded commitment when:

- material requirements and strategic constraints are traceable;
- critical architecture decisions have explicit rationale and owners;
- unresolved decisions are either intentionally deferred or gated;
- implementation can start without silently inventing scope or authority;
- rollback/transition logic is proportionate to impact;
- the strategic gate permits the next commitment.

## Handoff

Carry forward the v2 Strategic Context Header plus:

- authoritative architecture/spec references;
- explicit design decisions and rejected alternatives;
- open architecture questions;
- project-specific targets and their authority/source;
- main effort and reserve;
- evidence expected from implementation.

> **Completion criterion:** implementers know not only what to build, but which strategic assumption each material choice serves and what would justify changing it.

# Runbook — Enterprise Feature

> **Mode:** NEXUS-Sprint  
> **Planning range:** scenario-dependent; often multi-week  
> **Purpose:** deliver a material enterprise capability without allowing roadmap pressure to override system integrity, compliance, maintainability, or authority

---

## Governing frame

**Governing object:** produce a validated enterprise capability that improves the declared user/business outcome while remaining compatible with the existing product, controls, dependencies, and operating model.

**Non-object:** ship the roadmap item, maximize scope, satisfy a single stakeholder metric, or hit a generic quality number regardless of system-level consequences.

## Decision owner

An authorized product/program owner owns the business commitment. Security, compliance, legal, data, architecture, or operational authorities retain their own non-transferable decision rights where applicable.

Strategic Assurance tests coherence; it does not replace those authorities.

---

## Strategic control roster

| Agent | Slug | Responsibility |
|---|---|---|
| Strategic Assurance Lead | `specialized-strategic-assurance-lead` | end-state, causal coherence, seven tests, termination |
| Agents Orchestrator | `agents-orchestrator` | execution coordination |
| Project Shepherd | `project-management-project-shepherd` | cross-functional dependencies/stakeholders |
| Senior Project Manager | `project-manager-senior` | task/dependency map |
| Sprint Prioritizer | `product-sprint-prioritizer` | priority and explicit tradeoffs |

Core product, engineering, design, QA, compliance, finance, and specialist agents are activated from `strategy/runbooks.json` according to the actual dependency structure.

---

## Mandatory artifacts

Before material implementation:

- Strategic Decision Record;
- Claim Register;
- authority/stakeholder map;
- requirements traceability with authoritative source;
- integration/dependency map;
- security/compliance/data constraints;
- rollback/migration strategy proportionate to impact;
- measurable minimum sufficient result and termination criteria.

---

## Execution sequence

The sequence below expresses dependencies, not a fixed calendar.

### 1. Requirements and authority reconciliation

Distinguish:

- requested feature;
- underlying user/business problem;
- mandatory contractual/regulatory requirements;
- architectural constraints;
- stakeholder preferences;
- assumptions presented as requirements.

For every material requirement record its source and owner.

### 2. User / workflow evidence

Validate the workflow and affected roles at the level necessary for the commitment.

Do not assume one stakeholder represents all users, admins, compliance teams, operators, or customers affected by the feature.

### 3. Architecture and integration design

Explicitly model:

- interfaces/contracts;
- data ownership and migration;
- auth/authz;
- failure propagation;
- compatibility/versioning;
- external dependencies;
- observability;
- rollback/feature isolation;
- operational ownership;
- compliance/security constraints.

### 4. Prioritize the bounded capability

Use scoring frameworks only as aids.

The plan must state:

- main effort;
- minimum required integration surface;
- what is deferred;
- what is explicitly out of scope;
- reserve for integration surprises;
- evidence that would trigger reprioritization.

### 5. Foundation / thin integration slice

Before broad build, prove the riskiest or most causally central integration assumption where practical.

A vertical slice may be more valuable than extensive scaffolding if it discriminates whether the architecture works in the existing enterprise environment.

### 6. Build with independent validation

Use the v2 Build playbook.

For failures distinguish:

- implementation defect;
- design/integration defect;
- orientation/requirement defect.

Repeated failures that expose architecture or requirement errors should trigger `REDESIGN`, not more local patching.

### 7. Risk-based hardening

Select tests from actual requirements and risks.

This runbook does **not** impose universal defaults such as:

- >80% code coverage;
- P95 <200 ms;
- WCAG 2.1 AA in every context regardless of applicable standard;
- “zero vulnerabilities” as an undefined absolute;
- 95% brand adherence;
- 100% spec compliance when the spec itself contains unresolved contradictions;
- load at exactly 10× current traffic.

Those may be valid project targets when an authoritative requirement, risk model, or measurement justifies them.

For each quantitative gate record:

```yaml
requirement: ""
target: ""
source_or_owner: ""
baseline: ""
measurement_method: ""
materiality: ""
```

### 8. Controlled rollout

Choose rollout mechanics from impact and reversibility:

- feature flag;
- internal cohort;
- named tenants;
- percentage rollout;
- regional rollout;
- full release.

Do not default to a specific `5% → 25% → 100%` sequence unless it fits the user population, risk model, observability, and rollback characteristics.

---

## Communication

Communication cadence follows decision need, not generic “daily/weekly/monthly” doctrine.

Every material update preserves:

- governing object;
- current strategic output;
- changed evidence/assumptions;
- blockers requiring authority;
- reserve/budget change;
- next material decision.

Executive summaries must not erase technical dissent or uncertainty.

---

## Gate criteria

Before production exposure, establish as applicable:

- user/business mechanism remains supported;
- material requirements trace to authoritative sources;
- integration and migration evidence is sufficient;
- applicable security/compliance reviews are complete or explicit conditions exist;
- project-specific performance/capacity targets are verified using defined methods;
- rollback/isolation is tested to the required level;
- operational ownership/support exists;
- external claims are supported;
- open `UNKNOWN` and `NOT_TESTED` surfaces are explicitly accepted or gated;
- the next exposure remains within authority.

Strategic output: `PROCEED`, `PROCEED_WITH_CONDITIONS`, `HOLD`, `REDESIGN`, or `REJECT`.

---

## Termination / redesign triggers

Stop or redesign when:

- the underlying user/business benefit is falsified;
- required integration is materially incompatible with the current system;
- a mandatory legal/security/control condition cannot be satisfied;
- the migration/operational burden exceeds the authorized benefit;
- the feature creates unacceptable concentration or support risk;
- the implementation consumes the reserve needed to operate it safely;
- authority or stakeholder commitments required for deployment are withdrawn.

Sunk cost and executive visibility are not reasons to continue.

---

## Conservation

After release:

- transfer ownership to ordinary product/operations/support;
- expire temporary feature flags/access/processes when appropriate;
- monitor the user/business outcome as well as technical health;
- preserve the decision and evidence record;
- convert recurrent exceptions into explicit rules;
- open a new decision record for material expansion or changed objectives.

> **Runbook success:** the enterprise gains a supportable capability whose value and risks can be explained and sustained — not merely a completed roadmap line.

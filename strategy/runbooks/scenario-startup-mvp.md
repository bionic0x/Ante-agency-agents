# Runbook — Startup MVP

> **Mode:** NEXUS-Sprint  
> **Planning range:** often 4–6 weeks, but not a promise  
> **Purpose:** test a bounded product thesis with the smallest supportable evidence-generating product

---

## Governing frame

**Governing object:** establish whether a specific customer problem can be solved by a usable, supportable product strongly enough to justify the next material investment.

**Non-object:** maximize feature count, sprint velocity, launch speed, demo polish, or a predetermined calendar.

Launching an MVP is not evidence of product-market fit. The MVP exists to create better evidence about a product thesis while preserving enough reserve to redesign or stop.

## Decision owner

An authorized founder, product owner, or executive owns the material commitment and residual risk.

The Strategic Assurance Lead tests coherence. The Agents Orchestrator coordinates work. Neither role creates authority by itself.

---

## Core roster

### Strategic control — always active for material commitments

| Agent | Slug | Responsibility |
|---|---|---|
| Strategic Assurance Lead | `specialized-strategic-assurance-lead` | governing object, causal thesis, seven tests, falsifier, exit |
| Agents Orchestrator | `agents-orchestrator` | execution mesh and context continuity |
| Senior Project Manager | `project-manager-senior` | dependencies, plan, gates |
| Sprint Prioritizer | `product-sprint-prioritizer` | smallest evidence-bearing backlog |

### Product & build — activate as needed

| Agent | Slug |
|---|---|
| UX Architect | `design-ux-architect` |
| Frontend Developer | `engineering-frontend-developer` |
| Backend Architect | `engineering-backend-architect` |
| DevOps Automator | `engineering-devops-automator` |
| Evidence Collector | `testing-evidence-collector` |
| Reality Checker | `testing-reality-checker` |

### Growth / support — conditional

Activate only where the thesis and stage justify them: Growth Hacker, Content Creator, Social Media Strategist, Brand Guardian, Analytics Reporter, Rapid Prototyper, AI Engineer, Performance Benchmarker, Infrastructure Maintainer.

---

## Mandatory artifacts

Before a material build commitment:

1. instantiated `strategy/templates/strategic-decision-record.md`;
2. instantiated `strategy/templates/claim-register.yaml`;
3. product thesis and credible alternative explanation;
4. falsifier;
5. minimum sufficient result;
6. current authority/constraint map;
7. termination and conservation criteria.

---

## Execution topology

The following is a **default dependency pattern**, not a fixed week-by-week script.

### A. Orient

Determine what decision-critical evidence is missing.

Possible activities:

- user/problem evidence;
- market/alternative context;
- regulatory or data perimeter;
- technology feasibility;
- measured baseline.

Skip broad discovery when current evidence is already sufficient for the next bounded commitment.

### B. Define the thin thesis

Write:

```text
For [specific user/context],
we believe [bounded capability]
will change [behavior/problem state]
because [mechanism].
We will treat [observation] as evidence against the thesis.
```

Separate:

- problem evidence;
- product hypothesis;
- willingness-to-use/pay hypothesis;
- acquisition/distribution hypothesis;
- operational supportability hypothesis.

Do not collapse them into “PMF.”

### C. Architecture for the first meaningful slice

Choose the minimum system and UX architecture capable of producing the intended user outcome and evidence.

Explicitly state:

- critical dependencies;
- source of truth;
- security/access boundaries;
- project-specific SLO/quality requirements and their source;
- analytics/evidence instrumentation;
- rollback/recovery;
- intentionally deferred architecture.

### D. Build / validate loops

Use bounded tasks with independent validation.

Retry/experiment budget is configured from cost, reversibility, learning value, time, and reserve. There is no universal three-attempt rule.

When a failure repeats, classify it as:

- execution defect;
- design defect;
- orientation defect.

Do not keep repairing implementation if the thesis itself is failing.

### E. Controlled exposure

Choose the smallest real-user exposure that can test the thesis without unnecessary blast radius.

Possible forms:

- prototype/usability test;
- concierge/manual service;
- invitation cohort;
- limited production pilot;
- public MVP;
- staged segment rollout.

A public launch is not mandatory if a smaller test answers the decision better.

### F. Decide

After evidence arrives, return one of:

- `PROCEED`
- `PROCEED_WITH_CONDITIONS`
- `HOLD`
- `REDESIGN`
- `REJECT`

The decision owner authorizes the next material commitment.

---

## Metrics

There are no universal Startup MVP thresholds in this runbook.

Do **not** default to:

- 100% feature completion;
- launch in six weeks as proof of success;
- first users within 48 hours;
- >99% uptime without an authoritative SLO;
- a fixed number of feedback responses;
- a generic conversion target.

Instead define:

| Metric | Type | Why it matters | Baseline | Target / decision condition | Source |
|---|---|---|---|---|---|
| [metric] | outcome / effect / guardrail / activity | | | | |

Guardrail metrics should reveal when metric optimization damages the governing object.

---

## Strategic gate

Before the next irreversible commitment, apply all seven tests:

1. governing-object;
2. causal;
3. interactive;
4. conversion;
5. legitimacy;
6. epistemic;
7. exit.

A technical READY/PASS verdict is evidence for the gate, not the gate authority itself.

---

## Termination

Close, redesign, or narrow the initiative when:

- the declared falsifier is met;
- the user problem is weaker/different than assumed;
- the product cannot create the intended behavior/effect at acceptable cost/risk;
- required authority/resources cannot be obtained;
- the MVP generates no decision value relative to its cost;
- the minimum sufficient result is achieved and ownership transfers to normal product/operations.

Do not continue because a launch date, sunk cost, or prior sprint success makes stopping uncomfortable.

---

## Conservation

If the MVP thesis survives:

- transfer operational ownership;
- expire temporary access/processes;
- document real SLOs/constraints from evidence;
- preserve the Claim Register;
- convert repeatable controls into ordinary tests/policies;
- open a new strategic decision for material scale expansion rather than treating MVP success as automatic permission.

> **Runbook success:** the organization ends with a better decision and a supportable product thesis — not merely a shipped MVP.

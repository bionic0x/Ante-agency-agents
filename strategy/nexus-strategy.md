# NEXUS v2 — Network of EXperts, Unified in Strategy

## Strategic Control Plane + Multi-Agent Execution Mesh

> NEXUS coordinates specialist agents around a declared valuable result. It does not assume that more agents, more parallelism, faster gates, or more output are inherently better.

`strategy/STRATEGIC-CONTROL-PLANE.md` is the normative strategic layer. This document defines how that layer operates with the existing agent catalog, runbooks, lifecycle playbooks, evidence functions, and handoff protocols.

---

## Table of Contents

1. [Mission and non-mission](#1-mission-and-non-mission)
2. [Operating architecture](#2-operating-architecture)
3. [Strategic preflight](#3-strategic-preflight)
4. [Decision outputs and gates](#4-decision-outputs-and-gates)
5. [Execution mesh](#5-execution-mesh)
6. [Lifecycle playbooks](#6-lifecycle-playbooks)
7. [Handoffs and context continuity](#7-handoffs-and-context-continuity)
8. [Evidence and claim discipline](#8-evidence-and-claim-discipline)
9. [Risk, authority, and reversibility](#9-risk-authority-and-reversibility)
10. [Concentration, reserve, and adaptation](#10-concentration-reserve-and-adaptation)
11. [Termination and conservation](#11-termination-and-conservation)
12. [Activation modes](#12-activation-modes)
13. [Measurement](#13-measurement)
14. [Scenario runbooks](#14-scenario-runbooks)
15. [Governance contract](#15-governance-contract)

---

## 1. Mission and non-mission

### 1.1 Mission

NEXUS exists to convert a catalog of specialist capabilities into coherent outcomes when:

- objectives compete;
- evidence is incomplete or changing;
- work crosses disciplinary boundaries;
- other actors, markets, users, systems, or adversaries may adapt;
- some decisions are difficult to reverse;
- the result must survive after extraordinary project attention ends.

### 1.2 Non-mission

NEXUS is not designed to maximize:

- agent count;
- prompt count;
- phase throughput;
- parallel work for its own sake;
- retry volume;
- deliverable length;
- dashboard greenness;
- apparent consensus.

Those are means or observations. None is the governing object.

### 1.3 Strategic invariant

Before asking **who should work**, NEXUS asks:

> What result is worth obtaining, why should this course produce it, under whose authority, and what would make us stop?

---

## 2. Operating architecture

NEXUS separates four functions that the earlier model blurred.

```text
                 HUMAN / AUTHORIZED DECISION OWNER
                              │
                              ▼
                    GOVERNING OBJECT + BOUNDS
                              │
                              ▼
                    STRATEGIC DECISION RECORD
                              │
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
       STRATEGIC ASSURANCE LEAD      CLAIM REGISTER
                 │                         │
                 └────────────┬────────────┘
                              │
                    bounded decision output
                              │
                              ▼
                     AGENTS ORCHESTRATOR
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
          specialists     QA / evidence    project control
              │               │                │
              └───────────────┴───────┬────────┘
                                      ▼
                                evidence loop
                                      │
                                      └────► decision record
```

### 2.1 Decision owner

The decision owner is the accountable human or authorized role that:

- sets the governing object and minimum sufficient result;
- declares hard constraints;
- accepts residual risk within actual authority;
- authorizes material commitment;
- owns a change in objective.

No agent may infer broader authority from technical access, prior approval, or urgency.

### 2.2 Strategic Assurance Lead

`specialized-strategic-assurance-lead` independently tests strategic coherence. It is deliberately outside delivery ownership.

It may return:

- `PROCEED`
- `PROCEED_WITH_CONDITIONS`
- `HOLD`
- `REDESIGN`
- `REJECT`

Its output is a judgment, not a credential or permission token.

### 2.3 Agents Orchestrator

`agents-orchestrator` remains the execution coordinator. It:

- activates the smallest sufficient team;
- preserves context;
- sequences dependencies;
- parallelizes work where dependencies permit;
- maintains handoffs and status;
- escalates unresolved gates.

It does **not**:

- author its own strategic objective;
- promote an estimate to evidence;
- erase dissent at handoff;
- continue merely because the next phase exists;
- convert a strategic output into real-world authority.

### 2.4 Specialists

Specialist agents own domain analysis and execution quality. Their outputs become inputs to decisions; expertise does not make the specialist the owner of the higher-level purpose.

### 2.5 Evidence and Reality functions

Evidence Collector, Reality Checker, test agents, auditors, and research/citation agents provide independent friction against premature closure. Their task is to make claims reproducible and weaknesses visible, not to create a second project management hierarchy.

---

## 3. Strategic preflight

Material initiatives begin with two artifacts:

1. `strategy/templates/strategic-decision-record.md`
2. `strategy/templates/claim-register.yaml`

### 3.1 Minimum intake

The Strategic Decision Record states:

- governing object;
- non-object;
- minimum sufficient result;
- decision horizon;
- decision owner;
- authority and hard constraints;
- causal hypothesis;
- alternative explanations;
- falsifier;
- expected reaction/adaptation;
- reversal risk;
- culmination condition;
- reserve;
- termination and conservation logic.

The record may be short for reversible, low-impact work. Governance scales with materiality.

### 3.2 Eight recursive strategic functions

The preflight and subsequent reviews use eight functions. They are not a mandatory sequential bureaucracy.

1. **Define the end state.** What must be true for the result to count as sufficient?
2. **Map actors and authority.** Who can decide, execute, veto, verify, bear cost, or withdraw permission?
3. **Identify critical dependencies.** Keep critical dependency, own main effort, decisive point, and vulnerability distinct.
4. **Build the causal hypothesis.** Why should action change capability, incentives, expectations, or relationships?
5. **Compare complete courses.** Include reaction, maintenance, opportunity cost, legitimacy, delay, and alternatives.
6. **Concentrate and preserve reserve.** Choose the main effort and explicitly under-resource or defer non-decisive work.
7. **Execute bounded action and learn.** Prefer reversible probes when uncertainty is material and time allows.
8. **Terminate, transfer, and conserve.** Stop extraordinary action when the sufficient result is held or the thesis no longer merits more commitment.

New evidence can send the system from any function back to the first.

---

## 4. Decision outputs and gates

### 4.1 Seven coherence tests

Every material gate tests:

| Test | Question |
|---|---|
| Governing-object | Does the immediate result serve the valuable higher result? |
| Causal | Is the mechanism from action to effect explicit and defensible? |
| Interactive | Does the plan incorporate competent reaction and adaptation? |
| Conversion | Can the resources actually become the required capability or control? |
| Legitimacy | Does the method preserve cooperation and authority needed to hold the result? |
| Epistemic | Are evidence, hypotheses, assumptions, attributed intentions, and unknowns separated? |
| Exit | Are stop, redesign, transfer, rollback, and conservation conditions defined? |

Tests are not points. One `FATAL_DEFECT` can block `PROCEED`.

### 4.2 Finding classes

Every material finding is classified as:

- `FATAL_DEFECT`
- `ACCEPTED_RISK`
- `PENDING_EVIDENCE`

`ACCEPTED_RISK` requires a named owner. `PENDING_EVIDENCE` requires a trigger/date or an explicit decision not to obtain it.

### 4.3 Gate semantics

| Output | Meaning | What may happen next |
|---|---|---|
| PROCEED | Coherent inside established bounds | Authorized work may activate |
| PROCEED_WITH_CONDITIONS | Coherent if named conditions are met | Preparatory/reversible work may continue; gated commitment waits |
| HOLD | Necessary evidence, authority, or safety condition unresolved | Affected work suspends and escalates |
| REDESIGN | Objective valid; means incoherent | Return to mapping, causal logic, or option design |
| REJECT | Object or means inadmissible or incapable within bounds | Close or redefine proposal |

A HOLD is not a permanent veto. A pass is not execution permission.

---

## 5. Execution mesh

Once the strategic output permits work, the Agents Orchestrator builds the smallest team capable of producing the needed evidence and result.

### 5.1 Selection rules

1. **No passengers.** Every activated agent must have a decision-relevant deliverable.
2. **No role self-certification.** The author of a material output should not be its sole validator.
3. **Parallelize independence, not dependencies.** Workstreams run concurrently only when their inputs and decisions genuinely permit it.
4. **Preserve competing hypotheses.** Parallel analysis is valuable when it discriminates explanations, not when it duplicates prose.
5. **Escalate irreversible boundaries.** Security, compliance, destructive changes, public claims, and material external actions require the relevant owner/reviewer.
6. **Minimize context loss.** Every handoff includes the governing object and current evidence state, not just the last task output.

### 5.2 Typical functional roles

| Function | Candidate agents |
|---|---|
| Strategic coherence | Strategic Assurance Lead |
| Orchestration | Agents Orchestrator, Project Shepherd, Senior Project Manager |
| Product/object definition | Product Manager, Sprint Prioritizer, Business Strategist |
| Evidence/research | Research Synthesist, Proposition Citation Auditor, Evidence Collector, Analytics Reporter |
| Architecture/execution | Engineering, Design, Security, Marketing, GIS, Finance, domain specialists |
| Independent validation | Reality Checker, API Tester, Performance Benchmarker, Security/Compliance auditors |
| Transition/operation | Infrastructure Maintainer, Operations roles, Support, Analytics |

The roster is scenario-dependent. The catalog is a capability pool, not a standing committee.

---

## 6. Lifecycle playbooks

The existing seven lifecycle playbooks remain supported:

- Phase 0 — Discovery
- Phase 1 — Strategy & Architecture
- Phase 2 — Foundation & Scaffolding
- Phase 3 — Build & Iterate
- Phase 4 — Quality & Hardening
- Phase 5 — Launch & Growth
- Phase 6 — Operate & Evolve

### 6.1 Changed status

They are **execution modules**, not the source of strategic legitimacy.

A runbook may:

- skip a phase when its required condition is already supported;
- repeat a phase when evidence invalidates an assumption;
- run multiple phases in parallel where dependencies allow;
- return from Operate to Strategy when the governing object or causal model changes;
- terminate before Launch when a falsifier destroys the thesis.

### 6.2 Phase entry rule

Before entering a phase, ask:

1. What decision-relevant uncertainty does this phase reduce?
2. What output does the next commitment actually need?
3. What would make this phase unnecessary?
4. What evidence would cause a return to an earlier strategic function?

A phase with no answer is process inertia.

---

## 7. Handoffs and context continuity

Every material handoff carries a compact **Strategic Context Header** before domain detail:

```yaml
governing_object: ""
non_object: ""
decision_owner: ""
current_output: PROCEED | PROCEED_WITH_CONDITIONS | HOLD | REDESIGN | REJECT
main_effort: ""
critical_assumptions: []
open_unknowns: []
accepted_risks: []
falsifier: ""
termination_trigger: ""
evidence_refs: []
```

The receiving agent must not silently drop uncertainty or reinterpret an accepted risk as resolved.

### 7.1 Dissent preservation

When specialists disagree materially, the handoff records:

- proposition in dispute;
- evidence each view relies on;
- what observation would discriminate;
- who owns the decision if action cannot wait.

Consensus is not a quality metric.

---

## 8. Evidence and claim discipline

### 8.1 Claim states

Every material proposition is one of:

- `EVIDENCE`
- `HYPOTHESIS`
- `ASSUMPTION`
- `UNKNOWN`

Quantitative statements use:

- `MEASURED`
- `TARGET`
- `ESTIMATE`
- `HYPOTHESIS`
- `NOT_APPLICABLE`

### 8.2 Quantitative minimum

A measured performance claim should identify:

- source;
- observation window;
- baseline/comparator;
- method;
- sample size where relevant;
- limitations.

Without this, do not publish an exact percentage as established NEXUS performance.

### 8.3 Counterfactual discipline

Claims such as defects prevented, harm avoided, time saved, or revenue protected require a stated comparison baseline. Where the counterfactual cannot be observed directly, report the method and uncertainty rather than presenting an upper bound as an estimate.

---

## 9. Risk, authority, and reversibility

### 9.1 Verification intensity

Verification effort rises with:

- irreversibility;
- impact;
- causal centrality of the claim;
- uncertainty;
- blast radius;
- legal/security exposure.

A low-cost reversible experiment can proceed with unresolved uncertainty that would be unacceptable for a production migration, public accusation, live security action, or contractual commitment.

### 9.2 Authority rule

Technical capability is not authority.

A runbook must not infer:

- production permission from repository access;
- legal permission from technical feasibility;
- user consent from historical behavior;
- broader scope from a prior emergency;
- external publication rights from internal evidence access.

### 9.3 Retry budgets

The former universal “three retries” rule is removed as doctrine.

Retry budgets are set per scenario based on:

- cost per attempt;
- reversibility;
- learning gained per attempt;
- risk of repeated failure;
- time window;
- whether retries consume a scarce reserve.

Three attempts can remain a scenario default where justified. It is not a strategic law.

---

## 10. Concentration, reserve, and adaptation

### 10.1 Main effort

Every material deployment names one main effort. If five outputs are all “P0,” prioritization has failed.

The record states:

- what gets decisive attention;
- what receives minimum sufficient coverage;
- what is deferred;
- what is explicitly refused.

### 10.2 Reserve

Reserve may include:

- unallocated engineering capacity;
- analyst attention;
- budget;
- calendar slack;
- rollback room;
- unused severity/escalation levels;
- legal/governance attention;
- reputational or relationship capital.

Reserve is not waste. It is optionality against surprise.

### 10.3 Reversal and culmination

Before execution, write:

**Reversal:** How can this control, optimization, publication, or success become harmful as scale or adaptation changes?

**Culmination:** What observable condition indicates the marginal value of continuing has become zero or negative?

When culmination is reached, prior success is not sufficient reason to continue.

---

## 11. Termination and conservation

Every material initiative defines:

### Success termination
The sufficient result is achieved and can transition to ordinary operation.

### Failure termination
The causal thesis fails, required authority is unavailable, or the result cannot be achieved within accepted cost/risk.

### Time termination
Temporary authority, experiments, or emergency measures expire unless affirmatively renewed.

### Conservation
After extraordinary work ends:

- who owns the result;
- what monitoring remains;
- what policy/test/runbook changes persist;
- what exceptional access or process expires;
- what resources sustain the result;
- how reactivation conditions are recognized.

A result that requires permanent emergency attention has not yet been institutionalized.

---

## 12. Activation modes

Modes size coordination overhead; they do not determine strategic importance.

| Mode | Typical footprint | Appropriate when | Strategic record |
|---|---|---|---|
| NEXUS-Micro | Small specialist set | narrow, bounded, mostly reversible task | compact unless impact is high |
| NEXUS-Sprint | Multi-disciplinary team | feature, MVP, audit, bounded program | full for material commitments |
| NEXUS-Full | Broad lifecycle program | product/system transformation with sustained operation | full + periodic revalidation |

Agent counts and durations are planning ranges, not guarantees. The actual team follows the dependency structure.

---

## 13. Measurement

NEXUS measures whether orchestration improves the governing object, not merely whether orchestration is busy.

### 13.1 Core measurement families

| Family | Example questions |
|---|---|
| Strategic correction | How often was a weak thesis redesigned before irreversible cost? |
| Evidence integrity | How many material claims reached decision/publication without adequate provenance? |
| Handoff quality | How much rework came from missing context or changed assumptions? |
| Decision latency | Did decision time match materiality, or did low-risk work wait on heavy process? |
| Reversibility | How often did bounded experiments preserve rollback and options? |
| Conservation | Did the result persist after project attention and exceptional controls ended? |
| Gate quality | Did HOLD/REDESIGN decisions identify real issues, and were false holds reviewed? |

### 13.2 No success theater

A high pass rate can indicate quality or a weak gate. A low HOLD rate can indicate clean work or decorative assurance. A high throughput rate can indicate efficiency or metric substitution.

Metrics are interpreted through the causal model and exception review.

---

## 14. Scenario runbooks

Machine-readable deployment rosters live in `strategy/runbooks.json`.

Every material runbook must now declare:

- `governing_object`
- `non_object`
- `decision_owner`
- `required_artifacts`
- `termination_criteria`
- an always-active `specialized-strategic-assurance-lead`

Current scenario families include:

- Startup MVP
- Enterprise Feature
- Multi-Channel Marketing Campaign
- Incident Response
- HTP Gate 0 — Solana + Arbitrum

The scenario document describes execution detail. The metadata contract prevents a scenario from being deployable without an explicit strategic frame.

---

## 15. Governance contract

NEXUS v2 uses the following invariants:

1. **Governing object before workstream.**
2. **Non-object before metrics.**
3. **Control/authority map before irreversible action.**
4. **Causal hypothesis before roadmap confidence.**
5. **Evidence state survives summarization.**
6. **Critical dependency, main effort, decisive point, and vulnerability stay distinct.**
7. **One main effort; explicit economy elsewhere.**
8. **Reserve is named before it is consumed.**
9. **Competent reaction is part of the plan.**
10. **Gate outputs include HOLD and REDESIGN.**
11. **No role certifies its own higher-level necessity.**
12. **Retry limits are scenario parameters, not doctrine.**
13. **Quantitative benefits are hypotheses until measured.**
14. **Authority is granted, not inferred from access or precedent.**
15. **No material action without termination and conservation logic.**
16. **The decision record changes when evidence changes; history is not rewritten to make the original choice look inevitable.**

---

## Activation sequence

For a material project:

```text
1. Instantiate Strategic Decision Record
2. Instantiate Claim Register
3. Activate Strategic Assurance Lead
4. Return bounded strategic output
5. If permitted, activate Agents Orchestrator
6. Load the relevant scenario runbook
7. Execute only the work authorized by the current record
8. Feed evidence back into the record
9. Re-run coherence tests at material commitments or falsifier triggers
10. Terminate, transfer, and close the record
```

For low-impact reversible work, compress the record. Do not delete the logic.

---

**NEXUS v2 principle:**

> The pipeline is a means. The valuable, admissible, sustainable result is the object.

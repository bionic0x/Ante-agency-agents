# ⚡ NEXUS Quick-Start Guide

> **From one specialist to a governed multi-agent team without confusing orchestration, execution, and strategy.**

---

## What is NEXUS?

**NEXUS** (Network of EXperts, Unified in Strategy) coordinates Agency Agents into repeatable multi-agent workflows.

The Agency Agents app v0.3.0 adds **Runbooks** as deployable scenario teams. `strategy/runbooks.json` is the machine-readable contract the app uses to map a scenario to real agent slugs and install the roster.

NEXUS handles orchestration. The new **General Strategy Doctrine** governs material strategic choice.

These are different jobs:

```text
GENERAL STRATEGY DOCTRINE
What result? Why this mechanism? Against what reaction? With what sacrifice? Until when?

NEXUS
Who works when? What context is handed off? What quality gate controls execution?

SPECIALIST AGENTS
How is the selected intervention executed competently?
```

For material decisions, start with strategy before launching a full execution pipeline.

---

## Choose the Right Entry Point

| Your problem | Start with | Why |
|---|---|---|
| Material decision, unclear route, major resource commitment | **Strategic Decision & Transition Runbook** | Diagnose purpose, geometry, mechanism, reaction, allocation, evidence, and exit first |
| Build a product from scratch | **NEXUS-Full** | Full discovery → strategy → foundation → build → harden → launch → operate |
| Build a feature or MVP | **Startup MVP / Enterprise Feature Runbook** | Bounded execution with role-specific team and quality gates |
| Marketing objective where the constraint is not yet proven | **Strategy-Led Marketing Campaign Runbook** | Prevents channel-first planning and KPI sovereignty |
| Production incident | **Incident Response Runbook** | Time-critical coordinated response with verification |
| Low-materiality specialist task | **Direct specialist activation** | Do not add strategic ceremony where it changes no decision |

---

## 🧭 Strategic Decision & Transition

Use when the question is **what should we do?** rather than merely **how do we execute an already authorized task?**

The runbook follows:

```text
DEFINE END STATE
↓
MAP ACTORS / AUTHORITY / DEPENDENCIES
↓
BUILD CAUSAL MODEL
↓
IDENTIFY CONTROL / DECISIVE DEPENDENCY / SCHWERPUNKT
↓
DESIGN REAL OPTIONS
↓
SUBMIT TO COMPETENT REACTION
↓
HUMAN DECISION
↓
EXECUTE WITH INTENT + RESERVE + REVIEW
↓
TRANSITION + CONSERVE
```

**Activation prompt:**

```text
Activate the Strategic Decision & Transition runbook.

Decision required: [DECISION]
Superior purpose: [WHY THIS MATTERS]
Decision owner: [OWNER]
Horizon: [TIME]
Known hard constraints: [LEGAL / ETHICAL / FINANCIAL / TECHNICAL / INSTITUTIONAL]
Available resources: [RESOURCES]

Do not start with a preferred tool or solution.
Use the General Strategy Doctrine.
Separate facts, hypotheses, attributed intentions, and unknowns.
Generate real alternatives, model competent reactions, preserve reserve,
and define sufficient success, refutators, transition, and stopping conditions.
Strategic Red Team review is required before irreversible commitment.
```

Governing file: `strategy/GENERAL-STRATEGY-DOCTRINE.md`  
Runbook: `strategy/runbooks/scenario-strategic-decision.md`

---

## 🚀 NEXUS-Full: Complete Project

Use when strategic authorization exists or include the General Strategy Director in Phase 1 when the product/business route is still material and contestable.

```text
Activate Agents Orchestrator in NEXUS-Full mode.

Project: [PROJECT]
Specification: [SPEC]

Phase 0 — Discovery
Research, user evidence, market/context, constraints.

Phase 1 — Strategy & architecture
General Strategy Director when the superior route remains open;
Studio Producer / Senior PM / Product / UX / Brand / Backend / Finance as relevant.
Run Strategic Red Team before major irreversible commitment.

Phase 2 — Foundation
Infrastructure, architecture, design systems, scaffolding.

Phase 3 — Build
Task-level developer ↔ QA loops.

Phase 4 — Harden
Reality, security, performance, API, accessibility, compliance as required.

Phase 5 — Launch
Activate only marketing/growth interventions justified by the launch strategy.

Phase 6 — Operate & transition
Measure, learn, maintain, sunset, institutionalize, re-diagnose.
```

NEXUS quality gates do not replace strategic coherence tests. A perfectly executed wrong strategy is still wrong.

---

## 🏃 Startup MVP / Enterprise Feature

Use the deployable runbooks in the app when the delivery scenario fits.

### Startup MVP

- rapid product build;
- product + engineering + QA core;
- growth activated later;
- use General Strategy Director first if product/market/business route remains materially uncertain.

Runbook: `strategy/runbooks/scenario-startup-mvp.md`

### Enterprise Feature

- multi-stakeholder feature delivery;
- stronger compliance, governance, security, and quality needs;
- escalate to Strategic Decision runbook if scope changes enterprise obligations, portfolio, or high-irreversibility architecture.

Runbook: `strategy/runbooks/scenario-enterprise-feature.md`

---

## 📢 Strategy-Led Marketing Campaign

Do not activate platform specialists first for a material campaign.

**Activation prompt:**

```text
Activate the Strategy-Led Marketing Campaign runbook.

Superior business outcome: [OUTCOME]
Baseline / gap: [BASELINE]
Decision owner: [OWNER]
Horizon: [HORIZON]
Budget / capacity: [RESOURCES]
Hard limits: [LIMITS]

First determine whether the demand job is create, capture, or conserve.
Map buying situations, intermediaries, availability and bottlenecks.
Diagnose the constraint and causal mechanism before selecting channels.
Compare non-campaign alternatives where relevant.
Model buyer, competitor, platform, retailer and operational reactions.
Then allocate concentration, minimum support and reserve.
Only after human approval activate the selected channel specialists.
Measure business outcome, mechanism and execution separately.
Define sufficient success, refutators, constraint-migration triggers and exit.
```

The runbook can legitimately conclude **do not launch a campaign yet**.

Runbook: `strategy/runbooks/scenario-marketing-campaign.md`  
Marketing doctrine: `marketing/AGENCY_OPERATING_MODEL.md`

---

## 🚨 Incident Response

Use the app's Incident Response Runbook for production incidents where detection, authorization and effect time are compressed.

Runbook: `strategy/runbooks/scenario-incident-response.md`

The strategic doctrine still applies at the boundary: incident responders can execute inside emergency authority, but permanent policy, architecture, risk acceptance, or external commitments require the appropriate decision owner.

---

## 🎯 Direct Specialist Activation

Direct activation is correct when:

- purpose and scope are already authorized;
- the task is low-materiality or reversible;
- the specialist is not being asked to redefine superior goals;
- cross-system externalities are limited;
- success criteria and handoff are clear.

Examples:

```text
Activate API Tester to verify [ENDPOINT / CONTRACT].
Success condition: [CONDITION].
Evidence required: [EVIDENCE].
Escalate if [THRESHOLD].
```

```text
Activate UX Researcher to test [QUESTION] with [USERS].
Decision this research informs: [DECISION].
Do not recommend product strategy beyond the evidence; surface implications and unknowns.
```

```text
Activate Legal Compliance Checker for [SCOPE].
Treat legal/admissibility constraints as boundaries, not as a weighted trade-off against business upside.
```

---

## 🧪 Two Different Gate Systems

### Strategic coherence gates

Use for material choice:

1. **Purpose** — Does the immediate result serve the superior purpose?
2. **Causal** — Can the action produce the effect through an explicit mechanism?
3. **Interactive** — Does it survive competent reaction/adaptation?
4. **Conversion** — Do resources actually convert into control/effect?
5. **Legitimacy** — Does the method preserve cooperation/authority needed to consolidate success?
6. **Epistemic** — Are facts, hypotheses, attributed intentions and unknowns separated?
7. **Exit** — Can we adapt, transfer, stop, terminate and conserve?

These are contradiction tests, not a score.

### Execution quality gates

Use after a choice:

- specification complete enough to execute;
- task implementation complete;
- QA evidence supports PASS;
- security/performance/accessibility/compliance gates as relevant;
- integration verified;
- production readiness supported by evidence.

Do not use an execution PASS to prove the strategy was correct.

---

## 🔬 Evidence Rules

Every material decision package preserves:

- **facts** — sufficiently supported observations for the stated use;
- **hypotheses** — explanations still open to alternatives/refutation;
- **attributed intentions** — inferences about what another actor wants;
- **unknowns** — material information not available.

Also separate:

- probability;
- confidence;
- impact.

A dashboard does not convert an inference into a fact.

---

## 🛑 Autonomy and Stop Authority

Use the least authority required for the task.

```text
Assist
→ Recommend
→ Act after approval
→ Act within explicit bounds
→ Adapt policy within bounds
→ Broad autonomous objective pursuit
```

Higher autonomy requires stronger purpose architecture, clearer rights, better evidence, bounded consequences, reserve, and real stop authority.

Prospective claims about autonomous escalation or saturation remain hypotheses unless independently evidenced in the current case.

---

## 📁 Strategy Documents

| Document | Purpose | Location |
|---|---|---|
| **General Strategy Doctrine** | Cross-agency purpose, power, causality, evidence, interaction and termination | `strategy/GENERAL-STRATEGY-DOCTRINE.md` |
| **NEXUS Master Strategy** | Multi-agent orchestration doctrine | `strategy/nexus-strategy.md` |
| **NEXUS Executive Brief** | Compact overview | `strategy/EXECUTIVE-BRIEF.md` |
| **Strategic Decision Runbook** | Material cross-domain decision + transition | `strategy/runbooks/scenario-strategic-decision.md` |
| **Startup MVP Runbook** | MVP delivery | `strategy/runbooks/scenario-startup-mvp.md` |
| **Enterprise Feature Runbook** | Enterprise feature delivery | `strategy/runbooks/scenario-enterprise-feature.md` |
| **Strategy-Led Marketing Runbook** | Demand diagnosis → selected interventions → evidence/exit | `strategy/runbooks/scenario-marketing-campaign.md` |
| **Incident Response Runbook** | Production incident handling | `strategy/runbooks/scenario-incident-response.md` |
| **Runbook roster contract** | App v0.3.0 one-click team deployment | `strategy/runbooks.json` |
| **Marketing Operating Model** | Marketing specialization of general doctrine | `marketing/AGENCY_OPERATING_MODEL.md` |
| **Activation Prompts** | Reusable NEXUS prompts | `strategy/coordination/agent-activation-prompts.md` |
| **Handoff Templates** | Structured execution handoffs | `strategy/coordination/handoff-templates.md` |

---

## 🔑 Key Concepts in 30 Seconds

1. **Purpose before proxy** — execution metrics serve superior outcomes.
2. **Diagnosis before tool** — available capability does not define the problem.
3. **Mechanism before activity** — state why the action should change the result.
4. **Reaction is part of strategy** — other actors adapt, oppose and cooperate.
5. **Concentration + economy + reserve** — priority requires sacrifice and option value.
6. **Evidence can defeat the plan** — facts, hypotheses, intentions and unknowns stay separate.
7. **Intent-based delegation** — decentralize method inside clear purpose and boundaries.
8. **Quality gates verify execution** — they do not prove strategic correctness.
9. **Termination starts at entry** — define sufficient success and transition before scaling.
10. **The institution should outlive the campaign** — preserve capability and learning, remove obsolete debris.

---

<div align="center">

**Choose the right level first. Then choose the right agents.**

`strategy/GENERAL-STRATEGY-DOCTRINE.md` · `strategy/nexus-strategy.md` · `strategy/runbooks.json`

</div>
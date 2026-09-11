# 📑 Agency Strategy & NEXUS Executive Brief

## Purpose before orchestration. Orchestration before specialist execution.

---

## 1. Situation

The Agency now contains a large and growing catalog of specialized agents across engineering, design, marketing, research, finance, security, GIS, healthcare, paid media, product, project management, support, testing, and other domains.

This creates two distinct coordination problems:

1. **Strategic choice** — deciding what result matters, why a course of action should produce it despite other actors, where scarce resources should concentrate, what evidence could change the decision, and how the effort ends.
2. **Execution orchestration** — deciding which specialists act, in what sequence, with what context, handoffs, quality gates, and escalation rules.

The repository now separates those problems explicitly:

- `strategy/GENERAL-STRATEGY-DOCTRINE.md` governs material strategic choice.
- `strategy/nexus-strategy.md` governs multi-agent orchestration and execution flow.
- `strategy/runbooks.json` exposes scenario teams to the Agency Agents app.
- specialist agent files execute bounded domain work.

A well-orchestrated wrong strategy is still wrong. A sound strategy with poor execution can still fail. The operating model therefore requires both.

---

## 2. Governing Principle

The hierarchy is:

```text
superior purpose / outcome
→ strategic explanation
→ operational sequence
→ tactical objective
→ technical execution
```

Lower-level results may inform and challenge the strategy upward. They do not silently replace the superior purpose.

For material work, every recommendation should make visible:

- sufficient result;
- decision owner;
- actor/dependency geometry;
- causal mechanism;
- real alternatives;
- concentration, economy, and reserve;
- plausible reactions;
- evidence status and refutators;
- rights to propose, decide, execute, pause, and stop;
- transition and conservation.

---

## 3. What NEXUS Solves

NEXUS is the execution/orchestration layer. It provides:

- explicit role assignment;
- structured handoffs;
- phase sequencing;
- Dev↔QA loops where appropriate;
- evidence-oriented quality gates;
- retry/escalation logic;
- scenario runbooks;
- deployable team rosters for the app.

These are design capabilities of the system. They should not be presented as universal quantified performance gains unless measured in the relevant deployment.

### Evidence discipline

Claims such as “X% faster,” “Y% fewer defects,” or “Z% of handoffs fail” require a stated source, population, comparison, and measurement method. In their absence, the repository describes expected mechanisms and operational objectives rather than fabricated benchmark facts.

---

## 4. What the General Strategy Doctrine Adds

The General Strategy Doctrine governs questions NEXUS alone cannot answer:

### Superior purpose

What condition is actually valuable, for whom, within what limits?

### Geometry

Who decides, executes, pays, blocks, verifies, guarantees, adapts, or bears costs? What is the difference between formal authority and effective control?

### Causality

Why should this action produce the intended effect? What alternative explanation remains plausible? What would reduce confidence?

### Decisive structure

What is a central dependency, what is our Schwerpunkt, what condition is decisive, and what requirement is genuinely vulnerable? These concepts are not synonyms.

### Allocation

What receives concentration? What receives minimum sufficient support? What reserve remains available for surprise and adaptation?

### Interaction

What happens after competent opposition, adaptation, cooperation, platform/market response, or third-party intervention?

### Epistemic governance

What is established fact, hypothesis, attributed intention, and unknown? Can contrary evidence reach the decision owner before commitment becomes irreversible?

### Termination

What result is sufficient? When should extraordinary effort stop? Who owns transition, ordinary maintenance, and conservation?

---

## 5. Seven Strategic Coherence Tests

Before a material commitment, ask:

1. **Purpose** — Does the immediate result serve the superior purpose?
2. **Causal** — Can the action produce the claimed effect through an explicit mechanism?
3. **Interactive** — Does the design survive competent reaction or adaptation?
4. **Conversion** — Do the available resources actually convert into control or effect?
5. **Legitimacy** — Does the method preserve the cooperation/authority needed to consolidate success?
6. **Epistemic** — Are facts, hypotheses, attributed intentions, and unknowns separated?
7. **Exit** — Can the effort adapt, transfer, stop, terminate, and conserve the valuable result?

These are contradiction tests, not a weighted score. One fatal defect can invalidate an otherwise attractive plan.

---

## 6. Deployable Runbooks

The Agency Agents app v0.3.0 can use `strategy/runbooks.json` to install scenario rosters by stable filename slug.

| Runbook | Primary use | Strategic note |
|---|---|---|
| **Strategic Decision & Transition** | Material cross-domain choice | Starts with purpose, geometry, mechanism, reaction, allocation, evidence, and exit |
| **Startup MVP Build** | Rapid product delivery | Use strategic runbook first when product/market/business route remains materially unresolved |
| **Enterprise Feature Development** | High-stake feature delivery | Escalate when scope changes enterprise obligations, portfolio, or irreversible architecture |
| **Strategy-Led Marketing Campaign** | Demand intervention | Diagnoses whether a campaign is justified before activating channels |
| **Incident Response** | Production incident | Executes inside emergency authority; permanent policy/risk decisions remain with appropriate owner |

---

## 7. Strategic Agent Layer

### Cross-agency

- **General Strategy Director** — frames material decisions and owns the eight-phase strategic method.
- **Strategic Red Team** — independently attacks indispensable assumptions before irreversible commitment or major scale.

### Marketing specialization

- **Marketing Strategy Orchestrator**
- **Marketing Strategy Director**
- **Market & Demand Mapper**
- **Marketing Evidence Lead**
- **Marketing Portfolio Allocator**
- **Marketing Strategic Red Team**

These roles govern *whether and why* specialists should act. They do not replace the deep execution capabilities of the broader catalog.

---

## 8. Three NEXUS Modes

| Mode | Purpose | Appropriate when |
|---|---|---|
| **NEXUS-Full** | Full lifecycle orchestration | Multiple phases/divisions must coordinate over a substantial project |
| **NEXUS-Sprint** | Bounded cross-functional delivery | A feature, MVP, campaign, or strategic sprint needs a focused team |
| **NEXUS-Micro** | Small targeted workflow | Scope and authority are already clear and a few specialists can complete the task |

Agent counts and durations are scenario estimates, not guarantees. Team size should follow the work and the decision burden rather than a fixed quota.

---

## 9. Decision Rights and Autonomy

Use the least autonomy required:

```text
Assist
→ Recommend
→ Act after approval
→ Act within explicit bounds
→ Adapt policy within bounds
→ Broad autonomous objective pursuit
```

Higher autonomy requires stronger:

- objective architecture;
- competence;
- evidence;
- guardrails;
- reversibility;
- escalation paths;
- stop authority.

Prospective claims about autonomous escalation, machine-mediated saturation, or compressed authorization remain hypotheses unless independently supported in the specific case.

---

## 10. Measurement

Measure at the level appropriate to the decision.

### Strategic decision quality

Look for:

- explicit superior outcome;
- causal mechanism;
- real alternatives;
- named critical assumptions;
- evidence/confidence/refutators;
- resource trade-offs and reserve;
- reaction analysis;
- termination and transition conditions.

### Orchestration quality

Look for:

- complete handoffs;
- role clarity;
- gate compliance;
- evidence-backed PASS/FAIL decisions;
- escalation where authority is exceeded;
- low rework caused by missing context;
- retained institutional memory.

### Business/product/marketing outcomes

Use domain-specific measures tied to the actual causal model. Do not assume a universal benchmark across projects, categories, markets, or horizons.

---

## 11. Recommended Operating Sequence

For a material new initiative:

```text
1. Establish decision mandate
2. Run Strategic Decision & Transition framing if route is materially open
3. Human owner chooses / authorizes
4. Select NEXUS mode or scenario runbook
5. Execute with bounded specialist authority
6. Verify execution and mechanism evidence separately
7. Re-diagnose if assumptions/geometry/constraint change
8. Transition successful capability to ordinary ownership
9. Sunset obsolete interventions and preserve learning
```

For a low-materiality, already-authorized task, start directly with the relevant specialist and avoid unnecessary strategic ceremony.

---

## 12. Repository Map

```text
strategy/
├── GENERAL-STRATEGY-DOCTRINE.md    ← Cross-agency strategic constitution
├── EXECUTIVE-BRIEF.md               ← You are here
├── QUICKSTART.md                    ← Entry-point and activation guide
├── nexus-strategy.md                ← Multi-agent orchestration doctrine
├── runbooks.json                    ← App v0.3.0 deployable roster contract
├── playbooks/                       ← NEXUS phase playbooks
├── coordination/                    ← Activation + handoff templates
└── runbooks/
    ├── scenario-strategic-decision.md
    ├── scenario-startup-mvp.md
    ├── scenario-enterprise-feature.md
    ├── scenario-marketing-campaign.md
    └── scenario-incident-response.md

marketing/
└── AGENCY_OPERATING_MODEL.md        ← Marketing specialization of general doctrine

specialized/
├── general-strategy-director.md
└── strategic-red-team.md
```

---

## 13. Final Standard

**Do not optimize the agency for activity volume. Optimize it for justified decisions, competent execution, reversible learning where uncertainty is high, and the ability to conserve valuable results after extraordinary effort ends.**

NEXUS coordinates the work. Strategy decides what work deserves to exist.
# NEXUS Executive Brief

## Network of EXperts, Unified in Strategy — Strategic Overhaul

## 1. Decision

NEXUS should operate as a **strategic control plane plus execution mesh**, not as a fixed seven-phase pipeline.

The Agency already has a broad specialist catalog, lifecycle playbooks, scenario runbooks, handoff templates, and evidence-oriented QA. The missing layer is a durable mechanism that keeps those capabilities subordinate to a declared valuable result. Without that layer, a well-orchestrated team can still optimize the wrong objective, preserve unsupported claims, or continue after the original causal thesis has failed.

The overhaul introduces that missing layer while preserving the useful execution assets.

---

## 2. Governing object

**Governing object:** convert specialist capability into valuable, evidence-supported outcomes that remain coherent under uncertainty, reaction, constraint, and handoff.

**Non-object:** maximize agent count, parallelism, phase velocity, retry throughput, or apparent completion as ends in themselves.

A successful NEXUS deployment is not one that activates the most agents or clears every gate fastest. It is one that can explain:

- what result is worth obtaining;
- why the chosen means should produce it;
- what evidence supports that belief;
- who is authorized to accept the residual risk;
- what reaction or reversal could invalidate the plan;
- when to stop, redesign, consolidate, or transfer the result to ordinary operation.

---

## 3. What changes

### A. Decision, orchestration, and execution are separated

- **Decision owner** sets the governing object and accepts residual risk within actual authority.
- **Strategic Assurance Lead** independently tests coherence and preserves dissent.
- **Agents Orchestrator** coordinates execution; it does not invent the objective or execution permission.
- **Specialists** produce domain work and evidence.
- **Evidence / Reality functions** test claims and quality without redefining the purpose around what is easiest to measure.

### B. Every material runbook gets a strategic preflight

Before material commitment, NEXUS creates:

1. a **Strategic Decision Record**;
2. a **Claim Register**;
3. a governing object and explicit non-object;
4. a causal hypothesis, alternatives, and falsifier;
5. termination and conservation criteria.

### C. Gates become decision gates, not approval theater

A gate returns one of:

`PROCEED` · `PROCEED_WITH_CONDITIONS` · `HOLD` · `REDESIGN` · `REJECT`

A `HOLD` is temporary and condition-based. It does not create a second sovereign authority. `REDESIGN` protects a valid objective from incoherent means.

### D. The seven lifecycle phases remain, but lose doctrinal primacy

`DISCOVER → STRATEGIZE → SCAFFOLD → BUILD → HARDEN → LAUNCH → OPERATE`

These remain useful execution modules. They may be skipped, repeated, parallelized, or revisited when the Strategic Decision Record explains why. Strategy is recursive learning, not compliance with a calendar.

---

## 4. Evidence standard

NEXUS no longer presents unsupported exact performance percentages as facts.

Every material proposition is tagged:

- `EVIDENCE`
- `HYPOTHESIS`
- `ASSUMPTION`
- `UNKNOWN`

Quantitative claims are additionally marked `MEASURED`, `TARGET`, `ESTIMATE`, or `HYPOTHESIS` unless not applicable.

A measured performance claim should identify the observation window, baseline, source, and method. Until then, claims such as timeline compression, defect reduction, handoff-failure rates, retry effectiveness, or MTTR improvements remain hypotheses to test rather than benefits already proven by this repository.

---

## 5. The strategic method

NEXUS now treats strategy as eight recursive functions:

1. define the valuable end state and termination criteria;
2. map actors, authority, vetoes, affected parties, and control;
3. identify critical dependencies while separating center of gravity, own main effort, decisive point, and vulnerability;
4. build a causal hypothesis with alternatives and falsifiers;
5. compare complete courses of action, including reaction and second-order effects;
6. concentrate effort, economize elsewhere, and preserve reserve;
7. execute bounded actions that generate evidence and permit correction;
8. terminate, transfer, conserve, and institutionalize what should survive.

The method is governed by seven coherence tests: governing-object, causal, interactive, conversion, legitimacy, epistemic, and exit.

See `strategy/STRATEGIC-CONTROL-PLANE.md`.

---

## 6. Expected value — explicitly as hypotheses

The overhaul is designed to improve four things. These are **testable expectations, not measured results yet**.

| Expected effect | Mechanism | Evidence needed |
|---|---|---|
| Fewer wrong-object projects | governing object + non-object + causal test | rate of redesign/closure before build; postmortem classification |
| Better handoffs | mandatory decision/evidence context | rework caused by missing context; handoff defect logs |
| Less claim inflation | claim register + evidence states | unsupported claims caught before external use |
| Earlier correction of failing plans | falsifiers + HOLD/REDESIGN + culmination criteria | time/cost between disconfirming evidence and plan change |

Success metrics should be baselined before targets are adopted.

---

## 7. Operating architecture

```text
HUMAN / AUTHORIZED DECISION OWNER
             │
             ▼
   STRATEGIC DECISION RECORD
             │
     ┌───────┴────────┐
     │ Strategic      │
     │ Assurance Lead │
     └───────┬────────┘
             │ decision output
             ▼
      AGENTS ORCHESTRATOR
             │
     ┌───────┼──────────┐
     ▼       ▼          ▼
 specialists  QA/evidence  runbook/playbooks
     │       │          │
     └───────┴────┬─────┘
                  ▼
             evidence loop
                  │
                  └────────► Strategic Decision Record
```

No component above gains real-world execution authority from its place in this diagram.

---

## 8. Immediate repository changes

This overhaul adds or changes:

- `strategy/STRATEGIC-CONTROL-PLANE.md` — normative orchestration doctrine;
- `specialized/specialized-strategic-assurance-lead.md` — installable assurance role;
- `strategy/templates/strategic-decision-record.md` — decision artifact;
- `strategy/templates/claim-register.yaml` — evidence ledger;
- `strategy/runbooks.json` — strategic metadata and mandatory assurance roster;
- `scripts/check-runbooks.sh` — CI enforcement of the strategic contract;
- `strategy/QUICKSTART.md` — strategic preflight before team activation;
- `strategy/nexus-strategy.md` — revised operating model.

Existing phase playbooks and scenario documents remain executable components, subordinate to the control plane.

---

## 9. Adoption rule

For a **material** initiative — one with meaningful cost, external claims, compliance/security exposure, irreversible action, or cross-functional commitment — do not activate the execution mesh until a Strategic Decision Record exists and the Strategic Assurance Lead has returned a bounded decision output.

For trivial or fully reversible work, the record can be short. Governance should scale with materiality rather than becoming a ceremony.

---

## 10. Final recommendation

Adopt NEXUS v2 as the repository's standard orchestration model, with the following invariant:

> **Orientation before speed; evidence before claim; authority before commitment; termination before momentum.**

The purpose of the overhaul is not to make every project more elaborate. It is to make it harder for a highly capable multi-agent system to become more efficient at doing the wrong thing.

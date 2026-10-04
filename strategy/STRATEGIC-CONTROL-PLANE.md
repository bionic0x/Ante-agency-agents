# NEXUS Strategic Control Plane

## Purpose

NEXUS is not a seven-step conveyor belt. It is a **bounded decision system** for coordinating specialists around a valuable result while evidence changes, resources remain scarce, and other actors or systems can react.

The strategic layer answers four questions before orchestration answers anything else:

1. **What result is actually valuable?**
2. **Why should these means produce that result?**
3. **What reaction, uncertainty, or second-order effect could reverse the value of the plan?**
4. **How will the effort stop, transfer, or become ordinary operation?**

A technically successful deliverable can still be strategic failure when it optimizes the wrong object, creates an unowned dependency, destroys required cooperation, or cannot be conserved.

---

## 1. Document hierarchy

| Question | Governing artifact |
|---|---|
| Why / whether should this work proceed? | `strategy/STRATEGIC-CONTROL-PLANE.md` + Strategic Decision Record |
| Which agents and workstreams should execute it? | `strategy/runbooks.json` + scenario runbook |
| How should a lifecycle phase be executed? | `strategy/playbooks/` |
| How should context move between agents? | `strategy/coordination/` |
| What does a specialist know how to do? | The specialist agent file |
| What evidence supports an external or internal claim? | Claim register + underlying evidence |
| Can this organization still hear a warning? | `strategy/INSTITUTIONAL-SELF-TEST.md` |

### Precedence

When two artifacts conflict, the earlier link governs:

**applicable law and platform policy / authorized human decision owner → `GENERAL-STRATEGY-DOCTRINE.md` → `STRATEGIC-CONTROL-PLANE.md` → domain operating model → NEXUS orchestration → runbook → specialist agent → tool adapter.**

`GENERAL-STRATEGY-DOCTRINE.md` states what strategy *is* and is derived from a dated external source; this document states how that doctrine is *operated here*. A document may narrow what precedes it and may not expand it. Where this control plane appears to grant more scope, authority, or acceptable risk than the doctrine, the doctrine wins and this file is the one to fix.

Lower-level artifacts may **narrow** scope or authority. They may not silently expand the governing object, execution permission, or acceptable risk.

Strategy documentation does not create legal, production, financial, security, or organizational authority. Authority comes from the human/operator, applicable policy, and the systems that actually grant permission.

---

## 2. Separation of decision, orchestration, and execution

### Decision owner
The accountable human or authorized role that sets the governing object, accepts residual risk, and authorizes material commitments.

### Strategic Assurance Lead
A coherence function held **separate from the decision owner and from the orchestrator**. It tests the plan and may return `PROCEED`, `PROCEED_WITH_CONDITIONS`, `HOLD`, `REDESIGN`, or `REJECT`. Its judgment does not itself grant execution authority.

Separation of role does not establish independence of judgment. Assess access, authority, incentives, and the capacity to impose a costly pause. Shared operator, model, context, or evidence selection can create correlated errors; record those dependencies rather than inferring independence from role names or a different model.

Treat the output as structured challenge until a functioning review barrier is demonstrated. Record:

- who selects the evidence and whether the reviewer can independently seek contrary evidence;
- who can pause the work, who may clear a `HOLD`, and whether the author can bypass that pause;
- incentives, reporting dependencies, and relevant separation of operator, model, and context;
- a dated instance or exercise showing that contrary evidence reached the decision owner before commitment and could change or pause the decision.

A different operator/model/context, additional evidence access, or separate human clearance may strengthen review. None alone proves independence across all four dimensions. Where the author can dissolve a `HOLD` by rewording a prompt, disclose that limit and escalate material unresolved findings to the accountable human.

### Agents Orchestrator
The execution coordinator. It activates agents, preserves context, manages dependencies and handoffs, and reports state. It **does not define its own governing object** and does not overrule unresolved authority or evidence conditions.

### Specialist agents
They produce domain work and evidence. A specialist does not validate the strategic necessity of its own output merely by demonstrating technical quality.

### Evidence / Reality functions
They test whether assertions are supported and whether outputs meet the declared criteria. They do not redefine the purpose merely because a measurable proxy is available.

---

## 3. Epistemic states

Every material proposition used to justify a decision is tagged as one of:

- **EVIDENCE** — sufficiently supported for the declared use, with provenance and date.
- **HYPOTHESIS** — plausible explanation that must compete with alternatives.
- **ASSUMPTION** — temporarily accepted premise required to plan or test.
- **ATTRIBUTED_INTENT** — an inference about another party's intention, motive, or state of mind. State capability and volition separately; an actor who *can* do something has not thereby been shown to *intend* it. This status never converts to `EVIDENCE` through repetition; a change of status requires new, discriminating evidence sufficient for the stated use, with the original status and reason for revision preserved.
- **UNKNOWN** — relevant information not currently available.

For quantitative performance statements, use `MEASURED`, `TARGET`, `ESTIMATE`, or `HYPOTHESIS` in addition to provenance. A percentage without a measurement window, source, baseline, and method is not a production fact.

The summary layer must preserve uncertainty present in the underlying work. Confidence may not be promoted merely because the prose becomes shorter.

---

## 4. The eight strategic functions

These functions are **recursive**. They may run in parallel, and new evidence can force a return to the first function. They are not eight mandatory meetings.

### 1. Define the end state
Record the governing object, non-object, minimum sufficient result, beneficiaries, horizon, constraints, and termination criteria.

**Product:** strategic intent that can be evaluated.

### 2. Map actors, authority, and geometry
Identify who decides, executes, grants access, bears costs, can block, can verify, and can withdraw authority. Separate formal authority from observed influence.

**Product:** dated control/actor map.

### 3. Identify critical dependencies
Distinguish:
- center of gravity / critical dependency;
- own main effort (*Schwerpunkt*);
- decisive point;
- critical vulnerability.

Do not collapse the terms. State the causal transmission mechanism and substitutes.

**Product:** dependency hypothesis with scope and review conditions.

### 4. Build the causal hypothesis
Explain how actions are expected to change capabilities, incentives, expectations, or relationships and thereby produce the desired result. Record alternatives and a falsifier.

**Product:** causal chain and counter-hypotheses.

### 5. Compare complete courses of action
Compare not just the first move but reaction, implementation, maintenance, legitimacy, delay, opportunity cost, reversibility, and the option to wait, consolidate, reduce scope, or stop.

**Product:** option comparison with tradeoffs.

### 6. Concentrate, economize, and preserve reserve
Choose one main effort. State what receives only minimum coverage, what is deliberately not done, and which resources/options remain uncommitted for surprise.

**Product:** priority and reserve allocation.

### 7. Execute bounded action and learn
Delegate method within declared intent. Instrument the expected effects. Preserve dissent, failed hypotheses, and evidence. Escalate when authority, safety, or irreversibility requires it.

**Product:** execution order, observation plan, adaptation rules.

### 8. Terminate, transfer, and conserve
Determine whether the sufficient result has been achieved, the hypothesis has failed, or the marginal value of further effort has turned negative. Transfer durable functions to ordinary ownership and expire exceptional measures.

**Product:** closure/transition decision and conservation responsibilities.

---

## 5. Seven coherence tests

A proposal must survive all seven tests before an irreversible commitment. These tests are **not additive scoring**. One fatal defect can invalidate the plan.

| Test | Core question | Typical failure |
|---|---|---|
| Governing-object | Does the immediate result serve the higher purpose? | Activity is justified without an observable valuable result |
| Causal | Why should this action produce the intended effect? | Framework language replaces mechanism |
| Interactive | What competent reaction or adaptation changes the plan? | The environment is treated as passive |
| Conversion | Can available resources become the required control/capacity? | Inventory is counted as usable capability |
| Legitimacy | Does the method preserve necessary cooperation and authority? | The means damage the conditions required to hold the result |
| Epistemic | Are evidence, hypotheses, assumptions, attributed intentions, and unknowns separated, and does the separation survive the summary? | Inference becomes fact during synthesis |
| Exit | What stops, transfers, or changes the action? | Every observation becomes a reason to continue |

Classify findings as:
- `FATAL_DEFECT`
- `ACCEPTED_RISK`
- `PENDING_EVIDENCE`
- `NOT_APPLICABLE`

An accepted risk requires an owner and a reason. Pending evidence requires a date, trigger, or explicit decision not to obtain it.

`NOT_APPLICABLE` exists so that a test which does not bear on the case can be declared instead of answered. It requires a stated reason — for example, the adversarial-reaction dimension of the Interactive test may not apply to a bounded task after checking for relevant adaptive actors; diminishing returns and exit conditions still matter — and it is the only permitted way to leave a test unanswered. Without it, the seven tests are completed ritually: every row acquires a sentence, and a form that always passes has stopped testing anything. `NOT_APPLICABLE` on the Exit or Epistemic test is never valid.

---

## 6. Strategic decision outputs

| Output | Meaning | Orchestration state |
|---|---|---|
| `PROCEED` | Coherent within established bounds | Activate authorized work |
| `PROCEED_WITH_CONDITIONS` | Coherent only if named controls are satisfied before the relevant commitment | Activate safe preparatory work; gate the commitment |
| `HOLD` | Necessary evidence, authority, or safety condition is unresolved | Suspend affected work and escalate |
| `REDESIGN` | Governing object remains valid; proposed means fail coherence | Return to actor/dependency/options work |
| `REJECT` | Object or means are inadmissible or cannot plausibly produce the declared result within bounds | Close or redefine proposal |

No model output grants real-world authority by itself.

---

## 7. Reversal, culmination, and reserve

Every material plan must state three things before launch.

### Reversal
How could success itself create the next failure? Examples include scale creating concentration risk, automation amplifying a bad signal, transparency teaching an adversary, or local optimization damaging trust.

### Culmination condition
What early signal would show that additional effort no longer improves the governing object? Do not wait for outright failure to recognize negative marginal value.

### Reserve
What remains deliberately uncommitted? Reserve can be compute, budget, analyst attention, calendar time, rate-limit capacity, rollback room, legal/governance attention, reputation, or authority.

---

## 8. Strategic pathologies to detect

NEXUS reviews explicitly for:

1. **Level inversion** — local metric replaces the valuable end state.
2. **Nominal objective** — a declared goal has no observable success condition.
3. **Imaginary center** — visibility or prestige is mistaken for system dependence.
4. **Concept collapse** — critical dependency, main effort, decisive point, and vulnerability are treated as synonyms.
5. **Dispersion** — everything is priority; nothing receives decisive concentration.
6. **Friction denial** — the plan requires perfect timing, data, people, or dependencies.
7. **Disoriented speed** — faster execution on an unrevised false model.
8. **Denied culmination** — prior success is used to justify further commitment after the sign has changed.
9. **Mirrored symmetry** — the response is chosen by the opponent's move rather than our purpose.
10. **Illegitimate victory** — the method destroys cooperation or authority needed to consolidate the result.
11. **Attributed intention as fact** — psychology is presented as observation.
12. **Metric substitution** — actors optimize the indicator at the expense of the underlying result.
13. **Escalation of commitment** — sunk cost becomes a reason for future cost.
14. **Chronic personalization** — recurrent conflicts must be renegotiated because no rule, owner, exception path, or appeal exists.

Pathologies describe mechanisms, not personalities.

---

## 9. Mandatory artifacts

Every material runbook deployment produces at least:

1. `strategy/templates/strategic-decision-record.md` — instantiated for the project.
2. `strategy/templates/claim-register.yaml` — instantiated and maintained.
3. Evidence bundle or references sufficient to reproduce material claims.
4. Closure/transition update to the decision record.

Runbooks may require additional artifacts, but may not waive these without an explicit documented exception by the decision owner.

---

## 10. Governance rules

- **No unsupported certainty.** External or executive claims require provenance appropriate to their materiality.
- **No authority by inference.** Prior execution permission does not silently expand scope.
- **No irreversible action on stale orientation.** Material uncertainty can justify a reversible experiment, not an unbounded commitment.
- **No quality gate as theater.** A gate must be able to return HOLD or REDESIGN and must preserve dissent.
- **No fixed retry count as doctrine.** Retry budgets are scenario parameters based on cost, reversibility, and learning value.
- **No schedule as proof.** Timelines are planning estimates unless contractually committed by an authorized owner.
- **No strategy by metric.** Metrics instrument the causal hypothesis; they do not replace it.
- **No action without exit.** Material commitments require rollback, termination, transfer, or conservation logic.

---

## 11. Relationship to the existing seven phase playbooks

The existing lifecycle playbooks remain useful execution modules:

`DISCOVER → STRATEGIZE → SCAFFOLD → BUILD → HARDEN → LAUNCH → OPERATE`

They no longer define the strategy by their sequence. A runbook may skip, repeat, parallelize, or revisit phases when the Strategic Decision Record explains why. The control plane sits **above** the phase model:

```text
GOVERNING OBJECT + AUTHORITY
           │
           ▼
STRATEGIC DECISION RECORD
           │
  ┌────────┴────────┐
  │  Seven tests   │◄──────── Evidence / learning
  └────────┬────────┘
           │
   decision output
           │
           ▼
   AGENTS ORCHESTRATOR
           │
           ▼
runbook / phases / specialists
           │
           └──────────────► evidence back to the record
```

The point is not to slow execution. It is to ensure that speed remains subordinate to orientation and that execution remains subordinate to a result worth obtaining.

# NEXUS v2 Handoff Templates

> Handoffs preserve the current strategic frame, evidence state, dissent, and execution context. A shorter handoff is better than a longer one if the receiving agent can still reconstruct what matters to the decision.

---

## 0. Strategic Context Header — mandatory for material handoffs

Prepend this block to material transfers, phase gates, escalations, and incident handoffs.

```yaml
governing_object: ""
non_object: ""
decision_owner: ""
strategic_output: PROCEED | PROCEED_WITH_CONDITIONS | HOLD | REDESIGN | REJECT
main_effort: ""
critical_assumptions: []
open_unknowns: []
accepted_risks: []
material_dissent: []
falsifier: ""
culmination_condition: ""
termination_trigger: ""
evidence_refs: []
```

Rules:

- Do not remove an uncertainty because the document is becoming shorter.
- Do not convert an accepted risk into a resolved issue.
- Do not convert a hypothesis into evidence during handoff.
- If the receiving task is blocked by `HOLD`, pass only the work explicitly allowed by the HOLD conditions.
- Execution permission must come from the actual decision owner or system of authority, not from this header.

---

## 1. Standard Agent-to-Agent Handoff

```markdown
# NEXUS Handoff

## Strategic Context
[Paste the Strategic Context Header]

## Metadata
| Field | Value |
|---|---|
| From | [Agent / function] |
| To | [Agent / function] |
| Workstream | [Name] |
| Task reference | [ID / link] |
| Timestamp | [ISO-8601] |

## Current state
**Completed:** [What is actually complete]

**Not complete / not established:** [What remains open]

**Relevant artifacts:**
- [path/ref] — [purpose]

**Dependencies:** [Inputs/decisions this work relies on]

**Constraints:** [Authority, legal, technical, budget, time, security, brand, etc.]

## Deliverable request
**Decision-relevant question:** [What uncertainty or need this output resolves]

**Deliverable:** [Specific output]

**Acceptance criteria:**
- [ ] [criterion]
- [ ] [criterion]

**Evidence required:** [tests, sources, screenshots, measurements, citations, logs]

## Claim state

Vocabulary: `strategy/contracts.json`. Preserve claim IDs, revisions and source lineage.
| Proposition | Status | Evidence / source | Consequence if wrong |
|---|---|---|---|
| [claim] | EVIDENCE / HYPOTHESIS / ASSUMPTION / ATTRIBUTED_INTENT / UNKNOWN | [ref] | [impact] |

## Handoff back / next
[Who receives the output, what decision it informs, and what format is required]
```

---

## 2. QA / Validation — PASS

A QA pass means the tested acceptance criteria passed. It does **not** mean the initiative is strategically approved or that a live action is authorized.

```markdown
# NEXUS Validation Verdict: PASS

## Strategic Context
[Paste the Strategic Context Header]

## Task
| Field | Value |
|---|---|
| Task ID | [ID] |
| Producer | [Agent] |
| Validator | [Agent] |
| Attempt | [N] |
| Retry budget | [configured budget and rationale] |
| Timestamp | [ISO-8601] |

## Verdict
PASS for the acceptance criteria below.

## Evidence
| Criterion | Result | Evidence |
|---|---|---|
| [criterion] | PASS | [ref] |
| [criterion] | PASS | [ref] |

## Limitations / untested surfaces
- [limitation]

## Claim updates
- [claim ID] → [new status and why]

## Next action
[Authorized next step, or return to decision/gate owner]
```

---

## 3. QA / Validation — FAIL

```markdown
# NEXUS Validation Verdict: FAIL

## Strategic Context
[Paste the Strategic Context Header]

## Task
| Field | Value |
|---|---|
| Task ID | [ID] |
| Producer | [Agent] |
| Validator | [Agent] |
| Attempt | [N] |
| Retry budget | [configured budget and rationale] |
| Timestamp | [ISO-8601] |

## Issues

### [Issue ID] — [severity]
**Expected:** [criterion]

**Observed:** [result]

**Evidence:** [ref]

**Likely cause:** [EVIDENCE / HYPOTHESIS / UNKNOWN — explanation]

**Fix or discrimination step:** [specific next action]

## Retry decision
- [ ] retry inside existing design
- [ ] obtain missing evidence first
- [ ] decompose task
- [ ] redesign approach
- [ ] escalate because retry consumes a material reserve or crosses authority boundary

**Remaining retry/experiment budget:** [N / condition]
```

Retry count is a scenario parameter. Do not assume a universal three-attempt maximum.

---

## 4. Escalation / Repeated-Failure Report

Use when repeated attempts stop generating enough learning, consume material reserve, or reveal that the design rather than implementation is failing.

```markdown
# NEXUS Escalation Report

## Strategic Context
[Paste the Strategic Context Header]

## Problem
**Task / decision:** [ID]

**Escalation to:** [decision owner / orchestrator / assurance / specialist authority]

**Why escalation is required now:** [trigger]

## Attempt history
| Attempt | Change made | Evidence generated | Result | What we learned |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |

## Diagnosis
**Execution defect, design defect, or orientation defect?** [classification + rationale]

**Current causal hypothesis:** [statement]

**Alternative explanation:** [statement]

**Falsifier / discriminator:** [what would separate them]

## Reserve impact
- time consumed:
- capacity consumed:
- budget consumed:
- rollback/options lost:
- other material reserve:

## Recommended decision
- [ ] continue with bounded retry
- [ ] obtain evidence
- [ ] reassign
- [ ] decompose
- [ ] REDESIGN
- [ ] HOLD
- [ ] stop / defer

## Decision required
**Owner:** [authorized owner]

**Decision needed before:** [next material commitment / date]
```

---

## 5. Strategic / Phase Gate Handoff

This replaces the old binary phase-gate assumption. A lifecycle phase can be complete while the strategic output is still `HOLD` or `REDESIGN`.

```markdown
# NEXUS Strategic Gate Handoff

## Strategic Context
[Paste the Strategic Context Header]

## Transition
| Field | Value |
|---|---|
| Current module / phase | [name] |
| Proposed next module / commitment | [name] |
| Decision owner | [role/person] |
| Strategic Assurance Lead | [agent/instance] |
| Output | PROCEED / PROCEED_WITH_CONDITIONS / HOLD / REDESIGN / REJECT |
| Timestamp | [ISO-8601] |

## Seven coherence tests
| Test | Result | Finding | Classification | Evidence / condition |
|---|---|---|---|---|
| Governing-object | PASS / CONDITIONAL / FAIL | | FATAL_DEFECT / ACCEPTED_RISK / PENDING_EVIDENCE | |
| Causal | | | | |
| Interactive | | | | |
| Conversion | | | | |
| Legitimacy | | | | |
| Epistemic | | | | |
| Exit | | | | |

## Conditions before next material commitment
1. [condition]
2. [condition]

## Evidence carried forward
- [ref]

## Dissent carried forward
- [proposition, evidence, alternative, owner]

## Risks accepted by decision owner
- [risk]

## Next activation
| Agent / function | Why needed | Activation condition |
|---|---|---|
| | | |
```

---

## 6. Sprint / Iteration Handoff

Velocity is an execution observation, not the governing object.

```markdown
# NEXUS Iteration Handoff

## Strategic Context
[Paste the Strategic Context Header]

## Iteration
| Field | Value |
|---|---|
| Period | [start → end] |
| Main effort | [single primary effort] |
| Intended learning/result | [what should change] |

## Delivery state
| Task | Status | Evidence | Decision relevance |
|---|---|---|---|
| | | | |

## Hypothesis update
**What evidence strengthened the thesis:**
- [item]

**What weakened it:**
- [item]

**What remains unknown:**
- [item]

**Has the falsifier triggered?** [Yes/No + rationale]

**Has the culmination condition moved closer?** [assessment]

## Reserve
**Consumed this iteration:** [time/capacity/budget/options]

**Remaining:** [what is still deliberately uncommitted]

## Next iteration decision
PROCEED / PROCEED_WITH_CONDITIONS / HOLD / REDESIGN / REJECT
```

---

## 7. Incident Handoff

```markdown
# NEXUS Incident Handoff

## Strategic Context
[Paste the Strategic Context Header]

## Incident
| Field | Value |
|---|---|
| Severity | [policy-defined severity] |
| Incident authority | [owner] |
| Detected | [timestamp] |
| Current state | Investigating / Containing / Recovering / Conserving / Closed |

## Observed facts
- [EVIDENCE: source + timestamp]

## Hypotheses
- [HYPOTHESIS: cause / propagation explanation]

## Unknowns
- [UNKNOWN]

## Impact
[Who/what is affected; distinguish observed impact from estimated exposure]

## Actions taken
| Time | Action | Authority | Result | Evidence |
|---|---|---|---|---|
| | | | | |

## Current safe state / rollback
[Describe]

## Temporary authority or access
| Grant | Owner | Scope | Expiry |
|---|---|---|---|
| | | | |

## Next decision
[What must be decided, by whom, and what evidence is needed]

## Conservation requirements before closure
- [ ] root-cause or best-supported causal account recorded
- [ ] residual risks owned
- [ ] temporary access/controls expired or transferred
- [ ] recurrence prevention assigned
- [ ] evidence preserved according to policy
- [ ] governing object restored or explicitly revised
```

---

## Usage guide

| Situation | Template |
|---|---|
| Material context transfer | Strategic Context Header + Standard Handoff |
| Validation succeeds | QA / Validation — PASS |
| Validation fails | QA / Validation — FAIL |
| Repeated attempts stop learning | Escalation / Repeated-Failure Report |
| Material phase/commitment transition | Strategic / Phase Gate Handoff |
| Sprint/iteration boundary | Sprint / Iteration Handoff |
| Incident responder transfer | Incident Handoff |

The purpose of the template is reconstructability, not paperwork volume. Compress it for low-impact work; expand it when uncertainty, irreversibility, or blast radius increases.

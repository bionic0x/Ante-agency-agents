# NEXUS v2 Quick Start

> Start with the decision, then deploy the team.

NEXUS v2 separates **strategic judgment** from **orchestration** and **specialist execution**. The lifecycle playbooks still exist, but a material initiative no longer starts by blindly entering Phase 0 or Phase 1.

---

## 1. Classify the work

Use the lightest governance that matches the decision.

| Work | Typical mode | Strategic treatment |
|---|---|---|
| Narrow, reversible task | NEXUS-Micro | compact record; expand if impact/uncertainty is high |
| Multi-disciplinary feature, MVP, audit, campaign | NEXUS-Sprint | full preflight before material commitment |
| Broad product/system transformation | NEXUS-Full | full record + periodic revalidation |

Mode does not grant authority and does not guarantee a duration or agent count.

---

## 2. Start with Strategic Assurance

For material work, instantiate:

- `strategy/templates/strategic-decision-record.md`
- `strategy/templates/claim-register.yaml`

Then use:

```text
Activate Strategic Assurance Lead.

Initiative: [NAME]
Context: [PROBLEM / SPEC / LINKS]
Decision owner: [AUTHORIZED HUMAN OR ROLE]
Known constraints: [LEGAL / SECURITY / BUDGET / POLICY / TIME]

Create or complete the Strategic Decision Record.
State the governing object and explicit non-object.
Build the causal hypothesis, alternatives, and falsifier.
Separate EVIDENCE, HYPOTHESIS, ASSUMPTION, attributed intention, and UNKNOWN.
Identify competent reaction, reversal, culmination condition, reserve, and termination.
Apply all seven coherence tests.
Return exactly one output:
PROCEED / PROCEED_WITH_CONDITIONS / HOLD / REDESIGN / REJECT.
Do not treat the output as execution authority.
```

If the task is trivial and reversible, the record can be a few lines. If it is irreversible, externally consequential, security-sensitive, regulated, or expensive, the record expands.

---

## 3. If permitted, activate the execution mesh

```text
Activate Agents Orchestrator.

Strategic Decision Record: [PATH / CONTENT]
Claim Register: [PATH / CONTENT]
Scenario: [RUNBOOK OR TASK]
Current strategic output: [OUTPUT]

Build the smallest sufficient team.
Preserve the governing object, non-object, accepted risks, open unknowns, falsifier, and termination trigger in every material handoff.
Parallelize only genuinely independent work.
Do not activate work blocked by HOLD or unsatisfied conditions.
Return evidence to the decision record when assumptions change.
```

---

## 4. Use a scenario runbook when one fits

Machine-readable rosters live in `strategy/runbooks.json`.

Current scenarios:

| Scenario | Mode | Use |
|---|---|---|
| Startup MVP | NEXUS-Sprint | bounded MVP from thesis to validated release |
| Enterprise Feature | NEXUS-Sprint | material feature with compliance, security, and integration constraints |
| Marketing Campaign | NEXUS-Sprint | coordinated campaign with evidence and brand/compliance controls |
| Incident Response | NEXUS-Micro | bounded response, recovery, evidence, and post-incident conservation |
| HTP Gate 0 — Solana + Arbitrum | NEXUS-Sprint | evidence-first DeFi Gate 0 with chain-specific engineering and security/legal review |

Each runbook declares its governing object, non-object, decision owner, mandatory artifacts, termination criteria, and assurance role.

---

## 5. Lifecycle playbooks are execution modules

Use the phase playbooks when their function is needed:

```text
DISCOVER → STRATEGIZE → SCAFFOLD → BUILD → HARDEN → LAUNCH → OPERATE
```

Do **not** assume the sequence is mandatory.

You may:

- revisit Discovery when a production observation breaks the original thesis;
- run architecture and bounded research in parallel;
- skip market discovery when it is already evidenced and still current;
- return from Build to Strategy when a necessary dependency fails;
- terminate before Launch when a falsifier destroys the value proposition;
- move from Incident Response directly into institutional policy changes after recovery.

The Strategic Decision Record explains deviations from the default lifecycle.

---

## 6. Fast templates

### Feature / MVP

```text
Strategic preflight for [FEATURE / MVP].

Governing object: [VALUABLE USER/BUSINESS RESULT]
Non-object: shipping features, sprint velocity, or roadmap completion by themselves
Decision owner: [ROLE]
Minimum sufficient result: [OBSERVABLE CONDITION]
Constraints: [LIST]

Test the causal thesis before architecture commitment.
If coherent, activate Agents Orchestrator with the smallest team covering product, architecture, implementation, evidence, and independent QA.
Use reversible prototypes for unresolved high-value assumptions where feasible.
```

### Bug / reliability problem

```text
NEXUS-Micro for [BUG].

Governing object: restore [USER/SYSTEM FUNCTION] without creating regression or hidden operational debt.
Non-object: closing the ticket.
Decision owner: [ROLE]

Investigate root cause and competing explanations.
Apply a bounded fix, verify the claimed mechanism, test regressions, preserve evidence, and define the condition for closure.
Escalate if the repair changes security, data integrity, external behavior, or architecture materially.
```

### Marketing campaign

```text
Strategic preflight for [CAMPAIGN].

Governing object: [BEHAVIORAL / COMMERCIAL RESULT]
Non-object: impressions, post volume, follower growth, or channel activity unless causally linked to the result
Decision owner: [ROLE]

Separate measured baseline from target.
State the audience-response hypothesis and alternatives.
Define brand/compliance constraints, stop-loss/termination rules, and what evidence changes channel allocation.
Then activate the campaign roster.
```

### Compliance / security audit

```text
Strategic preflight for [AUDIT].

Governing object: reduce material exposure and establish an actionable evidence record.
Non-object: maximize finding count.
Decision owner: [ROLE]

Map authority and scope first.
Prioritize verification by impact, irreversibility, and causal centrality.
Keep findings, exploitability, legal conclusions, and remediation status distinct.
Do not infer permission for live changes from permission to audit.
```

### Incident response

```text
Activate the Incident Response runbook.

Governing object: restore the critical service safely while preserving evidence and preventing recurrence.
Non-object: fastest possible closure or MTTR in isolation.
Decision owner: [INCIDENT AUTHORITY]

During containment, keep authority and rollback explicit.
After stabilization, distinguish symptom removal, root-cause correction, and conservation.
Expire emergency access and temporary controls when their conditions end.
```

---

## 7. The seven questions at every material gate

1. **Governing object:** Does this result serve the higher purpose?
2. **Causal:** Why should this action produce the claimed effect?
3. **Interactive:** What competent reaction or adaptation matters?
4. **Conversion:** Can available resources actually produce the needed capacity/control?
5. **Legitimacy:** Does the method preserve cooperation and authority needed to hold the result?
6. **Epistemic:** Are evidence, hypotheses, assumptions, intentions, and unknowns separated?
7. **Exit:** What stops, redesigns, transfers, or terminates the action?

A gate can return `HOLD` or `REDESIGN`. Passing a gate is not execution permission.

---

## 8. Claim discipline in 30 seconds

Use the claim register.

```yaml
proposition: "NEXUS reduces rework by 30%"
status: HYPOTHESIS
quantitative_status: HYPOTHESIS
source_refs: []
baseline: "not yet measured"
falsifier: "controlled deployments show no material reduction"
```

After measurement:

```yaml
proposition: "..."
status: EVIDENCE
quantitative_status: MEASURED
source_refs: ["experiment-or-report-id"]
observation_window: "..."
baseline: "..."
method: "..."
limitations: ["..."]
```

Do not turn an aspirational number into a fact because it appears in an executive summary.

---

## 9. Retry rule

There is no universal three-retry doctrine.

Choose a retry/experiment budget from:

- cost per attempt;
- reversibility;
- learning gained;
- risk of repeated failure;
- time available;
- reserve consumed.

A three-attempt limit can still be a practical scenario default. It is a parameter, not a law.

---

## 10. Core documents

| Document | Purpose |
|---|---|
| `strategy/STRATEGIC-CONTROL-PLANE.md` | normative strategy and governance |
| `strategy/nexus-strategy.md` | operating model |
| `strategy/templates/strategic-decision-record.md` | material decision record |
| `strategy/templates/claim-register.yaml` | evidence and uncertainty ledger |
| `strategy/runbooks.json` | machine-readable scenario roster and strategic contract |
| `strategy/playbooks/` | lifecycle execution modules |
| `strategy/coordination/` | activation and handoff protocols |
| `strategy/htp-gate0/` | bounded HTP Gate 0 artifacts and chain overlays |

---

## 11. The minimum rule

For any material action, be able to answer in one screen:

```text
OBJECT        What valuable condition are we trying to create or preserve?
NON-OBJECT    What tempting proxy must not replace it?
MECHANISM     Why should our action produce the result?
EVIDENCE      What is observed vs hypothesized vs unknown?
AUTHORITY     Who may accept this risk and authorize commitment?
REACTION      What changes when others or the system adapt?
RESERVE       What remains uncommitted for surprise?
EXIT          What makes us stop, redesign, transfer, or close?
```

Then deploy the agents.

> **Orientation before speed. Evidence before claim. Authority before commitment. Termination before momentum.**

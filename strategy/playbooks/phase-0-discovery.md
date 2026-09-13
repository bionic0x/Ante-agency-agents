# Phase 0 — Discovery & Orientation

> **Status:** execution module subordinate to `strategy/STRATEGIC-CONTROL-PLANE.md`.

## Function

Reduce the decision-critical uncertainty that prevents a coherent commitment.

Discovery is not automatically the first calendar phase and it is not complete because a fixed number of reports, interviews, personas, sources, or market-sizing slides exist. It is used when the current Strategic Decision Record contains material `UNKNOWN`, `ASSUMPTION`, or weak `HYPOTHESIS` entries that can realistically be improved before commitment.

## Governing question

> What must we learn now for the decision owner to distinguish a valuable course of action from a well-executed mistake?

## Entry conditions

Use this module when one or more of the following is material:

- the user/customer problem is weakly evidenced;
- market, stakeholder, or operating context is unclear;
- legal/compliance perimeter is unresolved;
- available data cannot yet support the intended claim or measurement;
- technology feasibility or dependency risk is uncertain;
- a competing explanation would change the chosen course;
- the cost of acting on a wrong assumption exceeds the cost of learning first.

Do not run broad discovery merely because the playbook exists.

## Inputs

- current Strategic Decision Record;
- current Claim Register;
- project/problem brief;
- known constraints and authority boundaries;
- explicit decision to be informed.

## Main effort

Choose the smallest discovery portfolio capable of discriminating the decision-critical hypotheses.

Candidate agents include:

| Need | Candidate agent/function | Typical output |
|---|---|---|
| market / competitive context | Trend Researcher, Business Strategist | sourced market/context assessment |
| user need / behavior | UX Researcher, Feedback Synthesizer | observed needs, behavior, alternatives |
| data landscape | Analytics Reporter | source-of-truth and measurability audit |
| legal/compliance perimeter | Legal Compliance Checker | scoped requirements, unknowns, escalation needs |
| technology landscape | Tool Evaluator, engineering specialist | feasibility/dependency assessment |
| source synthesis | Research Synthesist, Proposition Citation Auditor | evidence map and claim status |

The roster is chosen from the uncertainty, not from a fixed agent count.

## Discovery protocol

### 1. Convert the decision into hypotheses

For each material unknown, record:

```yaml
decision: ""
hypothesis: ""
alternative: ""
evidence_needed: ""
falsifier_or_discriminator: ""
cost_of_being_wrong: ""
time_value_of_more_information: ""
```

### 2. Collect proportionately

Verification intensity rises with impact, irreversibility, and causal centrality.

Do not impose universal minimums such as:

- 15 sources;
- 5–10 interviews;
- 3–5 personas;
- a specific TAM threshold;
- a specific forecast horizon.

A specialist may propose such a sample or threshold, but must justify why it is adequate for the present decision.

### 3. Preserve epistemic states

Every material finding remains tagged as:

- `EVIDENCE`
- `HYPOTHESIS`
- `ASSUMPTION`
- `UNKNOWN`

Attributed intent remains separate from observed conduct.

### 4. Update the causal thesis

Discovery is valuable only if it changes one of:

- the governing object;
- the causal mechanism;
- the set/ranking of options;
- the authority/perimeter;
- the main effort;
- the falsifier;
- the decision to proceed, condition, hold, redesign, or reject.

## Convergence

The Executive Summary Generator may synthesize findings, but **does not own the strategic decision**.

A convergence package should contain:

1. decision-relevant evidence;
2. strongest alternative explanation;
3. unresolved unknowns;
4. changes to the Claim Register;
5. impact on the causal hypothesis;
6. implications for options and constraints;
7. recommendation to the Strategic Assurance Lead / decision owner.

## Gate

Apply the seven coherence tests using the updated evidence.

Possible outputs:

- `PROCEED`
- `PROCEED_WITH_CONDITIONS`
- `HOLD`
- `REDESIGN`
- `REJECT`

The decision owner retains actual authority.

## Exit condition

Discovery ends when **either**:

- the decision-critical uncertainty has been reduced enough for the next bounded commitment;
- remaining uncertainty is explicitly accepted by the authorized owner;
- the information is unobtainable within the relevant window and the plan is redesigned accordingly;
- the causal thesis is falsified and the initiative is rejected or reframed.

Discovery should not continue merely to increase confidence cosmetically.

## Handoff

Use `strategy/coordination/handoff-templates.md` and carry forward:

- governing object and non-object;
- current strategic output;
- evidence and open unknowns;
- alternatives not eliminated;
- accepted risks;
- falsifier and review trigger;
- authority constraints;
- evidence references.

> **Completion criterion:** the initiative is better oriented for a specific decision, not simply better documented.

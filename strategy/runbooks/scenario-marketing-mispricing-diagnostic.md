# ⚖️ Runbook: The Marketing Mispricing Diagnostic

> **Mode**: NEXUS-Sprint | **Duration**: 2 weeks from data receipt (optional 4–6 week Availability Arbitrage Sprint) | **Agents**: Mispriced CMO division + marketing strategic control layer

---

## Scenario

Use this runbook when a CMO, CEO, CFO, founder, or agency leader needs an independent, board-safe answer to one question:

> **Where is marketing capital currently priced for visible activity rather than for compounding availability — and what should move first?**

Typical triggers: a new CMO, an agency review, a proposed rebrand, rising acquisition costs, a budget cut, or a board asking what marketing actually creates.

The diagnostic does **not** assume the answer is more brand investment. Its first job is to find the binding constraint on the superior commercial outcome. If the evidence says the constraint is stock, distribution, price, or service, the report says so and the runbook routes the decision there.

## Governing References

- `strategy/GENERAL-STRATEGY-DOCTRINE.md`
- `strategy/MARKETING-OPERATING-MODEL.md`
- `mispriced-cmo/mispriced-cmo-diagnostic-lead.md` — module architecture and report skeleton

## Agent Roster

### Engagement Core

| Agent | Role |
|---|---|
| Mispricing Diagnostic Lead | Mandate, engagement state, module integration, mispricing thesis, readout |
| Availability Ledger Analyst | Quick-Win Leakage Audit · Ratio Reality Check · Ratio Covenant draft |
| Measurement Bias Reviewer | Measurement Bias Review · Metric Register · evidence architecture |
| Recognition Equity Auditor | Recognition Equity Audit · asset registry · rebrand burden of proof |
| ESOV & Fame Analyst | ESOV Fiction Test · Fame Deficit Score |
| Physical Availability Gap Analyst | Presence · prominence · portfolio · fulfilment · lost-demand estimate |
| Four-Year Clock & Exceptions Desk Analyst | Four-Year Clock Risk · Exceptions Desk Review |

### Strategic Control & Challenge

| Agent | Role |
|---|---|
| Market & Demand Mapper | Buying situations, intermediaries, availability geometry |
| Marketing Evidence Lead | Evidence plan, counterfactual quality, confidence |
| Marketing Portfolio Allocator | Marginal return, concentration, reserve for recommendations |
| Chief Financial Officer | CFO bridge — findings in capital allocation language |
| Marketing Strategic Red Team | Independent challenge of the thesis before readout |

### Deliverable & Assurance

| Agent | Role |
|---|---|
| Repricing Memo Writer | The Marketing Mispricing Report · The Repricing Memo |
| Mispricing Claim Auditor | Claim and citation verification; blocks unverified external claims |

### Commercial (internal only)

| Agent | Role |
|---|---|
| MAXX Profit Offer Architect | Qualification, pricing rationale, proposal, next-phase design — never present in client sessions |

---

## Phase 0 — Qualification and Mandate (before Day 0)

**Lead**: MAXX Profit Offer Architect (internal) → Mispricing Diagnostic Lead

Confirm a live trigger, a reachable decision owner, and a budget large enough that the diagnostic can surface value many times its fee. Then record the mandate:

```yaml
decision_owner: ""
sponsor: ""
superior_business_outcome: ""
annual_marketing_budget: ""
trigger: ""
horizon: ""
materiality: low | medium | high
hard_limits: []
confidentiality: ""
readout_audience: []
```

### Gate 0

**Who can act on the findings, and what outcome are they accountable for?**

---

## Phase 1 — Data Request and Interviews (Days 0–3)

**Lead**: Mispricing Diagnostic Lead

Request three to five years of spend by line and purpose, share and penetration, brand tracking, attribution/MMM/lift tests, 24 months of creative, distribution and stock data, dashboards and bonus metrics, and tenure history. Missing data is recorded as a finding, not a failure.

Interview the CMO, CFO, CEO or GM, performance lead, lead agency, and a commercial or sales leader using the same five questions, so contradictions surface.

### Gate 1

**Is there enough evidence to classify capital by job, or must the scope narrow before analysis starts?**

---

## Phase 2 — Ledger and Measurement First (Days 3–6)

**Leads**: Availability Ledger Analyst · Measurement Bias Reviewer  
**Support**: Marketing Evidence Lead · Marketing Portfolio Allocator

Every other module depends on knowing what money did and how it was credited.

- Classify spend by mechanism into create / capture / availability / conserve / learn / reserve
- Compute declared vs. real ratio and multi-year leakage
- Build the Metric Register; identify attribution vs. incrementality gaps
- Separate average from marginal return on the largest lines

### Gate 2

**Does finance accept the ledger as a fair classification, and do we know which causal claims are tested?**

---

## Phase 3 — Assets, Voice, Availability, Governance (Days 5–8)

**Leads**: Recognition Equity Auditor · ESOV & Fame Analyst · Physical Availability Gap Analyst · Four-Year Clock & Exceptions Desk Analyst  
**Support**: Market & Demand Mapper

Run modules 4–9 in parallel once the ledger and geometry exist. Each module returns: finding · evidence tag · confidence · business implication · recommended action · data gaps.

### Gate 3

**Which module findings are evidenced, which are hypotheses, and do any contradict each other?**

---

## Phase 4 — Thesis and Independent Challenge (Day 9)

**Lead**: Mispricing Diagnostic Lead  
**Challenge**: Marketing Strategic Red Team  
**Finance bridge**: Chief Financial Officer

Write the mispricing thesis:

> We believe [company]'s marketing capital is mispriced toward [visible activity] because [evidence]. The binding constraint on [superior outcome] is [constraint], not [assumed problem]. Moving [resource] from [line] to [line] should first show [mechanism signal] and then [business result]. Our confidence falls if [refutator].

The red team looks for the single contradiction that would invalidate it: a constraint the modules missed, a measurement artifact, a competitive response, or a recommendation the organization cannot execute.

### Gate 4

**Does the thesis survive the strongest challenge — and if not, is it narrowed or withdrawn?**

---

## Phase 5 — Report, Memo, Verification (Days 9–10)

**Leads**: Repricing Memo Writer · Mispricing Claim Auditor

- Assemble The Marketing Mispricing Report in client-safe language
- Draft The Repricing Memo if commissioned
- Verify every external claim and citation; nothing unverified in the body
- Record dissent and what the client can do without further support

### Gate 5

**Could a board decide from the memo, and does every recommendation have an owner, a first signal, a refutator, and a review date?**

---

## Decision Point — Readout (Day 10)

The decision owner receives the report first. The owner chooses, for each recommendation: **adopt / stage / test first / reject with reason**.

---

## Phase 6 — Optional: The Availability Arbitrage Sprint (4–6 weeks)

Activate only if the findings require implementation support.

**Lead**: Mispricing Diagnostic Lead  
**Core**: Marketing Portfolio Allocator · Availability Ledger Analyst · Measurement Bias Reviewer · Recognition Equity Auditor  
**Execution handoff**: Marketing Strategy Orchestrator routes selected interventions to channel specialists under `scenario-marketing-campaign.md`

Deliver: operating doctrine, reallocated budget logic, adopted Ratio Covenant, asset registry, measurement architecture with scheduled incrementality tests, incentive and decision-rights changes, and a 90-day plan with stop and scale rules.

---

## Phase 7 — Optional: The Availability Discipline Retainer

Quarterly: re-run the ledger, check covenant compliance, review tests, re-diagnose whether the constraint has migrated, and confirm what should now be maintained, stopped, or transferred.

---

## Language and Brand-Architecture Rules

- Client documents use THE MISPRICED CMO™ register and client-safe module names only
- Internal commercial vocabulary never appears in client material or client sessions
- BORING WINS' literary hostility is never imported into a report
- Every claim is tagged `[FACT]`, `[INFERENCE]`, `[HYPOTHESIS]`, or `[JUDGMENT]` in the evidence trace

## Completion Standard

The diagnostic is complete when the decision owner can state:

1. what the mispricing is, in one sentence;
2. what the binding constraint is and why it is not the assumed one;
3. which capital moves, from where to where;
4. what stops;
5. what signal should appear first, and when;
6. what would make them reverse;
7. what must be protected.

## Cross-division handoff example

See the [worked marketing, sales and product example](../../examples/mispricing-cross-division.md)
for an evidence-graded handoff, the control hierarchy, installation commands,
receiving-owner acceptance and stopping conditions. It composes this diagnostic
with the existing campaign runbook and does not create another decision owner.

# Runbook — Multi-Channel Marketing Campaign

> **Mode:** NEXUS-Sprint  
> **Planning range:** campaign-dependent; often multi-week  
> **Purpose:** test and scale a coordinated audience-response hypothesis while keeping channel activity subordinate to a measurable commercial or behavioral result

---

## Governing frame

**Governing object:** produce a defined audience behavior or commercial result through a compliant, brand-coherent campaign whose causal assumptions and measurement limits remain explicit.

**Non-object:** maximize impressions, posting frequency, engagement, follower growth, channel coverage, or creative volume without establishing their contribution to the declared result.

## Decision owner

An authorized marketing/business owner controls budget, external commitment, and material campaign changes within the organization's policies. Compliance, brand, platform, and legal authorities retain their respective rights.

---

## Strategic control roster

| Agent | Slug | Responsibility |
|---|---|---|
| Strategic Assurance Lead | `specialized-strategic-assurance-lead` | object/non-object, causal thesis, seven tests, stop/scale logic |
| Agents Orchestrator | `agents-orchestrator` | execution mesh and handoffs |
| Social Media Strategist | `marketing-social-media-strategist` | campaign/channel coordination |
| Analytics Reporter | `support-analytics-reporter` | baseline, measurement, evidence |

Campaign, platform, research, brand, growth, content, experiment, and compliance agents are activated only when the audience/channel hypothesis needs them. See `strategy/runbooks.json`.

---

## Mandatory artifacts

Before material spend/exposure:

- Strategic Decision Record;
- Claim Register;
- measured baseline or explicit `UNKNOWN`;
- audience/problem evidence;
- response hypothesis and credible alternatives;
- channel-selection rationale;
- budget/exposure authority;
- brand/compliance constraints;
- scale, pause, reallocate, and termination conditions.

---

## Campaign thesis

Write one causal chain per major audience/channel combination:

```yaml
audience: ""
observed_need_or_state: ""
message_or_offer: ""
channel: ""
expected_behavior_change: ""
mechanism: ""
measured_baseline: ""
target: ""
leading_indicator: ""
outcome_metric: ""
guardrail_metrics: []
alternative_explanation: ""
falsifier: ""
scale_condition: ""
stop_or_reallocate_condition: ""
```

A platform is not part of the plan merely because the catalog has a specialist for it.

---

## Execution pattern

### 1. Establish baseline and decision metric

Separate:

- activity: posts, sends, impressions;
- outputs: visits, leads, conversations;
- effects: qualified intent, trial, conversion, retention behavior;
- governing outcome: the commercial/behavioral result that matters.

Do not let the most visible platform metric replace the result.

### 2. Select channels from audience evidence

For each candidate channel ask:

- Is the target audience actually reachable there?
- What behavior is plausible on that channel?
- What evidence supports the mechanism?
- What does the channel cost in money, creative capacity, moderation/support, and measurement complexity?
- Does simultaneous activation help coordination or destroy attribution?

### 3. Build content/offer against the hypothesis

Content Creator, Brand Guardian, and platform specialists produce work against an explicit response hypothesis.

Creative quantity is not a success criterion.

### 4. Compliance and platform review

Review applicable:

- ad disclosures;
- endorsements/influencer rules;
- claims substantiation;
- data/consent rules;
- platform policies;
- regulated product/category limits;
- brand constraints.

Do not generalize one jurisdiction/platform review to another without evidence.

### 5. Controlled activation

Choose a spend/exposure level that can generate decision-grade evidence while preserving reserve.

Possible approaches:

- one channel first;
- small parallel cells with clear attribution;
- audience holdout;
- sequential creative test;
- budget-capped multi-channel launch;
- full coordinated campaign where simultaneity is itself part of the mechanism.

### 6. Update rather than chase

When results arrive, compare the causal explanations.

A poor metric can mean:

- wrong audience;
- wrong message/offer;
- wrong channel;
- tracking failure;
- insufficient exposure;
- external/context change;
- fundamentally weak product/value proposition.

Do not reflexively increase spend or content cadence before identifying which explanation the evidence supports.

---

## Metrics

This runbook contains no universal engagement, CTR, CAC, conversion, ROAS, reach, follower, or posting-frequency threshold.

Every quantitative target must state:

| Field | Requirement |
|---|---|
| Status | `MEASURED` / `TARGET` / `ESTIMATE` / `HYPOTHESIS` |
| Baseline | measured comparator or `UNKNOWN` |
| Window | observation period |
| Source | analytics/ad/CRM/source-of-truth |
| Method | attribution/calculation definition |
| Decision use | scale / hold / stop / learn |
| Limitations | known bias, delay, missingness |

An industry benchmark may inform a hypothesis; it does not become this campaign's baseline by citation alone.

---

## Guardrails

As applicable track:

- compliance/brand incidents;
- unsubscribe/complaint rate;
- support burden;
- low-quality lead share;
- return/refund/cancellation behavior;
- audience fatigue;
- organic cannibalization;
- marginal cost deterioration;
- attribution/data-quality degradation.

A campaign can improve its headline metric while harming the governing object.

---

## Gate / allocation decision

At material budget/exposure changes apply the seven coherence tests.

Possible outputs:

- `PROCEED`
- `PROCEED_WITH_CONDITIONS`
- `HOLD`
- `REDESIGN`
- `REJECT`

The business/marketing decision owner authorizes actual spend and publication.

### Scale only when

- the mechanism remains plausible;
- outcome evidence is sufficient for the added commitment;
- marginal economics remain within the authorized bounds;
- guardrails remain acceptable;
- measurement can still distinguish the relevant effects;
- additional exposure does not consume the reserve needed to respond.

### Reallocate / stop when

- falsifier triggers;
- guardrail breach makes the tactic inadmissible;
- marginal spend/effort no longer contributes to the governing object;
- a better channel/offer dominates under the current evidence;
- product/offer weakness makes further media optimization strategically irrelevant;
- required authority or platform access is withdrawn.

---

## Handoff / closure

At campaign close preserve:

- final Claim Register;
- measured baseline vs result;
- attribution method and limitations;
- channel/creative hypotheses supported or rejected;
- audience/market changes observed;
- guardrail outcomes;
- reusable brand/compliance learnings;
- recommendations expressed as hypotheses with conditions, not universal rules.

Expire campaign-specific access, automation, budgets, and temporary processes when their authority ends.

> **Runbook success:** the organization learns which market mechanism deserves more or less investment while producing a defensible commercial/behavioral result — not merely a busier set of channels.

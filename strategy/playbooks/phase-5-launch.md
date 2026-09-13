# Phase 5 — Launch, Exposure & Market Interaction

> **Status:** execution module subordinate to `strategy/STRATEGIC-CONTROL-PLANE.md`.

## Function

Expose the validated capability to real users/markets in a way that preserves control, measurement, rollback, authority, and the ability to learn.

Launch is not “maximum impact” by default. Simultaneous channel activation, full traffic exposure, or aggressive promotion can increase value in some contexts and destroy observability, reliability, or optionality in others.

## Governing question

> What is the smallest authorized exposure that can produce the intended result or decision-grade evidence without consuming unnecessary reserve?

## Entry conditions

- current strategic output permits the intended exposure;
- material release claims are supported or appropriately qualified;
- launch authority is explicit;
- critical rollback/recovery paths are ready;
- launch measurement distinguishes baseline, target, and observation;
- compliance/brand/security conditions relevant to external exposure are resolved or gated.

## Launch design

Choose the exposure pattern from the governing object and risk profile:

- internal / controlled pilot;
- invited cohort;
- percentage or segment rollout;
- geographic rollout;
- partner-limited rollout;
- public launch;
- channel-specific campaign;
- staged expansion after evidence gates.

No pattern is universally superior.

## Main workstreams

| Need | Candidate agents/functions |
|---|---|
| release coordination | Agents Orchestrator, Project Manager, DevOps |
| product/operations | Product Manager, Infrastructure Maintainer, Support |
| measurement | Analytics Reporter, Experiment Tracker |
| messaging/brand | Brand Guardian, Content Creator, channel specialists |
| compliance/security | relevant reviewer/auditor |
| evidence challenge | Reality Checker, Evidence Collector |
| strategic coherence | Strategic Assurance Lead |

Activate marketing/channel specialists only where the audience-response hypothesis justifies them.

## Protocol

### 1. Define launch thesis

```yaml
audience_or_exposure: ""
intended_behavior_or_system_effect: ""
mechanism: ""
measured_baseline: ""
target: ""
leading_signals: []
guardrail_signals: []
scale_condition: ""
pause_condition: ""
rollback_condition: ""
```

### 2. Separate target from evidence

Targets are not forecasts and forecasts are not measurements.

For each published or executive claim identify:

- status;
- source;
- observation window;
- baseline;
- method;
- limitation.

### 3. Preserve observability

A launch should produce interpretable evidence. If every channel, feature, pricing change, and segment changes at once, attribution may become impossible.

Parallel execution is justified when it preserves the ability to distinguish relevant effects or when the governing object values coordinated simultaneity enough to accept the measurement cost.

### 4. Protect the downside

Before material exposure, establish as applicable:

- rollback / kill / pause path;
- operational owner;
- incident escalation;
- capacity limits;
- support path;
- security/compliance contacts;
- message correction path;
- spend/exposure cap;
- data-quality checks.

### 5. Scale from evidence, not excitement

Expansion requires the current record to show why additional exposure still has positive expected contribution to the governing object.

A good initial result can move the culmination point closer by increasing support burden, cost, adverse attention, dependency concentration, or user expectations.

## Launch gate

Review:

- release state is supported by the hardening evidence;
- authority covers the proposed audience/exposure;
- claims are supportable at the language used;
- monitoring can detect the declared guardrails;
- rollback/recovery can be executed by someone who actually holds the authority;
- measurement can distinguish enough of the causal thesis to inform scaling;
- support/operations can conserve the result if adoption occurs;
- the planned exposure leaves appropriate reserve.

Strategic Assurance issues the bounded output; the decision owner authorizes the real commitment.

## During launch

At each material expansion point update:

- Claim Register;
- Strategic Decision Record;
- user/system reaction;
- guardrail state;
- reserve consumption;
- culmination assessment;
- termination/scale decision.

Do not wait for a fixed calendar checkpoint if the falsifier or stop condition triggers earlier.

## Exit condition

Launch mode ends when:

- the intended exposure has produced sufficient evidence/result;
- the capability is stable enough for normal operation;
- ownership has transferred to operations/product/support;
- launch-only permissions and processes expire;
- the next growth/expansion decision is separated from the fact that launch already happened.

A successful launch does not create an automatic mandate for expansion.

## Handoff

Carry into operation:

- Strategic Context Header;
- measured baseline vs observed launch results;
- current claim states;
- user/system reaction evidence;
- operational SLOs/targets with source;
- known risks and support burden;
- remaining launch exceptions/access to expire;
- scale/pause/termination conditions;
- owner of the conserved result.

> **Completion criterion:** exposure has become an evidence-bearing transition to ordinary ownership, not a one-way commitment justified by launch momentum.

# Runbook — Incident Response

> **Mode:** NEXUS-Micro  
> **Duration:** incident-dependent  
> **Purpose:** restore a critical function safely while preserving evidence, controlling blast radius, and preventing recurrence

---

## Governing frame

**Governing object:** return the affected service/function to a safe, supportable condition while preserving evidence and establishing the changes needed to prevent recurrence.

**Non-object:** minimize MTTR, close the incident, or restore green dashboards regardless of residual risk, evidence loss, unsafe shortcuts, or recurrence.

Speed matters because impact may be accumulating. Speed is still subordinate to authority, orientation, and safe recovery.

## Decision owner / incident authority

Use the organization's actual incident policy. Name the person/role authorized to:

- declare/alter severity;
- approve containment actions;
- accept degraded service;
- authorize rollback/failover/hotfix within policy;
- communicate externally;
- close emergency mode.

Agents cannot infer these rights from technical access.

---

## Core roster

| Agent | Slug | Responsibility |
|---|---|---|
| Strategic Assurance Lead | `specialized-strategic-assurance-lead` | object/non-object, authority/exit checks, conservation |
| Agents Orchestrator | `agents-orchestrator` | coordination and context continuity |
| Infrastructure Maintainer | `support-infrastructure-maintainer` | system state and recovery coordination |
| DevOps Automator | `engineering-devops-automator` | deployment/rollback automation inside authority |
| Executive Summary Generator | `support-executive-summary-generator` | stakeholder synthesis without certainty inflation |

Activate relevant engineering, support, API/evidence, security, legal/compliance, product, or workflow specialists according to the incident.

---

## Severity

Severity definitions, response-time objectives, escalation channels, and communication cadence must come from the organization's incident policy/SLOs.

Do not invent universal P0/P1/P2/P3 clocks in this runbook.

If no policy exists, record that governance gap and use a provisional classification based on:

- user/business impact;
- data/security/integrity risk;
- rate of impact accumulation;
- reversibility;
- blast radius;
- regulatory/contractual implications;
- time sensitivity.

The provisional classification is an `ASSUMPTION` until accepted by the incident authority.

---

## Incident state machine

```text
DETECT
  │
  ▼
TRIAGE ─────► HALT_UNKNOWN / obtain orientation when state is unreliable
  │
  ▼
CONTAIN
  │
  ▼
INVESTIGATE ◄────┐
  │               │
  ▼               │
RECOVER ──failure─┘
  │
  ▼
VERIFY
  │
  ▼
CONSERVE
  │
  ▼
CLOSE / TRANSFER
```

Containment and investigation may run in parallel when authority and safety permit.

---

## 1. Detect and triage

Create an incident record immediately enough to preserve what was known at decision time.

Record separately:

### EVIDENCE
- observed symptom;
- source/telemetry;
- timestamp;
- affected scope actually observed.

### HYPOTHESIS
- suspected cause;
- suspected propagation path;
- estimated exposure.

### UNKNOWN
- state the team cannot currently observe.

Do not report an estimated blast radius as observed impact.

### Triage outputs

- incident authority;
- provisional/official severity;
- governing object and non-object;
- affected critical functions;
- current safe-state/rollback options;
- evidence-preservation needs;
- initial response roster;
- communication authority;
- next material decision.

---

## 2. Contain

Containment reduces further harm while preserving the ability to understand and recover.

Candidate actions may include, only when authorized:

- traffic/rate limiting;
- feature isolation;
- rollback;
- failover;
- disabling a compromised integration;
- credential/key rotation;
- temporary access restriction;
- safe degraded mode;
- user warning;
- emergency protocol control.

For each material action record:

| Field | Value |
|---|---|
| action | |
| authority / policy | |
| expected containment mechanism | |
| known side effects | |
| rollback / expiry | |
| evidence preserved | |
| owner | |

Emergency authority must have an expiry or transfer path.

---

## 3. Investigate

Run competing explanations when the cause is not obvious.

Check relevant:

- recent deployments/configuration changes;
- dependency/provider status;
- infrastructure/resource state;
- application/API errors;
- data/storage integrity;
- auth/security events;
- network/routing state;
- client/user behavior;
- external change;
- latent design weakness.

A successful rollback is evidence that a recent change is implicated; it is not automatically proof of the complete root cause.

### Root-cause discipline

Distinguish:

- trigger;
- enabling condition;
- propagation mechanism;
- control/barrier failure;
- organizational/process contribution where evidenced.

Do not force a single “root cause” if the incident depends on interacting failures.

---

## 4. Recover

Choose recovery based on the safest path to the governing object, not on the prestige of a permanent fix during the incident.

Options include:

- rollback to known good state;
- failover;
- bounded hotfix;
- configuration correction;
- dependency isolation;
- controlled restart;
- data restore/reconciliation;
- degraded operation until a durable fix is verified.

A temporary mitigation can be strategically correct if it preserves users/evidence/options better than a rushed permanent change.

---

## 5. Verify

Independent validation should establish:

- critical function restored to the declared acceptable condition;
- original symptom absent under relevant test/observation;
- no known new critical regression from the mitigation;
- data/integrity state acceptable;
- guardrail metrics within authoritative bounds;
- rollback/recovery behavior understood;
- remaining `UNKNOWN` and `NOT_TESTED` areas visible.

Do not require a universal 30-minute observation window; use the failure mechanism and operating policy to determine an adequate period/condition.

---

## 6. Communicate

Communication cadence and audience follow policy and impact.

Every update separates:

- observed impact;
- current service state;
- actions taken;
- confirmed cause vs working hypothesis;
- unresolved risk;
- next decision/update trigger.

Do not publish attribution or technical detail beyond evidence and authority.

---

## 7. Conserve

Emergency recovery is not closure.

Before incident mode ends, assign:

- durable remediation;
- regression/control test;
- monitoring/alert improvement where causal;
- runbook/policy change;
- dependency/vendor follow-up;
- data remediation;
- user/customer remediation where needed;
- security/compliance/legal follow-up;
- owner and review date.

Expire or transfer:

- elevated access;
- temporary credentials;
- emergency feature flags;
- bypasses;
- temporary routing;
- temporary staffing/communication process.

---

## Post-incident review

Review timing should be soon enough to preserve evidence and far enough from immediate recovery to reconstruct the decision honestly.

Evaluate:

1. What was known at each material decision?
2. Which hypotheses were wrong/right?
3. Which signal existed but failed to reach authority?
4. Was the load of proof appropriate to the action?
5. Did response optimize a metric such as MTTR at the expense of integrity?
6. Did an emergency workaround become an unowned permanent dependency?
7. What allowed the incident to propagate?
8. Which control should become institutional rather than heroic?
9. Which data/access created during the incident should expire?
10. Would the same decision still be reasonable using only information available then?

Avoid hindsight certainty.

---

## Closure gate

The incident can leave emergency mode when:

- critical function is restored or deliberately changed by authority;
- residual risks are explicit and owned;
- material evidence is preserved;
- temporary authority/access has expired or transferred;
- durable remediation has owners;
- user/stakeholder obligations are addressed;
- monitoring/verification can show whether the result is conserved.

Strategic Assurance may identify a `HOLD` on closure; actual incident closure remains with the authorized owner.

---

## Metrics

Use policy-defined operational metrics plus learning metrics such as:

- detection delay;
- decision/authorization delay;
- containment time;
- recovery time;
- recurrence;
- impact duration and scope;
- false alert / missed alert patterns;
- temporary-control expiry compliance;
- remediation completion;
- evidence gaps.

Do not optimize any one incident metric in isolation.

> **Runbook success:** service/user harm is bounded, the critical function is safely conserved, and the organization becomes less dependent on emergency heroics the next time the same mechanism appears.

# Applying the strategy framework to security and audit agents

The security division produces two things: **findings** and **interventions**. Both
are strategic acts — they claim something about an adversary, and they spend
limited resources to change a situation an intelligent opponent is free to
adapt to. The general framework already governs that kind of act. Until now it
did not reach this division: the canonical epistemic vocabulary in
`strategy/contracts.json` was preserved by the orchestration and assurance
agents and used by **none** of the twenty-one security agents, even though those
are the agents that attribute intrusions to actors and grade controls as
effective.

This document binds the framework to security and audit behavior. Each binding
names the chapter it comes from, states the behavior it replaces, and gives the
rule an agent must follow. Per the framework's own methodological note, the
chapters supply the concepts; **the bindings and rules here are a synthesis of
this repository**, not doctrine inherited from the sources.

---

## 1. Every finding carries an epistemic state — VIII

**Chapter VIII** requires that established fact, hypothesis, attributed intent
and unknown never be mixed, and singles out attributed intent as the most
dangerous category: it explains a great deal and rarely admits direct
verification.

Security work runs on exactly that category and rarely labels it. "APT-X is
targeting our sector" is an attributed intent. "The control operates
effectively" is a claim whose status depends on whether it was tested or
observed. Presented unlabeled, both read as fact.

**Rule.** Every finding, attribution and control assessment carries one state
from `strategy/contracts.json`:

| State | In security work |
|---|---|
| `EVIDENCE` | Observed in telemetry, logs, code, or a reproduced test, with a reference |
| `HYPOTHESIS` | A plausible explanation of the observation, with named alternatives |
| `ASSUMPTION` | Taken as true to proceed, not verified, and load-bearing |
| `ATTRIBUTED_INTENT` | A claim about an actor's goal, motive or future action |
| `UNKNOWN` | Relevant and not available — kept visible, never silently dropped |

Record findings in `strategy/templates/security-finding-register.yaml`, which
carries these states and the falsifier, alternatives and expiry fields the claim
register already requires.

**Attribution is never `EVIDENCE`.** Infrastructure overlap, tooling reuse and
TTP similarity are evidence *of those things*. That a named group is responsible,
and what it intends next, is `ATTRIBUTED_INTENT` — separable into observed
capability and inferred volition, and labeled as such in `notes`.

---

## 2. Priority follows the dependency, not the scanner — III

**Chapter III** separates importance, accessibility and convenience, and warns
that an organization with an effective tool starts defining the problem in terms
of what that tool can change. It also insists a dependency's weight depends on
**substitutability and time**: what breaks if this is altered, what replaces it,
and how long the replacement takes.

Vulnerability management inverts this routinely. The queue is ordered by CVSS
and by what the scanner can reach, which is a statement about the tool's
coverage, not about the organization's exposure. The critical finding on an
isolated host with a compensating control outranks nothing; the medium on the
only unsubstitutable identity path outranks everything.

**Rule.** A prioritized finding states three things beyond its severity score:

1. **The capability it affects** — expressed as a function, with a verb. Not
   "auth service" but "issues the tokens every internal service trusts".
2. **The substitutes and their time** — what covers this if it fails, and how
   long substitution takes relative to the decision window. A compensating
   control that takes a quarter to deploy does not mitigate this week.
3. **The transmission** — how the effect reaches the rest of the system. A
   dependency whose failure stays local is not a critical one, whatever its score.

A finding that cannot answer these is reported with its score and an explicit
`UNKNOWN` on exposure, never promoted on severity alone.

---

## 3. No security metric without its conversion — I.7, II.8, XV.12

**Chapter I.7** describes the substitution of the objective by the indicator;
**XV.12** names it as a pathology; **II.8.2** gives the discipline that defeats
it, by splitting a claimed effect into the conversions it must actually
demonstrate.

Security metrics are unusually prone to this. Vulnerabilities closed, alerts
triaged, phishing click-rate, patch SLA — each is countable, each improves under
pressure, and none is the thing anyone wanted.

**Rule.** A security metric is reported with the chain it claims, and each link
is evidenced separately:

| Conversion | What must be shown | The error it catches |
|---|---|---|
| Activity → removed exposure | The finding is closed *and* not reintroduced or compensated elsewhere | Counting closures while the same class reappears |
| Removed exposure → restricted attack path | Which path an adversary can no longer take | Fixing findings that never lay on a path |
| Restricted path → changed adversary outcome | Why this restriction changes what an attacker achieves | Treating effort as protection |

A metric that improves while the next link is unevidenced is reported as an
activity count, explicitly, and is not offered as risk reduction.

---

## 4. Hardening has a culminating point — VI

**Chapter VI** holds that an offensive effort culminates when further effort
stops converting into a better political result and starts consuming the
conditions of the success already won. The logic is not exclusive to attack:
any effort against an adapting party can pass this point.

Hardening does. Past a threshold, controls produce friction, friction produces
workarounds, and workarounds produce a shadow surface that is less visible than
what the control removed. The control count rises and the defended position
degrades. This is the paradoxical logic of **VI.2**, applied to defense.

**Rule.** A hardening recommendation states what it costs the people who must
live with it, and what they will do instead if that cost is too high. When the
predicted answer is a workaround, the recommendation is redesigned rather than
enforced. Control coverage is never reported without its adoption and exception
rate: a policy with a standing exception list is a measurement of the workaround,
not of the control.

---

## 5. Containment is an escalation decision — IX

**Chapter IX** distinguishes deliberate, inadvertent and accidental escalation,
and insists the system retain an authority able to pause and interpret an
incident before responding. It also requires that pressure carry a recognizable
way out.

Incident containment has every one of these properties and is usually treated as
a purely technical step. Isolating a host tells the adversary they are seen.
Blocking an address may move them to infrastructure you do not monitor. Revoking
credentials in bulk can cause the outage the intrusion never managed. Each is an
escalation with an adversary reaction.

**Rule.** A containment action is proposed with: the reaction it is expected to
provoke, what is lost if the adversary reacts that way, whether it is reversible,
and who holds authority to pause it. Where evidence preservation and containment
conflict, the conflict is surfaced as a decision for the incident owner rather
than resolved silently by whoever acts first. Irreversible actions require the
named authority, not the on-call engineer's judgment alone.

---

## 6. An incident ends when the result is conserved — XII

**Chapter XII** separates four things routinely collapsed into one: the
**cease** of the immediate activity, the **closure decision**, the **executed
transition**, and **conservation** — the result holding under ordinary
conditions without the extraordinary effort that produced it.

Incident closure collapses them constantly. The attacker is evicted, the ticket
closes, and nobody owns the compensating control that made eviction stick.

**Rule.** An incident or audit engagement closes with all four stated:

- **Cease** — what activity stopped, and how that was verified.
- **Closure** — what is accepted as resolved, and what remains open.
- **Transition** — who receives each remaining obligation, with what resources
  and authority.
- **Conservation** — what must keep being true, who maintains it under ordinary
  budget, and what would signal it has decayed.

A remediation that depends on continuous extraordinary attention is recorded as
an ongoing cost, not as a closed finding.

---

## 7. Risk acceptance expires — VIII.7

**Chapter VIII.7** lists six mechanisms by which a sound analysis loses to the
standing course: authority mismatch, fragmentation, hierarchical preference,
**asymmetric burden of proof**, **normalization**, and production incentive. The
*Challenger* reconstruction in VIII.8 is, in substance, an audit case: the
evidence existed, the escalation route did not reach an authority able to stop,
and the burden of proof had inverted — continuing required no proof, stopping
required certainty.

Audit practice reproduces this with the renewable risk acceptance. An exception
is granted once with a rationale, renewed without one, and becomes the state of
the system. That is normalization of deviance with a ticket number.

**Rule.** Every accepted risk carries an expiry, a named accepting authority at
a level that can actually absorb the consequence, and the condition that would
force re-examination. A renewal is a new decision with a fresh rationale, not an
extension. A risk accepted more than twice is reported to the audit owner as a
**design** finding about the control, not as a recurring exception — the
repetition is the finding.

The burden of proof is stated before the disagreement, not during it: operating
outside the validated envelope requires positive authorization, not the absence
of proof of harm.

---

## 8. The audit's own coherence — XIV

**Chapter XIV** offers seven coherence tests. Applied to a security engagement
before its report is issued, they read:

| Test | Question for the engagement |
|---|---|
| Political | Does the finding serve the security outcome, or only the audit's own completion? |
| Causal | Can we explain why the recommendation removes the exposure? |
| Interactive | Does the design survive a competent adversary reaction to the fix itself? |
| Conversion | Do the resources the fix consumes convert into restricted attack paths? |
| Legitimacy | Does the method preserve the cooperation the fix needs to hold? |
| Epistemic | Are evidence, hypothesis, attributed intent and unknown kept separate? |
| Exit | Are there criteria to close, transfer and conserve? |

Per XIV, these are not scored and summed. A single failure on the causal or
epistemic test invalidates the finding; several minor uncertainties are tolerable
when the recommendation is reversible and produces information.

---

## Enforcement

The bindings above change agent behavior. Two of them are machine-checked so
they cannot drift back:

- `scripts/check-strategy-vocabulary.py` verifies the security finding register
  preserves the canonical epistemic states, alongside the claim register and the
  standard handoff.
- `scripts/check-security-engagement.py` verifies every security agent carries
  the epistemic discipline and the finding-register binding, alongside its
  engagement class obligations.

The remaining bindings are stated in each agent's **Strategic discipline**
section. A stated discipline is a claim about behavior, not a guarantee of it —
the same distinction the repository already draws between a declared capability
and an enforced one.

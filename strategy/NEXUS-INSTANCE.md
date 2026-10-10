# NEXUS instances: planning, evidence and replay

This is an offline contract engine. It does not launch models, call tools, write
production data, authenticate an owner, or lift either HTP network's HOLD.
The fixture demonstrates software behavior; live model quality remains unmeasured.
Use it to inspect a proposed team and validate recorded events before writing a
host integration. Existing `install.sh --runbook` remains profile installation.

## Run the bounded pilot

From the repository root:

```bash
python3 scripts/nexus-instance.py validate examples/nexus/strategic-decision.instance.json
python3 scripts/nexus-instance.py plan examples/nexus/strategic-decision.instance.json \
  --at 2026-09-15T12:00:00Z
python3 scripts/nexus-instance.py replay examples/nexus/strategic-decision.instance.json \
  --events examples/nexus/strategic-decision.events.jsonl --output /tmp/nexus-checkpoint.json
python3 scripts/nexus-instance.py replay examples/nexus/strategic-decision.instance.json \
  --events examples/nexus/strategic-decision.events.jsonl \
  --checkpoint /tmp/nexus-checkpoint.json --output /tmp/nexus-replayed.json
python3 scripts/nexus-options.py examples/nexus/options.json
python3 scripts/evaluate-nexus.py --runs examples/nexus/host-trials.json
```

`plan` requires an explicit clock for reproducible expiry checks. Replay uses
recorded event times. A checkpoint must match a prefix of the complete supplied
event history; the engine reconstructs the state instead of trusting a mutable
projection. Repeating an identical event ID is idempotent; changing its content
is an error. Output uses atomic replacement. This is a single-writer replay
format, not a concurrent event database. Use separate output paths for writers.

## Instance contract

`schema_version: 1` is validated by `scripts/nexus-instance.py`.

| Field | Required meaning |
|---|---|
| `id`, `runbook_ref`, `doctrine_sha256` | Instance identity, canonical candidate roster and pinned doctrine |
| `mandate` | Named owner/reviewers, authority reference, expiry and scope: `offline-analysis`, or `local-relay` for execution through [NEXUS Relay](../relay/DESIGN.md) |
| `objective` | Purpose ID, valuable result, non-object, success condition and hard constraints |
| `decision_state` | Canonical NEXUS decision; distinct from task completion |
| `budget` | Total cost, uncommitted reserve and deadline, in one consistent declared cost unit |
| `claims` | Typed statements, revisions, source references, source roots, scope, expiry and claim dependencies |
| `tasks` | Assigned catalog agent, level/vector, purpose reference, mechanism and task dependencies |
| `open_conditions` | Named HOLD conditions, classification and affected task IDs |
| `option_analysis` | Optional non-additive comparison with scenario overrides |

Each task also defines `claim_revisions`, `evidence_scope`, `cost_limit`,
`attempt_limit`, `retry_rationale`, `resource_scope` and `acceptance_predicates`,
and may declare `asserts`: the shared keys (for example `pricing.seat_usd` or
`platform.first`) on which its accepted result must state a value.
Resource-scope strings are logical exclusive-resource identifiers. They are not
filesystem permissions, sandbox paths or tool grants. A live adapter must resolve
and enforce resource identity; two different labels for the same file are not
isolated resources merely because this planner cannot recognize the alias.

The candidate roster comes from the existing runbook and canonical catalog. An
instance must contain at least one task; empty task plans are rejected. Only
explicit tasks are active. Independent ready tasks may run in parallel in a
future host integration; the offline engine merely validates their recorded
starts. It reserves concurrent budgets and prevents overlapping logical resources.

## Evidence and levels

Every task points to the superior purpose and states its mechanism. The engine
checks links and vocabulary, not the truth of a causal explanation. Task edges,
claim dependencies and source lineage remain separate relationships.

Claim revisions invalidate consumer pins and mark downstream claims for review.
Expiry propagates through claim dependencies. Reviewers explicitly revise claims
and rebind task inputs; rebind cannot drop an inconvenient claim or reset consumed
budget. Scope checks traverse the entire claim ancestry during validation and
replay, including explicit rebinding of revised claims: every premise must match the task scope or be explicitly shared. Marking
only a derived conclusion `shared` cannot transfer a Solana-only premise into an
Arbitrum task. A host must separately verify whether each `shared` classification
is defensible; this runner provides no scope-transfer override.

Accepted task results have a monotonic `result_revision`. Each start records the
direct predecessor revisions it consumes in `dependency_revisions`. Rebinding a
task marks its already-started direct and transitive consumers `inputs_stale`,
even if they previously passed QA. The flag persists after the predecessor is
repeated successfully. Independent tasks remain unaffected. A named owner or
reviewer must explicitly rebind each stale consumer and rerun it; this retains
spent cost, attempts and result revision history. Pending consumers that have not
started consume the current predecessor revisions when they start.

Running stale consumers retain their reservation until `finish` reconciles actual
cost. An accepted finish can record successful QA but cannot clear stale inputs:
`TASK_INPUT_REVIEW` and any `DEPENDENCY_REVISION` blocker prevent reuse or successful
instance closure. Rebinding a running task remains prohibited.

Checkpoints produced before task result revisions were introduced must be
regenerated by replaying the complete event history without the old checkpoint.
Old projections are not silently upgraded or trusted. A history that previously
closed over obsolete dependent results now fails and requires reviewed correction.

Promotion to `EVIDENCE` requires a new source reference and a recorded reason.
This is a necessary recording condition, not proof that the new reference is
true, independent or sufficient. The shared-source report identifies common
lineage; it does not score corroboration. Canonical epistemic states are taken
from `strategy/contracts.json`, including `ATTRIBUTED_INTENT`.

## Event contract

Every JSONL event has a unique `id`, a zoned ISO `at`, a named `issuer`, and `type`.
The engine checks issuer labels against the instance; the live host must supply
authentication and independently verify the mandate. JSON labels are not signatures.

| Event | Additional fields and effect |
|---|---|
| `start` | `task_id`, `reserved_cost`, optional `model_id`; checks dependencies, HOLD, scope/expiry, budget, attempts, resource ownership and unresolved assertion conflicts among the task's direct dependencies |
| `finish` | `task_id`, `actual_cost`, `accepted`, `evidence_refs`; accepted outputs need all named `predicate_results` true and an issuer who is the owner or a reviewer and **not the task agent**. The agent may report only a non-accepted finish. Every reference becomes a recorded task output. An accepted finish carries `asserts` with exactly the task's declared keys (string, number or boolean values) |
| `hold` | `condition` with ID, classification, reason and `task_ids`; blocks affected work and its consumers |
| `resolve_hold` | Condition ID, reason and evidence; owner only; fatal defects require redesign |
| `decision` | Canonical state and reason; owner only; favorable QA cannot clear HOLD |
| `claim_revision` | Complete next claim revision and reason; owner/reviewer only. Promotion to `EVIDENCE` needs a new reference **and** a new source root, and no added reference may be a recorded task output. Widening or transferring a scoped claim (any scope change away from a non-`shared` scope) needs the owner and `evidence_refs`; narrowing a `shared` claim stays open to reviewers |
| `rebind_claims` | Task ID, exact set of input claims with reviewed revisions, and reason; resets the task for rerun and invalidates its consumers |
| `dissent` | Objection, evidence references and residual-risk owner; preserved in history and kept open until answered |
| `dissent_response` | Owner only: `dissent_id` (the dissent event ID), `disposition` (`UPHELD`, `RISK_ACCEPTED` or `REFUTED`), `response`, `risk_owner`, `evidence_refs`. Each dissent is answered once |
| `resolve_conflict` | Owner only: `key` with a current conflict, chosen `value`, `reason`, `evidence_refs`. Holds while the competing results are unchanged; any new result on the key reopens it |
| `override_verdict` | Owner only: `proposer_task_id` whose challenger verdict is negative, `reason`, `evidence_refs`, and a future `expires`. Opens the P8 gate until expiry or until any challenger verdict on that task changes; never rewrites the verdict, and cannot open a gate that has no verdict |
| `release_reserve` | Owner only: positive `amount` not exceeding the remaining reserve, named `contingency`, `reason`, `evidence_refs`. Released reserve becomes committable budget |
| `close` | Evidence and closure record; mandate and deadline must be current, with at least one task and all planned work complete and current, and no unanswered dissent |
| `terminate` | Outcome, reason, evidence and closure record; cancels unnecessary/pending work without claiming it succeeded |

A closure record contains `achieved`, `outstanding`, `accountable`, `on_breach`
and `conservation_resources`. Termination can record sufficient result, failure,
expiry, redesign or rejection. Running work must be reconciled first.
`SUFFICIENT_RESULT` is refused while a `FATAL_DEFECT` or `PENDING_EVIDENCE`
condition is open, while any dissent is unanswered, or unless the decision is
`PROCEED`/`PROCEED_WITH_CONDITIONS`: sufficiency cannot compensate a fatal defect,
relabel a negative or held decision, or close over missing evidence. It may still
cancel planned work when the need was met another way. Use the matching negative
outcome otherwise; negative outcomes remain available with open dissent. No new event
may reopen a closed instance: create a reviewed successor with new assumptions.

A scoped HOLD does not stop independent work under an existing mandate. A global
HOLD without scoped conditions blocks all starts. Actual cost overruns are recorded
rather than discarded; subsequent starts are blocked as appropriate. A task PASS
never modifies the strategic decision. Uncertain evidence may support bounded
analysis; its presence is not authorization for the action being analyzed.

## Independent judgment

The 2026-10-10 stress test showed that ordering guarantees did not protect the
independence of the judgment. Eight rules now hold in the engine:

1. **No self-acceptance.** A task agent cannot accept its own work, even if it is
   also listed as a reviewer.
2. **Outputs are not corroboration.** References attached to any `finish`,
   accepted or not, cannot promote a claim to `EVIDENCE`; promotion also needs a
   new source root, not only a new reference on an old lineage.
3. **Scope moves cost as much as promotion.** Widening or transferring a scoped
   claim needs the owner and evidence; it can no longer launder a Solana-only
   premise into an Arbitrum task through a reviewer's reason string.
4. **Sufficiency cannot relabel.** See the termination rule above.
5. **Dissent needs an answer.** Open dissent blocks success closure and
   sufficient-result termination until the owner records a disposition.
6. **The reserve has conditions of use.** Only `release_reserve` moves reserve
   into committable budget; `plan` reports the remaining reserve, released total
   and open dissent.
7. **Subplans must be compatible.** When current accepted results state
   different values for the same shared key, `plan` lists the conflict under
   `assertion_conflicts`, a consumer of those results cannot start
   (`ASSERTION_CONFLICT:<key>`), and neither success closure nor
   `SUFFICIENT_RESULT` is possible until the owner records `resolve_conflict`.
   Negative outcomes stay available. Numbers compare by value (`39` equals
   `39.0`). `plan` also lists `shared_model_tasks`: agreement among runs of one
   model is not independent corroboration.

8. **Proposals face their challenger first.** `strategy/challenger-pairs.json`
   names proposer/challenger pairs (today: Macro Regime Alpha and Quant Research
   and Alpha Validation). Every task run by a proposer needs a task run by its
   challenger that depends on it and asserts `verdict:<proposer task id>` with a
   canonical decision state. A verdict counts only from an accepted, current run
   that consumed the proposer's current result. Until it is `PROCEED` or
   `PROCEED_WITH_CONDITIONS`, every other task downstream of the proposer is
   blocked (`CHALLENGER_PENDING`, `CHALLENGER_VETO` or `CHALLENGER_CONFLICT`
   with the proposer task id), the owner cannot record a favourable `decision`
   over a veto or split, and neither success closure nor `SUFFICIENT_RESULT` is
   possible. Only the pair may consume the proposer's output before the verdict:
   the challenger to judge it, the proposer to redesign it as a new task with
   its own challenger task. Disagreeing challenger runs resolve through
   `resolve_conflict` to one of their own verdicts; any other outcome is an
   `override_verdict`, which only the owner can issue, with evidence and an
   expiry. Neither the owner nor any reviewer may be an agent of the pair.
   `plan` reports every gate under `challenger_gates`.
   `scripts/check-challenger-pairs.py` keeps each pair rostered together and
   out of its excluded runbooks (the HTP Gate 0 runbook for this pair).

These rules check who issued what and which declared values disagree. They do
not detect contradictions on keys no task declared, authenticate issuers,
establish that a new source root is truly independent, or judge whether a dissent
answer or conflict resolution is adequate. A live host must still authenticate the mandate.

## Multifactor comparison

Options declare admissibility and fatal defects before numerical comparison.
Inadmissible, fatal or pending-review options cannot enter the admissible frontier.
Each selected factor specifies whether higher or lower values are preferred.
Values carry MEASURED, TARGET, ESTIMATE, HYPOTHESIS or UNKNOWN status. Measured
values require source, observation window, method and baseline. Unknown values
remain incomparable. Scenario overrides expose changes in the undominated set.
Each dominance edge reports its `evidence_basis` (the statuses it rests on) and
`measured_only`. Dominance built on TARGET, ESTIMATE or HYPOTHESIS values is a
conditional comparison, not measured superiority. `measured_only` describes supplied
labels; it does not authenticate the measurements or establish causality.

There is no weighted score. Dominance is conditional on the declared factors and
values; a short list of factors is not a complete strategy. Probability, confidence
and impact must be assessed separately by the owner/reviewer. Numeric fixture
values illustrate mechanics only and are not a forecast of this architecture.

## Host evaluation remains outstanding

The twelve cases in `examples/nexus/evaluation-cases.json` define the starting
protocol, written up in [NEXUS-MEASUREMENT-PROTOCOL.md](NEXUS-MEASUREMENT-PROTOCOL.md).
`host-trials.json` and `host-judgments.json` are deliberately empty and the
evaluator returns `NOT_MEASURED`.

Comparing real sessions takes two files, not one. A **trial** row records
`submission_id`, `case_id`, `trial_id`, `variant`, `model_version`, `host_version`,
`started_at`, `inputs_hash`, `budget_policy_ref`, `evidence_ref`, `operator`, and
the five run counters: `cost_usd`, `tokens_total`, `wall_time_seconds`,
`invalid_decisions`, `rework_cycles`. A **judgment** row records only
`submission_id`, `reviewer`, `judged_at`, `evidence_ref` and the four judged
metrics: `factual_errors`, `fatal_defects`, `constraint_violations` and
`evidence_coverage` as `{covered, required}`.

The split reduces direct metadata leaks but does not prove blinding: a judgment naming its variant, case, trial or model is
rejected, as is one whose reviewer identifier matches any trial operator. `nexus-blind.py seal`
builds the review packet under opaque submission ids and refuses artifacts that
narrate their own pipeline.

Each case/trial needs all three variants with the same inputs, budget policy, host and
model. Pre-declare the cases and trial count, preserve raw outputs, and separate
development cases from held-out ones. The evaluator reports the metrics separately
with their spread, names incomplete pairs and unjudged submissions, and produces
no score or ranking. It neither manufactures model responses nor claims
statistical superiority. Fatal defects remain separate and uncompensated.
Component ablations and institutional self-test exercises require additional
observed work.

For a first live adapter, verify Claude discovery and resolved tools, authenticate
the mandate outside this engine, enforce expiry and side-effect boundaries, bind
resource identifiers, preserve the full event history, and observe actual budget
consumption. Do not import the fixture's dates or authority into a real project.

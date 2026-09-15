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
| `mandate` | Named owner/reviewers, authority reference, expiry and `offline-analysis` scope |
| `objective` | Purpose ID, valuable result, non-object, success condition and hard constraints |
| `decision_state` | Canonical NEXUS decision; distinct from task completion |
| `budget` | Total cost, uncommitted reserve and deadline, in one consistent declared cost unit |
| `claims` | Typed statements, revisions, source references, source roots, scope, expiry and claim dependencies |
| `tasks` | Assigned catalog agent, level/vector, purpose reference, mechanism and task dependencies |
| `open_conditions` | Named HOLD conditions, classification and affected task IDs |
| `option_analysis` | Optional non-additive comparison with scenario overrides |

Each task also defines `claim_revisions`, `evidence_scope`, `cost_limit`,
`attempt_limit`, `retry_rationale`, `resource_scope` and `acceptance_predicates`.
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
replay: every premise must match the task scope or be explicitly shared. Marking
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
| `start` | `task_id`, `reserved_cost`; checks dependencies, HOLD, scope/expiry, budget, attempts and resource ownership |
| `finish` | `task_id`, `actual_cost`, `accepted`, `evidence_refs`; accepted outputs need all named `predicate_results` true |
| `hold` | `condition` with ID, classification, reason and `task_ids`; blocks affected work and its consumers |
| `resolve_hold` | Condition ID, reason and evidence; owner only; fatal defects require redesign |
| `decision` | Canonical state and reason; owner only; favorable QA cannot clear HOLD |
| `claim_revision` | Complete next claim revision and reason; owner/reviewer only |
| `rebind_claims` | Task ID, exact set of input claims with reviewed revisions, and reason; resets the task for rerun and invalidates its consumers |
| `dissent` | Objection, evidence references and residual-risk owner; preserved in history |
| `close` | Evidence and closure record; mandate and deadline must be current, with at least one task and all planned work complete and current |
| `terminate` | Outcome, reason, evidence and closure record; cancels unnecessary/pending work without claiming it succeeded |

A closure record contains `achieved`, `outstanding`, `accountable`, `on_breach`
and `conservation_resources`. Termination can record sufficient result, failure,
expiry, redesign or rejection. Running work must be reconciled first. No new event
may reopen a closed instance: create a reviewed successor with new assumptions.

A scoped HOLD does not stop independent work under an existing mandate. A global
HOLD without scoped conditions blocks all starts. Actual cost overruns are recorded
rather than discarded; subsequent starts are blocked as appropriate. A task PASS
never modifies the strategic decision. Uncertain evidence may support bounded
analysis; its presence is not authorization for the action being analyzed.

## Multifactor comparison

Options declare admissibility and fatal defects before numerical comparison.
Inadmissible, fatal or pending-review options cannot enter the admissible frontier.
Each selected factor specifies whether higher or lower values are preferred.
Values carry MEASURED, TARGET, ESTIMATE, HYPOTHESIS or UNKNOWN status. Measured
values require source, observation window, method and baseline. Unknown values
remain incomparable. Scenario overrides expose changes in the undominated set.

There is no weighted score. Dominance is conditional on the declared factors and
values; a short list of factors is not a complete strategy. Probability, confidence
and impact must be assessed separately by the owner/reviewer. Numeric fixture
values illustrate mechanics only and are not a forecast of this architecture.

## Host evaluation remains outstanding

The twelve cases in `examples/nexus/evaluation-cases.json` define a starting
protocol. `host-trials.json` is deliberately empty and the evaluator returns
`NOT_MEASURED`. To compare real sessions, supply rows containing:

- `case_id`, `trial_id`, `variant` (`single_agent`, `fixed_team`, `nexus_instance`);
- `model_version`, `host_version`, `started_at`, `inputs_hash`, `budget_policy_ref`;
- `evidence_ref`, `reviewer`, observed `cost` and `latency_seconds`;
- explicit reviewer booleans for `correct_reaction`, `uncertainty_preserved`,
  `traceable` and `fatal_violation`.

Each case/trial needs all three variants with the same inputs and budget policy.
Use a predeclared review rubric, preserve raw outputs and separate development
cases from held-out cases. The evaluator reports descriptive counts, missing case
coverage, median cost and latency. It neither manufactures model responses nor
claims statistical superiority. Fatal violations remain separate. Component
ablations and institutional self-test exercises require additional observed work.

For a first live adapter, verify Claude discovery and resolved tools, authenticate
the mandate outside this engine, enforce expiry and side-effect boundaries, bind
resource identifiers, preserve the full event history, and observe actual budget
consumption. Do not import the fixture's dates or authority into a real project.

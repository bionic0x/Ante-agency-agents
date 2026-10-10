# NEXUS Overdrive: a measured, self-improving brain

**Status: Phase 1 (measurement) in progress. Nothing here claims that NEXUS or
Overdrive improves results.** This charter defines what would show that, what
would show the opposite, and what the agency may change about itself in between.

## Purpose and non-object

**Purpose.** Let the agency plan, run, integrate and improve its own work with
less owner effort per decision, while every improvement is shown on evidence the
improver did not write and every consequential step keeps a named human gate.

**Non-object.** Autonomy for its own sake, throughput bought with fatal defects,
or a self-improvement loop that grades itself. A faster agency that is wrong more
often has not been overdriven; it has culminated.

## The four parts of the brain

| Part | Today | Overdrive target | Human gate that stays |
|---|---|---|---|
| **Planner** | An instance is written by hand | A planner agent drafts the instance from an objective brief; the engine validates it and a plan linter checks critical path, budget headroom and shared-key coverage | The owner adopts the instance (pins its hash in the mandate) |
| **Live orchestrator** | The pilot runs one task at a time | A scheduler starts every ready task in parallel under engine admission, resource scopes and budget reservations | Acceptance of every result (P1) |
| **Synthesis / decision** | Rules block bad closures (P1–P7) | A decision brief assembles accepted results, assertion conflicts, open dissent, shared-model warnings and evidence lineage for the owner | `resolve_conflict`, `dissent_response`, `decision`, `close` |
| **Contract engine** | Schema v1, offline replay | Extended in place; v1 instances, events and tests keep working | Unchanged: the engine never executes or accepts |

**Self-improvement.** The agency may propose changes to its own profiles,
runbooks and code. A proposal becomes a pull request only after it passes the
release gate and the improvement gate below. A human merges it.

## Phases, exits and kill criteria

The order follows the doctrine: orient before accelerating (IV.3), measure
before claiming a gain (VIII.12), consolidate before extending (XI.10).

### Phase 1 — Measurement

Build what makes the existing protocol executable:

- **Case packs** (`scripts/nexus-casepack.py`): each case frozen with brief,
  materials, constraints, permitted evidence, defect rubric and a machine-checkable
  output contract. `inputs_hash` is the hash of the frozen pack. Packs are split
  into `development` and `held_out`.
- **Trial runner** (`scripts/nexus-trial.py`): runs `single_agent`,
  `fixed_team` and `nexus_instance` on the same pack, model and budget policy, and
  writes trial rows that `evaluate-nexus.py` accepts. The `nexus_instance` variant
  pauses for owner acceptance like a live run.
- **Improvement gate** (`scripts/nexus-improve.py`): refuses a proposal that
  touches the protected evaluator, and refuses one that regresses on held-out
  evidence.

- **Campaign** (`scripts/nexus-campaign.py`): fixes the exit and the kill rule
  below in code before results exist, plans the missing runs with their spend
  ceiling, and returns `INCOMPLETE`, `PROCEED_TO_PHASE_2` or `REDIRECT`. Pack
  authors follow [`NEXUS-CASEPACK-AUTHORING.md`](NEXUS-CASEPACK-AUTHORING.md).

**Exit.** At least six held-out packs authored by someone other than the
improver, run with all three variants, two trials each, under one model and one
budget policy, on a live host, blind-judged through `nexus-blind.py`.

**Kill or redirect.** If `nexus_instance` does not avoid more fatal defects than
`fixed_team` on held-out packs, Phase 2 does not speed up the control plane.
Overdrive then redirects to improving fixed teams and profiles, which the same
gate can still measure.

### Phase 2 — Throughput

Parallel orchestrator and plan linter. **Exit:** median wall time per held-out
pack falls with fatal defects and constraint violations no worse than Phase 1.
**Kill:** any increase in fatal defects that survives a rerun.

### Phase 3 — Autonomy with human gates

Planner agent, decision brief and the profile optimizer: agents propose profile
and runbook edits, scored on development packs and admitted only through the
improvement gate on held-out packs. **Exit:** owner events per closed instance
fall with no regression in judged metrics. **Kill:** the owner can no longer
reconstruct why a decision was taken from the brief and the event history.

## The improvement gate

A self-improving system fails in a characteristic way: it improves the measure
instead of the work (XV.12). Three rules prevent that.

1. **The improver cannot touch the judge.** Paths listed in
   `strategy/overdrive-protected.json` — held-out packs, the evaluator, the blind
   sealer, judgments, the improvement gate itself, the engine's judgment rules,
   the release gate and CI — may not change in a self-improvement proposal. Changing
   them needs a separate, human-authored pull request.
2. **No composite score.** A proposal is admitted only if, on held-out packs,
   it is no worse than the baseline on every metric beyond the declared tolerance
   and better on at least one. Fatal defects get zero tolerance.
3. **Development and held-out stay apart.** Optimizers may read development
   packs freely. Held-out results are reported only as a pass or fail of the gate,
   so the optimizer cannot fit to them.

The gate outputs `PROPOSE` or `REJECT` with reasons. It never merges.

## Limits

Measurement here records what the runner and reviewers report; it does not
authenticate costs or reviewer independence. Six packs do not support claims of
statistical superiority, and the gate's tolerance rule is a decision convention,
not a significance test. Live trials need a model key and money; the runner
does not spend either without an explicit operator command.

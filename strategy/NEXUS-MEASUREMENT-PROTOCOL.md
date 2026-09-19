# NEXUS measurement protocol

The instance engine plans, replays and terminates. Whether it improves task performance has not been measured. `examples/nexus/host-trials.json` is empty and `evaluate-nexus.py`
therefore reports `NOT_MEASURED`. That is the honest state, and this document is
how it stops being the state — not by asserting a gain, but by running something
that could have shown its absence.

**Status: NOT_MEASURED.** Nothing below has been executed. A protocol is a plan
for collecting evidence, not evidence.

## What is being compared

Three ways of answering the same case, holding everything else fixed.

| Variant | Definition | What it isolates |
|---|---|---|
| `single_agent` | One session, one general profile, no delegation | The model's unaided performance on the case |
| `fixed_team` | A roster fixed in advance, invoked in a fixed order, no replanning | Whether specialization alone accounts for any difference |
| `nexus_instance` | The roster and order the instance engine plans, with its budgets, HOLDs, claim expiry and termination contract | Whether the *control plane* accounts for any difference |

`fixed_team` exists because without it a gain by `nexus_instance` over
`single_agent` is uninterpretable: specialization and additional inference can themselves change the output. A
difference from the single-agent baseline alone cannot isolate orchestration. The comparison that
matters is `nexus_instance` against `fixed_team`; `single_agent` is a baseline, not an assumed performance floor.

## What is held constant

Every paired trial fixes all of these, and `evaluate-nexus.py` refuses a pair
whose rows disagree on any of these four fields:

- `model_version` — the same model for all three variants, recorded per row.
- `inputs_hash` — the same case material and the same initial context. A variant
  that starts with extra context is not answering the same question.
- `budget_policy_ref` — the same cost and wall-time ceiling. Without a shared
  ceiling, `nexus_instance` can buy quality with spend and call it orchestration.
- `host_version` — the same host version within each paired trial.

Cases come from `examples/nexus/evaluation-cases.json`: twelve scenarios, each
with a stated `expected_behavior`. These are scenario outlines, not complete
benchmark material or calibrated judging rubrics. Before live trials, freeze the
full task inputs, permitted evidence, constraints and defect-counting rubric for
each selected case. Equal hash/reference labels are checked by the evaluator;
their actual contents and budget enforcement require independent verification.

## The nine metrics, and why there is no tenth

Five are supplied by the runner under a shared instrumentation contract:

| Metric | Definition |
|---|---|
| `cost_usd` | Money spent by the run, as reported by the host |
| `tokens_total` | Input plus output tokens across every session in the run |
| `wall_time_seconds` | First request to final artifact |
| `invalid_decisions` | Decisions rejected by the same external validity checks applied to all three variants |
| `rework_cycles` | Artifacts withdrawn and redone inside the run |

Run counters are not authenticated by this evaluator. Use identical accounting
for cached tokens, retries, coordination and failed sessions across all variants.
Record rework uniformly; unavailable instrumentation must not be entered as zero.
An engine-only rejection count cannot be compared with an uninstrumented baseline.

Four are supplied by a separate reviewer against the case rubric:

| Metric | Definition |
|---|---|
| `factual_errors` | Statements contradicted by the case material |
| `fatal_defects` | Defects that make the artifact unusable or unsafe to act on |
| `constraint_violations` | Breaches of a limit the case stated explicitly |
| `evidence_coverage` | `{covered, required}` — claims carrying a usable evidence reference over claims needing one, kept as a fraction so a denominator of zero stays visible instead of reading as 100% |

There is no composite score, and `evaluate-nexus.py` rejects any input carrying a
`score`, `rank`, `overall`, `winner` or `composite` field. The reason is not
squeamishness. These metrics trade against each other, and any weighting that
combines them encodes a purpose — cheapest acceptable answer? highest assurance
at any cost? — that the protocol does not hold and the reader does. A single
number would also make a fatal defect purchasable with a lower token count, which
is exactly the substitution the doctrine's own metric pathology describes. Fatal
defects are reported alone, and are never offset.

The cost metrics are not a virtue on their own either. A run is cheap when it
does less, so `cost_usd` and `tokens_total` are only interpretable next to the
judged counters. The report states this in its own `limitations`.

## Blinding

Mask direct pipeline labels and keep the reviewer separate from the execution
workspace. File separation and keyword screening reduce obvious leaks but do not
prove blinding: style, content, weak identifiers or access to the trial mapping
can still reveal assignment. The packet records `NOT_INDEPENDENTLY_VERIFIED`
unless known tells are present, in which case it records `KNOWN_TELLS`.

1. Run the trials. Each row gets an opaque `submission_id` —
   `nexus-blind.py submission-id --case … --trial … --variant … --salt …`, which
   is reproducible for the operator. Use a private high-entropy salt; the format
   alone cannot establish opacity. A
   submission id that is not sixteen hex characters is rejected, so
   `nexus-run-0001` cannot slip through.
2. Seal the review packet:
   ```bash
   python3 scripts/nexus-blind.py seal --trials host-trials.json \
     --artifacts runs/ --cases examples/nexus/evaluation-cases.json --out review/
   ```
   This validates trial IDs, rejects symlinks and path escapes, and includes each
   case scenario, expected behavior and artifact hash. It copies each artifact
   under its submission id, shuffles the index, and
   **refuses to seal** if an artifact narrates its own pipeline ("as the NEXUS
   orchestrator…", "delegating to…"). Self-narration is the common way a blind
   leaks. Preserve original outputs: do not edit or rerun selectively until they
   look blind. Use a preregistered, consistently applied redaction procedure or
   record the review as unblinded. `--allow-tells` records a known leak; it does
   not certify blinding, and the evaluator does not independently verify packet access.
   A packet is written once; a sealed directory is never overwritten.
3. The reviewer receives `review/` and nothing else, and records counts per
   submission id. A judgment row carrying `variant`, `case_id`, `trial_id` or
   `model_version` is rejected as a metadata leak. A reviewer identifier matching
   any trial operator (ignoring surrounding whitespace and case) is rejected.
   Identifier separation does not authenticate that they are different people.
4. `evaluate-nexus.py --runs … --judgments …` joins the two after the judgments
   are sealed.

## Pre-registration and the stopping rule

Declare, before the first run, in a dated note: which cases, how many trials per
case, the budget policy, the model version, and who reviews. Then run all of
them. Stopping when the numbers look good, adding trials until they do, or
dropping a case that went badly are the three ways this protocol turns into
advocacy, and none of them leaves a trace in the output.

Incomplete execution pairs are excluded from matched aggregates and listed in
`incomplete_pairs`. The primary `comparisons` use only fully judged triples, so
all nine metrics have exactly the same case/trial cohort across variants.
`execution_comparisons` separately describes all complete execution triples.
`fatal_observations` preserves every supplied fatal finding, including excluded
or partially judged trials; these records are never treated as a clean result. This matters more than it looks: a variant that crashed or
blew its budget produces no artifact, and silently dropping it would delete the
comparison it lost. An unjudged submission is named in `unjudged_submissions`
across all supplied runs, including incomplete triples. Only complete execution
triples enter execution summaries. The CLI `--require-paired` requires at least
one fully judged triple, no incomplete execution triples and no unjudged rows;
it does not establish that the planned number of trials or cases was completed.

Preregistration and stopping rules are procedural requirements in this version.
No frozen trial schedule is parsed: a wholly omitted repetition leaves no trace.
Audit the output against the independently frozen schedule, including failures
and cancellations, before making a performance claim.

## What a completed run can and cannot support

With a handful of trials per case this yields descriptive medians and ranges per
variant, per metric. That is enough to notice a large, consistent difference and
enough to motivate or challenge a hypothesis within these observations. It is not a statistical test, it does not
establish causation, and it does not generalize past the cases, the model version
and the host recorded in the rows. `evaluate-nexus.py` states this in every
report and offers no ranking.

A result of "no observed difference" should be published in the same place as
any other. It does not establish statistical equivalence or absence of an effect. The engine's value would then rest on its bounded behavior —
budgets, HOLDs, expiry, termination — which is a separate claim with its own
evidence, not on model quality.

## Current state

```bash
python3 scripts/evaluate-nexus.py --runs examples/nexus/host-trials.json \
  --judgments examples/nexus/host-judgments.json
# => "status": "NOT_MEASURED"
```

Both files are empty. Twelve cases are defined and unmeasured. See
[NEXUS-INSTANCE.md](NEXUS-INSTANCE.md) for the engine this protocol would
measure, and [OPERATIONS.md](../OPERATIONS.md) for the surrounding release
boundary.

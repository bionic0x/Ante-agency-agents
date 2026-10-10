# Writing a held-out case pack

The Phase 1 exit of [NEXUS Overdrive](NEXUS-OVERDRIVE.md) needs at least six
held-out case packs. Each must be written by someone other than whoever writes the
agency's improvements. This guide is for those authors. Your pack is the only part
of the measurement the improver never sees, so its value depends on two things:
you write it independently, and you settle what counts as a failure before any
variant answers it.

## Who may author

- Anyone who does not write or tune the agency's profiles, runbooks or code for
  the proposals being judged. Record your own name as `author`. The campaign and
  the improvement gate refuse a held-out pack whose `author` or `frozen_by` matches
  a named improver.
- Do not show the pack to an improver before or after freezing. Held-out
  results are reported only as a pass or fail of the gate.

## What makes a good pack

- **A real decision.** The brief names the decision, who takes it and by when.
  "Analyse the market" is not a case. "Decide whether to extend the pilot to
  three regions this quarter" is.
- **Material that can mislead.** Pick a case in `examples/nexus/evaluation-cases.json`
  (`case_ref`) and supply materials where the failure it describes is possible.
  Examples: an indicator that moved while the outcome did not, two sources that
  share an origin, or a premise that has expired.
- **Observable fatal defects.** Write each `rubric.fatal_defects` entry so that a
  reviewer who has only the output and the pack can tell whether it occurred.
  "Recommends extending because the KPI rose, without addressing renewals" can
  be judged. "Poor reasoning" cannot.
- **A small, honest rubric.** Two to five entries per rubric key. Each
  `evidence_required` entry names a point that must be grounded in your
  materials.
- **An instance that fits the case.** `instance.json` starts as a copy of a
  template. Rewrite its tasks, `asserts` keys and claims for your case. Give two
  independent tasks an assertion key they could plausibly disagree on.

## Steps

```bash
python3 scripts/nexus-casepack.py new examples/nexus/casepacks/<new-id> \
    --author "<your name>" --case-ref <case id>
# replace every TODO in pack.json, add materials, rewrite instance.json
python3 scripts/nexus-casepack.py validate examples/nexus/casepacks/<new-id>
python3 scripts/nexus-casepack.py freeze examples/nexus/casepacks/<new-id> \
    --by "<your name>" --at <ISO-8601 time with zone>
```

Validation refuses any field that still starts with `TODO`. Run
`python3 scripts/nexus-lint.py examples/nexus/casepacks/<new-id>/instance.json`
on the rewritten instance: a shared key that only one task asserts cannot
produce the disagreement the case may be testing. Once frozen, a pack
cannot be edited; a changed case is a new pack id. Submit held-out packs in a
human-authored pull request, separate from any improvement proposal.

## Running the campaign

```bash
python3 scripts/nexus-campaign.py plan --held-out examples/nexus/casepacks \
    --improver <improver label> --model <model id> --policy trial-standard-v1 \
    --operator <operator> --out <campaign dir>
python3 scripts/nexus-campaign.py status --held-out examples/nexus/casepacks \
    --improver <improver label> --trials <campaign dir>/trials.json \
    --judgments <judgments file>
```

`plan` prints every missing run and its spend ceiling. It spends nothing. Each
run is started by an operator. Seal the artifacts with `scripts/nexus-blind.py`
before review. `status` returns `INCOMPLETE`, `PROCEED_TO_PHASE_2` or `REDIRECT`
according to the exit and kill rules in the charter. Those rules are fixed in
code before the results exist.

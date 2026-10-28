# Ante Foundation example: the laboratory consortium

A synthetic case (Marco, Appendix E): three universities share a laboratory
with 100 effective hours a week, ask for 110, and quarrel over urgency. Every
figure is invented for teaching; no real institution is described.

`lab-consortium/run.sh` takes the inputs in `input/` through the whole method
and the learning loop:

| Step | Command | What the artefact settles |
|---|---|---|
| 1 | `frame` | resulting state, minimum acceptable, limits, horizon |
| 2 | `map` | actors with preference, representation and capacity kept apart |
| 3 | `cause` | the causal chain, a rival explanation, an observable refutation |
| 4 | `focus` | the dependency to act on, with substitution and horizon |
| 5 | `options` | options that differ in mechanism, continuity baseline included |
| 6 | `react` | competent opposition, unexpected cooperation, a third-party shift |
| 7 | `street` | how each metric and rule could be gamed, and how that would show |
| 8 | `ach` | competing hypotheses with shared sources counted once |
| 9 | `watch` | indicators tied to responses, reserve, culmination signal |
| 10 | `close` | the termination contract, designed before the commitment |
| 11 | `cohere` | the seven tests, non-additive; which verdicts remain admissible |
| 12 | `pathology` | the fourteen pathologies swept with false-positive checks |
| 13 | `nodal` | the claims that carry the plan and how hard each must be verified |
| 14 | `decide` | the decision record: `PROCEED_WITH_CONDITIONS`, with a named accepted risk |

Then the decision is recorded in a hash-chained ledger (marked `synthetic`),
one expectation is reconciled as `CONFIRMED` and the other as
`NOT_YET_OBSERVABLE`, and calibration answers `INSUFFICIENT_SAMPLE` — correctly:
synthetic decisions never enter calibration.

```bash
bash examples/foundation/lab-consortium/run.sh          # rewrites artifacts/ and learning/
git diff --exit-code examples/foundation/lab-consortium # identical bytes: the chain is deterministic
python3 scripts/ante deck --artifacts examples/foundation/lab-consortium/artifacts --plain
```

The doctrine tables come from `foundation/proposals/contracts-v2.json` until the
owner settles decision D-004. A complete chain is a record, not an
authorisation to act.

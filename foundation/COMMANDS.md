# `ante` strategy commands

`python3 scripts/ante <command> INPUT [--at ISO8601] [--from ARTEFACT ...] [--out DIR]`
(or `python3 -m ante`). Offline and deterministic: the same input and `--at`
produce the same bytes. Exit 0 artefact produced (any verdict, `HOLD` included),
2 invalid input or doctrinal rejection, 3 broken lineage.

Every input carries `claims` (`{id, text, status, source: {ref, origin}, date, limit}`),
and an optional `at`. Review commands also carry `independence_level`
(`SELF` · `SEPARATED_CONTEXT` · `INDEPENDENT_OPERATOR`). Each command module's
docstring is its full input specification.

| Command | Marco | Needs (`--from`) | Refuses |
|---|---|---|---|
| `frame` | XIII F1, I | — | objective without an observable condition (pathology 2) |
| `map` | XIII F2, II | frame | actor whose preference, representation and capacity are one statement |
| `cause` | XIII F3, I.3 | frame | chain without a rival or an observable refutation |
| `focus` | XIII F4, III | map | centre without substitution or horizon; concept confusion (pathology 4) |
| `options` | XIII F5, App. B | cause | one viable option plus decoys; no continuity baseline; same mechanism; scores |
| `react` | XIII F6, VI, IX | options | no competent opposition, no unexpected cooperation, no third-party shift |
| `ach` | VIII.4 | frame | incomplete matrix; reports source groups, self-produced evidence, sensitivity |
| `watch` | XIII F7, VI.9 | options | indicator without a response; no pause or terminate threshold |
| `close` | XII, XIII F8 | frame | placeholder clauses; one clause pasted into several |
| `cohere` | XIV | frame | FAIL not fatal; `NOT_APPLICABLE` on Epistemic or Exit; unanswered test |
| `pathology` | XV | frame | unswept pathology; detection without false-positive check; culmination conflated with inversion or escalation |
| `decide` | SDR | frame, cohere, pathology (+ close to activate) | verdict outside what `cohere` admits; `PROCEED` without independent review, with a detected pathology, without close or expectations |
| `selftest` | VIII.13 | — | `PASS` without evidence or dated in the future |

`ante run RUNBOOK --artifacts DIR` checks that a case directory holds the chain
the runbook declares (`strategy_commands` in `strategy/runbooks.json`), intact, of
one case, under the canonical doctrine. It executes nothing.

`--draft-with PROVIDER --model ID` writes an unsigned `<command>.draft.json` from a
brief; see `ante/strategy/draft.py`.

## Learning

| Command | What it does | What it refuses |
|---|---|---|
| `learn record DECIDE --ledger L --at T` | appends a sealed `decide` artefact, frozen, to a hash-chained ledger | anything but `decide`; a second record; a record dated before the decision |
| `learn reconcile OBS --ledger L --at T` | appends observed outcomes (`CONFIRMED`, `REFUTED`, `INCONCLUSIVE`, `NOT_YET_OBSERVABLE`) as new entries | system-produced sources confirming or refuting; observations before the decision or in the future; `NOT_YET_OBSERVABLE` after the horizon |
| `learn calibrate --ledger L --at T` | Brier score and reliability by runbook, agent and claim kind | groups below `--min-sample` (default 30) answer `INSUFFICIENT_SAMPLE`, with no number |
| `learn patterns --ledger L --at T` | proposes differences in refutation rate that survive a permutation test with Bonferroni correction | patterns that only system-sourced evidence supports; synthetic decisions |
| `learn verify --ledger L` | checks the chain | — (a broken chain exits 3) |

## Self-development

| Command | What it does |
|---|---|
| `develop propose SPEC --patch P --base REF` | registers one bounded change with its findings, hypothesis, pre-registered metric, kill criterion, cost ceiling, scope and autonomy delta; refuses protected or out-of-scope paths, a second open proposal, spend beyond the campaign, a stopped loop |
| `develop gate ID --patch P [held-out evidence] [--selftest-register R] [--independent-review F]` | applies the patch at the base and runs the base evaluator: Overdrive paths, develop policy, characterization, self-test, held-out Pareto comparison, Turing lock; answers `PROPOSE`, `HOLD` or `REJECT` |
| `develop pr ID [--execute]` | after a `PROPOSE`, prints (or with `--execute` runs) the push and `gh pr create --draft`; once per proposal |
| `develop resume --by NAME --reason TEXT` | a named human restarts a loop stopped after two consecutive held-out regressions |
| `develop close ID --outcome merged\|rejected\|withdrawn` | frees the open-proposal slot |
| `develop status` | proposals, gates and committed spend |

Every `develop` command takes `--state FILE` (a hash-chained log) and, except
`status`, `--at`. Decisions D-013 and D-014 describe the policy and the lock.

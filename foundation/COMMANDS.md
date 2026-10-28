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

# Decision record — Ante Foundation

One entry per structural decision: context, decision, alternatives, consequences.
Status is `ACCEPTED` when the refactor relies on it, `PROPOSED` when it waits for
a human decision.

---

## D-001 · Where the foundation work lives — PROPOSED

**Context.** The foundation prompt forks `bionic0x/Ante-agency-agents` into
`bionic0x/ante-foundation` at `86addea`. Creating a repository is an account-level
action outside the scope this work session was granted.

**Decision.** Work proceeds on branch `foundation/v2`, created from `86addea`,
in the existing repository. The branch is portable: if the owner creates the
fork, the same history is pushed there unchanged.

**Alternatives.** Create the fork now (needs the owner's authorisation);
work only locally (loses review and CI).

**Consequences.** The `THIRD_PARTY_NOTICES.md` fork declaration is written
when the destination is fixed.

---

## D-002 · Characterization contract — ACCEPTED

**Context.** The refactor must keep every existing CLI byte-identical (invariant 5).

**Decision.** `tests/characterization/run.py` runs 114 cases through the real
script paths and compares exit status, stdout, stderr and written files with
recordings taken at `86addea`. Paths are normalised to `<ROOT>` and `<TMP>`;
the environment is fixed (`TZ=UTC`, `LC_ALL=C.UTF-8`, `PYTHONHASHSEED=0`).
Each case was run twice before recording and none differed. `record` never
overwrites a recording: changing one is a behaviour change and goes in its own
pull request.

**Alternatives.** Rely on the existing unit tests (they import modules directly
and do not pin CLI text); snapshot only exit codes (misses output drift).

**Consequences.** Recordings depend on CPython 3.11 argparse wording; the harness
is run with the CI interpreter. Cases that need the `claude` CLI or a network
are characterised through `--help` and usage errors only.

---

## D-003 · Protected scripts during the extraction — PROPOSED

**Context.** Nine NEXUS programs, every `test-*` file, `verify-release.sh` and
`.github/**` are protected. The prompt asks for the old scripts to become thin
wrappers and for the new checks to join the release gate, and it allows protected
paths to change only in separate, hand-reviewed commits labelled `protected:`.

**Decision.** Phase 1 builds `ante/` and converts the unprotected scripts first.
Each protected script becomes a wrapper in its own `protected:` commit that is a
mechanical move (no logic change), listed file by file in the pull request, and
proven by its characterization cases. Wiring `tests/characterization` and
`ante selftest` into `verify-release.sh` and the workflows is likewise one
`protected:` commit per file.

**Alternatives.** Leave protected scripts untouched and duplicate their logic in
`ante/` (two implementations of the evaluator — rejected: the evaluator would
stop being one thing); wrap everything in one commit (not reviewable line by line).

**Consequences.** The owner reviews those commits as the human author of record.
Nothing in the self-development loop (Phase 4) can produce or modify them.

---

## D-004 · One machine source for the seven tests and fourteen pathologies — PROPOSED

**Context.** `strategy/contracts.json` (protected) holds modes, epistemic states,
decision states and levels. The seven tests and fourteen pathologies exist only
as prose, in two versions that disagree:

| Item | `GENERAL-STRATEGY-DOCTRINE.md` | `STRATEGIC-CONTROL-PLANE.md` |
|---|---|---|
| Test 1 name | Political/purpose | Governing-object |
| Finding classes | fatal defect · accepted risk · pending information | `FATAL_DEFECT` · `ACCEPTED_RISK` · `PENDING_EVIDENCE` · `NOT_APPLICABLE` (never on Epistemic or Exit) |
| Pathology 9 | Reflex symmetry: competing where the other actor converts resources better | Mirrored symmetry: the response is chosen by the opponent's move |

The *Marco* (XIV, XV.9) supports both readings of pathology 9: its definition
names the domain where the other converts better, its mechanism column names the
move that fixes our response.

**Proposal for the owner to decide.**
1. Add `coherence_tests` and `pathologies` to `contracts.json` with stable ids
   (`purpose`, `causal`, `interactive`, `conversion`, `legitimacy`, `epistemic`,
   `exit`; `level_inversion` … `chronic_personalization`), each carrying both
   display names as aliases so neither document is edited to fit the code.
2. Keep test status (`PASS`, `CONDITIONAL`, `FAIL`, `NOT_APPLICABLE`) separate
   from finding class (`FATAL_DEFECT`, `ACCEPTED_RISK`, `PENDING_EVIDENCE`),
   with `NOT_APPLICABLE` forbidden on Epistemic and Exit — the control plane's
   rule, which the prompt's `ante cohere` already assumes.
3. Pathology 9 keeps the *Marco* definition (domain where the other converts
   better) as its description and the mirrored-response mechanism as its
   `mechanism` field.

The SDR template (`strategy/templates/strategic-decision-record.md` §8) already
separates *result* (`PASS` / `CONDITIONAL` / `FAIL` / `NOT_APPLICABLE`) from
*classification* and uses *Governing-object*: points 1 and 2 follow it.

The complete proposed file is `foundation/proposals/contracts-v2.json`; the
strategy tests run against it.

**Consequences.** Until the owner decides, `ante/doctrine` loads only what
`contracts.json` already contains: `cohere`, `pathology` and `decide` exit 2 with
a pointer to this entry unless they are given the proposal explicitly
(`--contracts`, a hidden option kept for tests). Every `cohere` and `pathology`
artefact records the hash of the doctrine it used, and `decide` refuses parents
produced under another one, so a proposal file cannot be mixed into a real chain.

---

## D-005 · Canonical JSON keeps its historical profiles — ACCEPTED

**Context.** Six programs serialise JSON for hashing with different settings
(see `INVENTORY.md §3`). Frozen pack hashes and replay digests depend on them.

**Decision.** `ante/core/canon.py` exposes named profiles (`ascii`, `ascii_strict`,
`unicode_strict`, …) that reproduce each historical byte stream; new code uses
one profile, `unicode_strict`. Unifying the old callers would change existing
hashes and therefore breaks v1 compatibility.

**Alternatives.** One canonical function for everything (invalidates frozen packs).

---

## D-006 · Refactor scope — ACCEPTED

The extraction covers the Python programs under `scripts/` and adds the `ante/`
package. The shell installers and converters are out of scope; the release gate
continues to cover them, and the baseline records their result.

---

## D-007 · Duplicate JSON keys stay accepted where they were — ACCEPTED

`ante/core/io.py` rejects duplicate keys for every new command. The existing CLIs
that accept them today (characterization `routing--route-duplicate`,
`instance--validate-duplicate-keys`) keep doing so through Phase 1. Tightening
them is a behaviour change with its own pull request and rebaselined recordings.

---

## D-008 · The installer runtime stays self-contained in `scripts/` — ACCEPTED

**Context.** Moving `resolve-agents.py` into the package made six cases of the
protected `test-install-functional.py` fail with `No module named 'ante'`: the
test installs from a copy of `scripts/` plus `tools.json`, which is how the
installer is meant to run. Moving `registry.py` broke `check-tools.sh`, which
verifies capabilities by reading that file's source.

**Decision.** `install.sh`'s Python dependencies — `resolve-agents.py`,
`build-catalog.py`, `registry.py`, `integration-state.py`, `build-hermes-plugin.py`,
`check-hermes-config-rewrite.py` — stay where they are, unchanged.
`ante.registry` loads them by path (`ante._compat.load_script`) and adds only
readers for `strategy/runbooks.json`. One implementation, no copies.

**Alternatives.** Ship `ante/` with the installer (changes the distribution
contract the protected test encodes); duplicate the catalog code in the package
(two implementations of one roster).

**Consequences.** The prompt's "every old script is a wrapper" holds for the
NEXUS programs; for the installer runtime the rule is inverted on purpose, and
the inventory says so.

---

## D-009 · Runbooks declare their command chain — ACCEPTED

**Context.** `ante run <runbook>` must know which artefacts a runbook expects;
the prompt makes `cohere`, `pathology`, `close` and `decide` mandatory for
material runbooks.

**Decision.** Each runbook in `strategy/runbooks.json` gains `strategy_commands`.
Sprint and Full runbooks use the whole method
(`frame map cause focus options react ach watch close cohere pathology decide`);
Micro runbooks use `frame cause options close cohere pathology decide`. A runbook is
material unless it sets `material` to a stated reason. `check-runbooks.sh`
enforces the four controls and that the chain ends in `decide`; it stays
self-contained because the protected `test-runbook-contracts.py` runs it from a
copy without `ante/`. `scripts/convert-outputs.sha256` records the new
`runbooks.json` hash (a contract line, reviewed here).

**Alternatives.** Infer chains from the mode at run time (invisible to the app
that reads `runbooks.json`).

---

## D-010 · `PROCEED` requires an independent coherence review — PROPOSED

**Context.** Invariant 10 says a review by the same operator, model and context
is a coherence function, not a barrier; VIII.9 is satisfied only by
`INDEPENDENT_OPERATOR`.

**Decision.** `ante decide` accepts `PROCEED` only when the `cohere` parent was
produced at `INDEPENDENT_OPERATOR`. With `SELF` or `SEPARATED_CONTEXT` the owner
can still decide `PROCEED_WITH_CONDITIONS` and name the independent review as a
condition. This is a design choice of the foundation, made explicit for the owner
to confirm or relax.

---

## D-011 · Lineage is the set of artefacts supplied, bound by case and time — ACCEPTED

Each artefact names its parents by hash, carries the `case_id` set by `frame`,
and is sealed by `artifact_sha256`. A command verifies every parent's seal,
refuses parents of two cases, parents dated after its own decision time, and the
absence of the parents its step needs (exit 3). Claims are visible downstream
only through the parents actually supplied, so a reference to an upstream claim
proves that artefact was present.

---

## D-012 · Model drafting is opt-in and never signed — ACCEPTED

`--draft-with PROVIDER --model ID` asks a declared provider's adapter to draft a
command input from a brief. The output is `<command>.draft.json`: every claim is
forced to `HYPOTHESIS` with `origin: system`, the proposal sits under `input`
beside a `draft` header with `signed: false`, and running a command on the file
as written fails. Only Anthropic has an adapter (the existing Claude Code adapter);
other providers in `providers.json` are refused until one is written.

---

## D-013 · The develop loop's own protected list lives beside Overdrive's — PROPOSED

`ante develop` must never change the evaluator that judges it. Overdrive already
protects its evaluator in `strategy/overdrive-protected.json`, and
`nexus-improve.py paths` enforces it. The foundation adds parts that need the
same protection (the gate, the Turing lock, ICE layers, constructs, doctrine and
claims discipline, the ledger, characterization tests) and declares which scopes
a proposal may edit at all.

Changing `overdrive-protected.json` is itself a change to a protected path, so
this branch does not touch it. Instead `foundation/develop-policy.json` holds the
foundation's protected list, the editable scopes and the loop's limits (one open
proposal, 50 USD committed per campaign, stop after two consecutive held-out
regressions), and protects itself. The gate applies both lists, read at the base
revision, and the stricter wins.

**Proposal for the owner.** Merge the develop protected list into
`overdrive-protected.json` in a hand-written `protected:` commit, so a single
policy file governs every self-improvement path. Until then both lists apply.

**How the gate keeps its evaluator honest.** The candidate is applied in a
worktree at the base; `nexus-improve.py` and the characterization harness with
its recordings run from a second worktree at the base, never from the candidate.
A forged proposal that rewrites the evaluator is judged by the old one (tested).
Held-out packs must be outside the checkout. Missing held-out evidence is HOLD,
never PROPOSE. `pr` opens at most one draft per proposal, only with `--execute`,
refuses an existing remote branch, never force-pushes, never merges and never
touches `.github/**`.

---

## D-014 · The Turing lock counts autonomy cumulatively — PROPOSED

Each proposal declares an integer `autonomy_delta` on six dimensions
(permissions, budget, scope, gate thresholds, frequency, human-review reduction).
Only positive components count, so lowering one does not pay for raising another.
Any positive delta is held until a review record by an `INDEPENDENT_OPERATOR`
names the proposal. The lock also sums the positive deltas the gate let through
in the last 90 days, since the last review of the accumulation: above 4, a review
of the single step is not enough, and the record must accept the accumulated
total. Five one-step proposals, each reviewed on its own, therefore pass four
times and are held on the fifth — the erosion lives in the sum, which no
single-step reviewer saw. A proposal that declares no change but adds lines about
budgets, limits, approvals, permissions or thresholds trips a heuristic wire
(`UNDECLARED_AUTONOMY`) and is held. Review records are self-declared like every
independence label in Ante: the lock checks form, coverage, date, hash and that
the loop did not write them, not who the reviewer is. The limit and window are
constants in `ante/turing/lock.py`, a protected path, for the owner to set.

---

## D-015 · Canaries are seeded before freezing, and kept outside the checkout — ACCEPTED

A canary is `ANTE-CANARY-` plus 32 hex digits, written as an HTML comment into
each markdown or text material of a held-out pack by `ante ice seed`, before
`nexus-casepack.py freeze` (afterwards the material is fixed by `inputs_hash`).
The registry that maps canaries to packs lives beside the packs, outside the
checkout; the format alone is enough to detect contamination. `ante develop`
rejects any proposal whose spec, patch or cited findings contain a canary, at
proposal time and again at the gate. The held-out examples already frozen in
`examples/nexus/casepacks/` are public teaching material: they carry no canary,
and the gate refuses any held-out root inside the checkout. A test asserts that
the checkout contains no canary string at all.

The five ICE layers (`ante/ice/layers.json`) — canary scan (detect), autonomy and
spend margins (absorb), base-revision evaluation (contain), draft-only branch
(recover), held-out regression stop (learn) — each declare their data and their
assumption; `ante ice layers` fails if two share either.

---

## D-016 · Literary names stay in the CLI; artefacts use functional names — ACCEPTED

The prompt names the mechanisms after Gibson (`nodal`, `street`, `stub`,
`jackpot`, `ghosts`, `deck`, constructs, ICE, the Turing lock). They are kept as
command and module names, which are internal conventions. Everything a third
party reads uses functional names: `load_bearing_claims`, `misuse_analysis`,
`snapshot`, `frozen_reviewer`, `shadow_trial`, `cumulative_drift`,
`stale_claims`, `discard_archive`, finding codes such as
`MISUSE_ANALYSIS_MISSING` and `LOAD_BEARING_UNVERIFIED`. One residue remains for
the owner to decide: an artefact's `command` field records the command that
produced it, so a decision's lineage lists `nodal` and `street`. Renaming those
two commands (for example `load` and `misuse`) would remove it.

---

## D-017 · CI wiring is delivered as a patch for a protected commit — PROPOSED

The prompt asks for the new checks in `verify-release.sh` and the runbook
workflow. Both `scripts/verify-release.sh` and `.github/**` are protected paths,
and adding steps is not a mechanical extraction, so this branch does not edit
them (§11). `foundation/proposals/ci-wiring.patch` adds, for the owner to apply
in a hand-written `protected:` commit: the characterization recordings, the
extraction check, the foundation tests, the frozen-reviewer and defence-layer
checks, and the institutional self-test run on `foundation/selftest-register.json`
and published to the job summary (reported, never failing the build, as the
self-test doctrine requires). The patch applies cleanly to this branch and the
release gate was run with it applied.

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

**Consequences.** Until the owner decides, `ante/doctrine` loads only what
`contracts.json` already contains, and the commands that need the tests or the
pathologies (`cohere`, `pathology`, `decide`) are not merged.

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

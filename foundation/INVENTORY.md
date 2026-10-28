# Inventory of the base commit

Base: `bionic0x/Ante-agency-agents` at `86addea` (main, 28 Oct 2026).
Scope of the refactor: the 37 Python programs under `scripts/` that are not
tests. The shell installers and converters (`install.sh`, `convert*.sh`,
`lint-agents.sh`, `check-*.sh`, `lib.sh`) stay outside the refactor; the release
gate keeps covering them unchanged.

Columns: **P** = listed in `strategy/overdrive-protected.json` (changes only by
a separate, hand-reviewed `protected:` commit); **Writes** = files the program
can create or change; **External** = processes or network it can reach;
**Covered by** = existing tests that exercise it, plus the characterization
cases recorded in Phase 0 (`tests/characterization/cases.json`).

## 1. NEXUS engine and evaluation

| Script | P | Purpose | Inputs → outputs | Writes | External | Depends on | Covered by |
|---|---|---|---|---|---|---|---|
| `nexus-instance.py` | ✔ | Deterministic planner and event replay; never executes | instance JSON (+ events JSONL, checkpoint, `--at`) → plan / replay JSON | `--output` file | — | `build-catalog.py`, `nexus-options.py`, `contracts.json`, `vectors.json`, `challenger-pairs.json` | `test-nexus-instance.py`, `test-nexus-improve.py`; 13 cases |
| `nexus-options.py` |   | Factor comparison without weighted scores | options JSON → dominance JSON | — | — | — | `test-nexus-evaluation.py`; 2 cases |
| `nexus-routing.py` |   | Admissible execution targets by level, vector and factor | instance (+ observations, `--at`) → route/coverage JSON | — | — | `contracts.json`, `providers.json`, `vectors.json` | `test-nexus-routing.py`; 4 cases |
| `nexus-lint.py` |   | Plan-shape findings before adoption | instance → findings JSON, exit 1 on ERROR (or WARN with `--strict`) | — | — | `nexus-instance.py` | `test-nexus-lint.py`; 4 cases |
| `nexus-brief.py` |   | Owner's decision brief | instance + events + `--at` → Markdown or JSON | — | — | `nexus-instance.py`, `nexus-lint.py` | `test-nexus-brief.py`; 3 cases |
| `nexus-pilot.py` |   | Bounded live-execution pilot | `step` / `accept` / `replay` | events JSONL, packets | via adapter | `nexus-anthropic.py`, `nexus-instance.py`, `nexus-routing.py` | `test-nexus-pilot.py`; 2 cases |
| `nexus-anthropic.py` |   | Claude Code execution adapter | `observe` | run artefacts | `claude` CLI | `agent-capabilities.py` | `test-nexus-anthropic.py`; help/usage only |
| `nexus-plan.py` |   | Planner drafts a task graph; owner adopts | `draft` / `adopt` / `verify` | draft, adoption files | `claude` CLI (draft) | `nexus-instance.py`, `nexus-lint.py`, `nexus-anthropic.py`, `build-catalog.py` | `test-nexus-plan.py`; help/usage only |
| `evaluate-nexus.py` | ✔ | Join trials with blind judgments; no composite | trials (+ judgments, cases) → report JSON | — | — | `evaluation-cases.json` | `test-nexus-evaluation.py` and four more; 3 cases |
| `nexus-blind.py` | ✔ | Seal review packets without pipeline labels | `seal` / `submission-id` | review packet directory | — | `evaluate-nexus.py` | `test-nexus-evaluation.py`, `test-nexus-review.py`; 1 case |
| `nexus-casepack.py` | ✔ | Freeze and verify case packs | `validate` / `verify` / `freeze` / `list` / `new` | `frozen` block in pack | — | `nexus-instance.py`, `build-catalog.py` | `test-nexus-casepack.py` and three more; 12 cases |
| `nexus-trial.py` | ✔ | Run one evaluation trial | `run` / `accept` / `owner-event` / `resume` / `status` / `brief` | run directory | `claude` CLI | `nexus-anthropic.py`, `nexus-brief.py`, `nexus-casepack.py`, `nexus-instance.py`, `evaluate-nexus.py` | `test-nexus-trial.py`; help/usage only |
| `nexus-review.py` | ✔ | Blind reviewer kit and collection | `kit` / `collect` | kit directory | — | `evaluate-nexus.py`, `nexus-casepack.py` | `test-nexus-review.py`; help/usage only |
| `nexus-improve.py` | ✔ | Self-improvement gate: protected paths + held-out non-regression | `paths` / `compare` / `gate` | — | `git` | `evaluate-nexus.py`, `nexus-casepack.py`, `overdrive-protected.json` | `test-nexus-improve.py`; 1 case |
| `nexus-campaign.py` | ✔ | Phase 1 exit and kill rule fixed before results | `plan` / `status` / `throughput` | `--out` plan | — | `nexus-casepack.py`, `nexus-trial.py`, `evaluate-nexus.py` | `test-nexus-campaign.py`; 2 cases |
| `nexus-optimize.py` | ✔ | Bounded edit proposal to one profile | `propose` | proposal directory | `claude` CLI | `nexus-casepack.py`, `nexus-anthropic.py`, `build-catalog.py` | `test-nexus-optimize.py`; help/usage only |
| `marketplace-intake.py` |   | External marketplace observations → offline HOLD packets | snapshot + `--at` → packets JSON | — | — | — | `test-marketplace-intake.py`; 5 cases |
| `nexus-relay.py` |   | Entry point of NEXUS Relay | `init` / `invite` / `serve` / `verify` / `anchor` / `reconcile` | SQLite store | local server | `relay/nexus_relay` | `relay/tests`; help only |

## 2. Catalog, registry and adapters

| Script | Purpose | Writes | External | Covered by |
|---|---|---|---|---|
| `build-catalog.py` | Roster from frontmatter; `--check` compares `CATALOG.md` | `CATALOG.md`, `--json` | — | `test-runbook-contracts.py`; 1 case |
| `registry.py` | Canonical divisions/tools reads for shell | — | — | 14 shell suites; 2 cases |
| `resolve-agents.py` | IDs, names and runbooks → adapter slugs | — | — | `test-install-functional.py`; 3 cases |
| `integration-state.py` | Per-agent adapter state | state files | `subprocess` | conversion suites; usage only |
| `build-hermes-plugin.py` / `check-hermes-plugin.py` / `check-hermes-config-rewrite.py` | Hermes router plugin build and checks | plugin directory | `subprocess` (rewrite check) | `test-hermes-plugin.py` and conversion suites |
| `agent-capabilities.py` / `check-agent-privileges.py` | Declared and observed capability boundaries | `--output` profile | — | `test-agent-capabilities.py`, `test-agent-privileges.py`; 1 case |
| `check-security-engagement.py` | Engagement contract of security agents | — | — | `test-security-engagement.py`; 1 case |
| `check-challenger-pairs.py`, `check-htp-gate0.py`, `check-strategy-vocabulary.py` | Structural guards | — | — | release gate; 3 cases |
| `host-acceptance.py`, `host-session-evidence.py`, `probe-host-claude-code.py` | Live-host acceptance records and probe | probe output | `claude` CLI (probe) | `test-host-acceptance.py` |
| `import-openclaw-community.py` | Community import with provenance | agent files | network (`urllib`) | `test-openclaw-import-provenance.py` |
| `list-changed-agent-files.py` | Changed paths → canonical agents | — | — | `test-changed-agent-files.py` |
| `benchmark-conversion.py` | Conversion timing, never a gate | benchmark output | `git` | — |

## 3. Duplicated code

| Concern | Copies | Divergence that the extraction must preserve |
|---|---|---|
| Canonical JSON for hashing | `marketplace-intake.py:70`, `nexus-casepack.py:65`, `nexus-instance.py:32`, `nexus-pilot.py:228`, `nexus-anthropic.py:317`, `integration-state.py` | `ensure_ascii` differs (`True` in intake and instance, `False` in casepack, pilot and adapter); `allow_nan=False` only in casepack and instance. Frozen `inputs_hash` values depend on these exact settings, so `ante/core/canon.py` exposes them as explicit profiles, not as one function. |
| ISO-8601 parsing with mandatory timezone | `nexus-instance.py:61`, `nexus-pilot.py:47`, `nexus-routing.py:48`, `marketplace-intake.py:54`, `nexus-casepack.py:139`, and six more | `nexus-routing.py` does not translate `Z` (accepted natively by Python 3.11) and echoes the rejected value in its message; the others do not echo. |
| JSON loading | `nexus-pilot.py:57`, `nexus-plan.py:63`, `nexus-trial.py:113`, `integration-state.py:50`, inline `json.loads` elsewhere | Duplicate keys are rejected only by `marketplace-intake.py` and `check-security-engagement.py`. Everywhere else the last value silently wins (characterization: `routing--route-duplicate` exits 0, `instance--validate-duplicate-keys` fails on an unrelated field). |
| `require()` / domain error classes | 6 `require` copies, 11 `*Error(ValueError)` classes | Message prefix and exit status differ per CLI (`ERROR …` exit 1 in most; intake prints a generic message and exits 2). |
| Exact-key validation | `marketplace-intake.py:exact_keys`, hand-written checks in the engine | — |
| Module loading of sibling scripts | `spec_from_file_location` in 14 programs | Hyphenated filenames prevent ordinary imports; this is the main obstacle the `ante/` package removes. |

## 4. Discrepancies with the foundation prompt

| Prompt assumption | Repository fact | Consequence |
|---|---|---|
| `ante/doctrine` loads the seven tests and fourteen pathologies from `strategy/contracts.json` | `contracts.json` holds runbook modes, epistemic states, decision states and levels only. Tests and pathologies exist as prose in several documents. | A single machine source needs a `protected:` change to `contracts.json`. See D-004. |
| The seven tests have one canonical form | `GENERAL-STRATEGY-DOCTRINE.md §14` names test 1 *Political/purpose* and has three finding classes; `STRATEGIC-CONTROL-PLANE.md §5` names it *Governing-object* and adds `NOT_APPLICABLE` as a fourth class (forbidden on Epistemic and Exit). Pathology 9 reads *competing where the other actor converts better* in one and *the response is chosen by the opponent's move* in the other. | Two doctrinal sources disagree; the prompt (§11) reserves that choice for a human. See D-004. |
| Old scripts become thin wrappers in Phase 1 | 9 of the 18 programs in section 1, every `test-*.py`/`test-*.sh`, `verify-release.sh` and `.github/**` are protected. | Wrapping a protected script, wiring new tests into the release gate or adding workflows all need hand-reviewed `protected:` commits. See D-003. |
| Held-out packs live outside the checkout | Three exposed sample `held_out` packs are published in `examples/nexus/casepacks`; `nexus-campaign.py` and `nexus-improve.py` already refuse held-out roots inside the checkout. | Invariant 4 is already enforced mechanically for real campaigns; the samples remain fixtures. |
| `ante` runs on Python 3.11 | CI pins Python 3.11; this inventory and the recordings were produced with 3.11.18. | Recordings embed CPython's argparse text; a different minor version can change help output. The harness must run under 3.11. |

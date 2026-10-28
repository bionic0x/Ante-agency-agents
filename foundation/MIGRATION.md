# Migration to the Ante Foundation

Nothing a user runs today changes. Every script under `scripts/` keeps its name,
arguments, exit codes, output bytes and side effects. This page lists what moved,
what stays where it is and why, what is deprecated and from when, and how to check
the equivalence yourself.

## What moved

Eight scripts now delegate to the `ante` package. Each script file is a short
entry point that loads its module into the script's own namespace
(`ante/_compat.py`), so code and tests that monkeypatch a script's globals keep
working.

| Script (unchanged interface) | Implementation |
|---|---|
| `scripts/nexus-options.py` | `ante/nexus/options.py` |
| `scripts/nexus-routing.py` | `ante/nexus/routing.py` |
| `scripts/nexus-lint.py` | `ante/nexus/lint.py` |
| `scripts/nexus-brief.py` | `ante/nexus/brief.py` |
| `scripts/marketplace-intake.py` | `ante/nexus/marketplace.py` |
| `scripts/nexus-anthropic.py` | `ante/nexus/anthropic.py` |
| `scripts/nexus-pilot.py` | `ante/nexus/pilot.py` |
| `scripts/nexus-plan.py` | `ante/nexus/plan.py` |

Each move is mechanical: the module is the original file without its shebang and
with `ROOT` imported from `ante.paths`. `foundation/tools/extractions.json` records
the moves against the base commit, and `python3 foundation/tools/extraction.py
verify` re-derives every module from the base revision and compares bytes.

## What stays in `scripts/`, and why

| Scripts | Reason |
|---|---|
| The evaluator and its tests: `nexus-improve.py`, `evaluate-nexus.py`, `nexus-casepack.py`, `nexus-trial.py`, `nexus-blind.py`, `nexus-campaign.py`, `nexus-review.py`, `nexus-optimize.py`, `nexus-instance.py`, `test-*.py`, `test-*.sh`, `verify-release.sh` | Listed in `strategy/overdrive-protected.json`. A structural change needs a separate, hand-written `protected:` commit approved by the owner (decision D-003). |
| Installer runtime: `resolve-agents.py`, `build-catalog.py`, `registry.py`, `integration-state.py`, `build-hermes-plugin.py`, `check-hermes-config-rewrite.py` | The installer copies `scripts/` alone into hosts and test fixtures; these must run without the `ante` package (decision D-008). `ante.registry` reads them instead of duplicating them. |
| Shell checks and converters | Unaffected; `check-divisions.sh` and `check-runbooks.sh` learned about the new directories and the runbook `strategy_commands` field. |

## New, additive

- `scripts/ante` and `python3 -m ante`: the strategy, learning, self-development
  and defence commands in [COMMANDS.md](COMMANDS.md).
- `strategy/runbooks.json`: each runbook declares `strategy_commands` (the artefact
  chain `ante run` checks) and `material` (true, or the reason it is not).
  `scripts/convert-outputs.sha256` carries the new hash of that file.
- `foundation/develop-policy.json`, `ante/constructs/frozen.json`,
  `ante/ice/layers.json`: data the self-development gate reads at the base revision.

## Deprecations

Announced 2026-10-28. Nothing is removed before the owner confirms it, and not
before **2027-04-28**.

| Deprecated | Use instead | Why |
|---|---|---|
| Loading one of the eight moved scripts as a module with `runpy` or `importlib.util.spec_from_file_location` to reach its functions | `import ante.nexus.<module>` | The entry point exists for the command line; the module is the stable import surface. Both work until removal. |
| Reimplementing canonical JSON, timestamp parsing or JSON loading in new tools | `ante.core.canon`, `ante.core.time`, `ante.core.io` | One implementation per rule (INVENTORY lists eleven copies of time parsing). Existing scripts keep their own copies until each is moved mechanically. |

The command-line entry points of every script are **not** deprecated.

## How to verify equivalence

```bash
python3 tests/characterization/run.py            # 114 recorded cases: exit code, stdout, stderr, written files
python3 foundation/tools/extraction.py verify    # every moved module equals the base file, mechanically transformed
python3 -m unittest discover -s tests/foundation -p 'test_*.py'
bash scripts/verify-release.sh                   # the release gate, unchanged
```

The characterization recordings were taken at the base commit before any code
moved. `run.py record` never overwrites a recording: a recording that stops
matching is a behaviour change, which belongs in its own pull request with a
reviewed rebaseline. The baseline measurements and what was not measured are in
[BASELINE.md](BASELINE.md).

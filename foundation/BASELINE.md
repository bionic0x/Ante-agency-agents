# Baseline at the base commit

Recorded before any code moved. Every later phase is compared with this state.

| Item | Value |
|---|---|
| Repository | `bionic0x/Ante-agency-agents` |
| Commit | `86addea` — merge of PR #62 (`feat/act-marketplace-intake`), `main` on 28 Oct 2026 |
| Interpreter | CPython 3.11.18 in a virtual environment |
| Dependencies | `.github/requirements/validation.txt` installed with `--require-hashes` (PyYAML 6.0.3); `relay/tests/requirements-property.txt` for the property run |
| Date of run | 28 Oct 2026 (Europe/Madrid) |

## Release gate — `scripts/verify-release.sh`

**Result: `PASSED: complete release gate`, exit 0, 16 min 20 s wall time.**

| Component | Measured result |
|---|---|
| Python `unittest` suites run by the gate | 430 tests across all suites, all OK; 1 module skipped (see relay) |
| Agent lint | 506 files, 0 errors, 14 warnings |
| Divisions | 19 consistent across `divisions.json`, discovery, directories and CI |
| Tools | 17 validated from `tools.json`, 15 converted, 2 source/identity |
| Runbooks | 9 runbooks, 134 slug references, 28 required artefacts, 9/9 termination contracts structurally valid |
| Catalog | `CATALOG.md` current — 506 agents, 9 runbooks |
| Security engagement | 22/22 security agents pass |
| Conversion outputs | 32 passed, 0 failed (506 roster agents × 15 tools) |
| Installer and converter regressions | all shell suites PASS |

## NEXUS Relay — `relay/tests`

| Run | Result |
|---|---|
| Inside the gate (no `hypothesis`) | 122 tests OK, `test_properties` skipped: *hypothesis is not installed* |
| With `relay/tests/requirements-property.txt` | 131 tests OK, 0 skipped |

## Characterization — `tests/characterization`

| Item | Value |
|---|---|
| Cases | 114 (31 `--help`, 20 usage errors, 63 behavioural cases on repository fixtures) |
| Stability | every case executed twice before recording; 0 unstable |
| Replay against the recordings | 114/114 match |

## Not measured

| Item | Reason |
|---|---|
| `.github/workflows/security.yml` (gitleaks, zizmor, semgrep, osv-scanner) | Runs on GitHub; not reproduced locally. The PR's own CI run is the measurement. |
| Live-host behaviour of `nexus-anthropic`, `nexus-trial`, `nexus-plan draft`, `nexus-optimize`, `probe-host-claude-code` | Requires the `claude` CLI and credentials; characterised through help and usage errors only. |
| macOS installer run | CI-only. |

The 14 lint warnings and the stale counts in `UNIFIED_AGENCY_BUILD_INFO.json`
(8 runbooks there, 9 in the tree) exist at the base commit and are left as they are.

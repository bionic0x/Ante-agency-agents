# Changelog

## Ante Foundation: strategy, learning and self-development — 2026-10-28

- Add the `ante` package and `scripts/ante`. Shared core (`ante.core`: strict JSON
  loading, canonical JSON profiles, schema checks, UTC time), doctrine tables,
  registry façade and sealed artefacts bound by hash, case and time.
- Strategy layer: fourteen commands following the method of the General Theory
  of Strategy — `frame`, `map`, `cause`, `focus`, `options`, `react`, `street`,
  `ach`, `watch`, `close`, `cohere`, `pathology`, `nodal`, `decide` — plus
  `selftest` and `ante run` (chain completeness per runbook). Each refuses its
  characteristic defect; `decide` admits only what `cohere` leaves admissible and
  refuses `PROCEED` without an independent review, a termination contract, dated
  expectations, or with a load-bearing assumption not accepted as a named risk.
- Learning layer: hash-chained decision ledger with frozen decision snapshots,
  reconciliation, Brier calibration with `INSUFFICIENT_SAMPLE`, patterns guarded by
  a permutation test with Bonferroni correction, cumulative-drift review
  (`jackpot`), shadow trials (`stub`), weak signals and a discard archive.
- Self-development: `ante develop` proposes bounded changes, judges them with the
  base revision's evaluator, characterization, held-out comparison, canary scan
  and a lock on cumulative autonomy, and opens at most one draft pull request; it
  never merges. Frozen reviewer profiles and five independent defence layers.
- Eight scripts become entry points over `ante/nexus/` with byte-identical
  behaviour, proved by 114 characterization recordings taken before the move.
  Runbooks declare `strategy_commands` and `material`.
- Synthetic end-to-end example in `examples/foundation/`; 152 foundation tests
  and 114 characterization cases. Owner
  decisions pending: D-001, D-003, D-004, D-010, D-013, D-014 (`foundation/DECISIONS.md`).

## ACT-LABS marketplace patterns and offline intake — 2026-10-28

- Assess ACT-LABS-IO discovery, event processing and task lifecycle patterns at
  pinned commits; record 23 source blob identities and SHA-256 fingerprints.
- Add an original, standard-library offline review envelope and CLI with
  chain/contract/log identity, duplicate/conflict detection, freshness/deadline
  flags and payload hashing. Every packet remains HOLD without execution authority.
- Document source limitations, existing-role handoffs and requirements for a
  future MCP/live adapter; no ACT code, credentials, signer or SDK is imported.
- Add 15 boundary tests to local release validation and Runbook CI.

## Upstream synchronization and MCP advisory remediation — 2026-10-16

- Merge 48 commits from `msitarzewski/agency-agents:main` with upstream ancestry preserved. Keep the fork's NEXUS, HTP, Relay, Alpha Research Suite and custom agents; apply upstream's source fixes to 26 files and regenerate the conversion manifest for the 21 changed agent profiles.
- Update Semgrep's hash-pinned transitive `mcp` dependency from 1.29.0 to 1.30.0 (upstream-compatible minor update) in response to GHSA-84m7-p3x7-pcfv / CVE-2026-59951; artifact SHA-256 digests verified against PyPI. No scanner suppression or waived security gate.

## NEXUS Overdrive: profile optimizer — 2026-10-11

- Add `scripts/nexus-optimize.py` (Phase 3, protected from self-improvement
  proposals). It proposes a body-only edit to one agent profile from
  development-split feedback and writes a patch; it never commits or merges.
  Refused: held-out evidence, frontmatter changes, body changes above
  `--max-change` (30%), a dropped Identity/Core Mission/Critical Rules section, a
  proposal that names an evidence pack or copies eight consecutive words of its
  materials, and an unchanged body. One refusal is fed back; every attempt is kept.
- Live checks on claude-opus-5-5 (about $0.58). The first run was refused twice:
  the body grew 36%, and then the reply's outer fence was shorter than the profile's
  own code blocks. With longer outer fences accepted and requested, the next run
  proposed a 28% edit on its first attempt: a measure audit (activity, proxy,
  outcome), an incentive-gaming check, and an outcome guardrail for each proxy. It
  was not applied; admission needs the held-out gate.
- Add 12 tests.

## NEXUS Overdrive: planner agent — 2026-10-11

- Add `scripts/nexus-plan.py` (Phase 3). The owner writes an objective file
  (`examples/nexus/planner-objective.example.json`); the planner agent drafts only
  the task graph; the tool assembles the instance, feeds engine refusals back for at
  most two repairs and lints the result. A planner that sets anything besides tasks
  is refused. `adopt` pins the instance hash under the mandate owner and requires
  each linter warning to be accepted by code; `verify` checks the pin.
- Live check on claude-opus-5-5: the first call drafted five tasks, with two
  independent pairs that assert the same keys under different agents, plus a
  synthesis that used the whole ordinary budget. The engine refused one field type
  and the repair passed (about $0.21). With a typed example task in the prompt, the
  next draft was valid on its first attempt (about $0.11).
- Add 9 tests.

## NEXUS Overdrive: reviewer kit and decision brief — 2026-10-11

- Add `scripts/nexus-review.py`. `kit` turns a sealed review packet into scoring
  sheets built from each pack's rubric, with the case brief and materials under an
  opaque key; nothing in the kit distinguishes the three variants of a pack.
  `collect` refuses unfilled items or an artifact edited during review and writes
  judgments `evaluate-nexus.py` accepts. Protected from self-improvement proposals.
- Add `scripts/nexus-brief.py` (Phase 3) and `nexus-trial.py brief`: the owner's
  decision brief from an instance and its event log. Lists what waits on the owner,
  asks the engine whether closure would be admitted now through a probe event that
  is never recorded, flags shared models and source roots, and keeps every owner and
  reviewer event with its stated reason. It decides nothing.
- Add 15 tests.

## Repository audit fixes — 2026-10-10

- **Nine regression tests were not run anywhere** (neither CI nor the release gate) and
  seven of them failed. Four only needed their sandboxes updated for the registries
  (`tools.json`, `scripts/registry.py`, `convert-engine.sh`, `integration-state.py`).
  The other three exposed real defects, fixed here:
  - `convert.sh --parallel`: a failing converter aborted under `set -e` before its
    buffered error was printed or the buffer removed; the failure now shows the
    worker's output, cleans up and exits non-zero. Tool names pass as arguments.
  - `install.sh`: a failed automatic conversion left no `[ERR]` line although the
    summary points to one; it now names the conversion failure.
  - `convert.sh` and `install.sh`: an unknown option printed no usage. `convert.sh
    --help` read a fixed line range that cut off `--parallel` and `--jobs`, did not
    describe `--out`, and omitted the registered `dsh` converter; it now uses
    sentinels and the test checks every registered tool is listed.
  All nine now run in CI and in `verify-release.sh`.
- **Relay:** model prices accepted `true` and `Infinity` (`math.floor` then raised
  instead of refusing the request); they must now be finite non-negative numbers.
- **Trial runner:** budget policies accepted an infinite limit; refused now.
- **Evaluation boundary:** the improvement gate now refuses held-out roots inside the
  public checkout, as the campaign already did, and both refuse packs that reuse a
  published material file byte for byte, which a copy outside the checkout used to
  pass. Both guards are mechanical, not proof of secrecy.
- `CONTRIBUTING.md` described hand-maintained `AGENT_DIRS` and tool lists and put
  renderers in `convert.sh`; it now matches the registry-driven scripts.
- Remove two unused imports and a dead installer variable; mark 33 scripts with a
  shebang executable.

## Alpha Research Suite integration — 2026-10-10

- Add six non-executing investment research specialists and a versioned common artifact envelope.
- Extend the existing Investment Hypothesis Validation optional roster, preserving Macro → Quant P8 independent validation.
- Keep the suite's evidence classes separate from NEXUS claim and decision vocabularies.
- Run the six synthetic standard-library examples in CI and update the generated catalog to 506 agents.

## NEXUS Overdrive, Phase 2: throughput — 2026-10-10

- Add the parallel schedule to the trial runner: ready tasks the engine admits start
  together (bounded by `--max-parallel` and remaining calls); acceptance may come in
  any order; concurrent calls are charged once in wall time. `sequential` stays the
  default. A `<trials>.schedule` manifest keeps the two schedules in separate files.
- Add the plan linter (`scripts/nexus-lint.py`): critical path, depth, widest level;
  warnings for serialized resources, budget headroom, single-source, dependent or
  same-agent assertion keys, and multiple final tasks.
- Add `nexus-campaign.py plan --schedule parallel` and `throughput`, the Phase 2 exit:
  `ADOPT_PARALLEL` only when median NEXUS wall time falls with no more fatal defects
  or constraint violations, and Phase 1 did not redirect.
- Live check on a development pack: two tasks ran concurrently and the run completed
  in 59 s against 76 s sequential (one sample; not evidence).
- Add 19 tests.

## NEXUS Overdrive held-out packs, first set — 2026-10-10

- Add three frozen held-out case packs by `claude-session-pack-author`:
  `harbor-pricing-intent` (attributed-intent), `freight-exclusivity-lapse`
  (expired-premise) and `clinic-reminder-release` (qa-versus-purpose). Each buries
  its trap in ordinary detail; the development smoke run showed an obvious trap
  does not separate the variants.
- That label is barred from authoring improvement proposals judged on these packs;
  the gate and the campaign refuse it as `--improver`. Three more packs from
  another author are needed for the Phase 1 exit.

## NEXUS Overdrive, Phase 1: measurement — 2026-10-10

- Add the Overdrive charter (`strategy/NEXUS-OVERDRIVE.md`): planner, orchestrator,
  synthesis and contract engine are overhauled in three phases; the owner's gates stay.
- Add frozen case packs (`scripts/nexus-casepack.py`): brief, materials, rubric,
  output contract, roster and NEXUS instance hashed into `inputs_hash`; a frozen pack
  cannot be edited, only replaced under a new id. Two synthetic development packs.
- Add the trial runner (`scripts/nexus-trial.py`) for `single_agent`, `fixed_team`
  and `nexus_instance` under a named budget policy, with a deterministic fake executor
  for tests. NEXUS runs pause for independent acceptance and block on assertion
  conflicts until the owner resolves them; owner wait is excluded from wall time.
- Add the self-improvement gate (`scripts/nexus-improve.py`) and its protected-path
  policy (`strategy/overdrive-protected.json`, read from the base revision): no change
  to the evaluator, tests, CI or held-out packs; held-out Pareto non-regression with
  zero tolerance for fatal defects; never merges.
- Add the Phase 1 campaign (`scripts/nexus-campaign.py`): exit and kill rule fixed
  in code; `plan` prints missing runs and their spend ceiling without spending;
  `status` returns `INCOMPLETE`, `PROCEED_TO_PHASE_2` or `REDIRECT`. Fake-executor
  rows and packs written by an improver never count.
- Add `nexus-casepack.py new` (placeholders refused until written) and the
  held-out authoring guide; the improvement gate now requires `--improver` and
  refuses held-out packs that improver wrote or froze.
- Start the live host with an allowlisted environment and refuse a call that reuses the
  calling session id. A live smoke run from inside a Claude Code session showed the
  inherited environment loading that session's tools, plugins and context into the
  trial (286k tokens, $1.20 for one answer); with the allowlist the same answer took
  14k tokens and $0.09. Smoke rows are kept out of the repository; they are not evidence.
- Add 54 tests across the four tools and wire them into CI and the release gate.

## NEXUS assertion conflicts (P7) — 2026-10-10

- Tasks may declare `asserts`: shared keys their accepted result must state a value for.
  Accepted finishes must assert exactly those keys with scalar values.
- `plan` reports `assertion_conflicts` among current accepted results and
  `shared_model_tasks` from the new optional `model_id` on `start`.
- A task cannot start over conflicting results from its direct dependencies;
  success closure and `SUFFICIENT_RESULT` are refused while a conflict is unresolved.
- Add owner-only `resolve_conflict`; a resolution lapses when a new result changes
  the competing values.
- The live pilot records `model_id` and accepts `--asserts`.
- Add 9 engine tests and 1 pilot test.

## NEXUS independent judgment (P1–P6) — 2026-10-10

- **P1** Refuse an accepted `finish` issued by the task agent; acceptance needs the
  owner or a reviewer distinct from the agent. Agents may report non-accepted finishes.
- **P2** Record every task output reference; refuse promotion to `EVIDENCE` when an
  added reference is a task output or when no new source root is added.
- **P3** Require the owner and `evidence_refs` to widen or transfer a scoped claim;
  narrowing a `shared` claim remains a reviewer action.
- **P4** Refuse `SUFFICIENT_RESULT` under a `HOLD` decision, with open
  `PENDING_EVIDENCE`, or with unanswered dissent.
- **P5** Add `dissent_response` (owner; `UPHELD`, `RISK_ACCEPTED`, `REFUTED`); open
  dissent blocks success closure and sufficient-result termination.
- **P6** Add `release_reserve` (owner; named contingency, bounded amount). Relay
  reservations and `plan` use the effective reserve; `plan` reports releases and open dissent.
- Add 15 engine regression tests and one Relay test; tighten the promotion test.
  Checkpoints from earlier versions must be regenerated by full replay.

## Kimi Code adapter migration — 2026-09-15

- Migrate Kimi from the legacy `~/.config/kimi/agents/<slug>/agent.yaml` + `system.md` adapter to current Markdown custom agents under `$KIMI_CODE_HOME/agents/` (default `~/.kimi-code/agents/`).
- Preserve the repository privilege boundary explicitly: source agents without `tools` render `tools: []`; declared capabilities are allowlisted, `WebFetch` maps to Kimi `FetchURL`, and unknown source tokens fail conversion.
- Add current-format renderer/installer regression coverage and advertise Kimi project scope in `tools.json`.

## Closure integrity and Gate 0 guards — 2026-09-16

- Refuse NEXUS `SUFFICIENT_RESULT` termination with an open `FATAL_DEFECT` or a
  `REJECT`/`REDESIGN` decision. Matching negative outcomes remain available.
- Reject cross-scope claims at rebind, including the complete claim ancestry,
  preserving the result invalidation and closure guards introduced in PR #24.
- Report explicit errors for unknown condition/claim IDs and missing event time/type.
- Annotate every option dominance edge with `evidence_basis` and `measured_only`;
  comparisons based on hypotheses are visibly distinct from measured observations.
- Add a structural HTP Gate 0 validator and regression tests for network scope,
  manifest/freeze-date binding, evidence status, roster and prohibited live actions.
- Align CI and the complete release gate with NEXUS fixture and Gate 0 validation;
  install PyYAML explicitly for runbook and Hermes workflows.
- Remove two unused imports and refresh the README roster count.

## Privilege and provenance hardening — 2026-09-14

- Add a closed `scripts/agent-tools.json` security registry for the five tool tokens
  retained by the reviewed 490-agent roster. CI validates the canonical scalar
  representation, rejects duplicate/unknown tokens, and derives the effective
  privilege class (`read`, `network-read`, `write`; `execute` is reserved) from
  registry data.
- Review all 11 profiles that declared `Bash` (four Mispriced CMO and seven
  paid-media profiles). None requires shell execution for its stated workflow;
  remove `Bash` from all 11 and from the closed registry, leaving **zero execute
  profiles**. Reintroduction now requires an explicit security-registry change.
- Treat privilege-registry changes as lint infrastructure so a semantic change to
  a tool forces a full-roster validation. Add privilege tests and the checker to
  the local release gate.
- Harden the OpenClaw importer so `--source-ref` must be an immutable full commit
  SHA and exact downloaded bytes for `agents.json` and every discovered `SOUL.md`
  must match the Git blob IDs from that pinned tree before normalization.
- Make source verification fail closed: any missing/mismatched/unreadable source
  aborts before agent, registry or stale-path writes. Add offline regression tests
  for Git-object hashing, blob mismatch rejection and immutable-ref validation.
- Correct the security documentation: agent Markdown is inert in the repository,
  but a host may honor `tools:` as runtime capability requests; declarations do
  not themselves grant authorization.

## Domain expansion and CI discovery hardening — 2026-09-14

- PR #17 fixes changed-agent discovery in pull-request linting: agent files placed
  directly under a canonical division can no longer make the lint workflow report
  success while skipping both the linter and originality check. The registry-driven
  path filter has direct-root/nested regression coverage and is part of the release gate.
- PR #16 adds bounded Mediterranean convective nowcasting, labor/employment
  litigation support, and ES/EN brand/menu localization specialists. The nowcasting
  profile has no shell privilege and does not treat CAPE/shear cutoffs as universal
  decision authority; the legal profile requires current-source verification for
  material deadlines; the localization profile separates language QA from legal or
  allergen certification.
- Add a dated institutional self-test **exercise plan** aligned one-to-one with the
  canonical eight predicates. It remains `NOT_DEMONSTRATED` until dated evidence
  exists, rejects aggregate scoring, and does not manufacture independent authority.
- Regenerate `CATALOG.md` and the conversion manifest for **490 agents**, retaining
  19 divisions, eight runbooks and 14 converted tool formats. The strict conversion
  gate passes 27/27 and installers pass on Ubuntu and macOS.

## Closure, registry and conversion hardening — 2026-09-14

- PR #15 completes substantive structured `termination_contract` objects across
  all eight NEXUS runbooks and makes contract absence a release error.
- PR #14 makes `tools.json` authoritative for supported-tool membership/order and
  install-kind grouping while retaining explicit renderer/install implementations;
  CI actions are pinned, permissions reduced and ShellCheck runs at error severity.
- PR #13 introduces granular incremental conversion state for per-agent adapters,
  including changed-agent staging, corruption/orphan repair, rename/delete pruning,
  duplicate-output rejection and clean full-rebuild fallbacks.
- PR #12 adds reproducible non-gating conversion benchmarks, canonical division
  discovery, and removes residual conversion hot-path subprocess work.
- PR #11 reduces conversion subprocess overhead and parallelizes commit-pinned
  OpenClaw source fetching without changing generated adapter contracts.

## Doctrine alignment — 2026-09-14

- Integrate the supplied doctrine patch on top of PR #8, preserving all 487
  agents and the existing installer and CI fixes.
- Add attributed-intent status, fourteen named pathologies, scoped test
  inapplicability, explicit precedence, and evidence requirements for independence.
- Add two structured closure contracts and reject malformed contracts and
  placeholder criteria; retain advisory adoption for the other six runbooks.
  PR #15 later supersedes the advisory state by requiring contracts on all eight.
- Add contract regression tests to CI and the release gate.
- Add an institutional self-test that distinguishes demonstrated results from
  missing evidence. Correct unsupported historical conclusions in the supplied
  patch; a template field or different model does not certify functioning.
- Regenerate the conversion manifest from the current source tree.

## Review follow-up — 2026-09-14

- Make stale catalog and converted-output manifests fail pull-request CI, matching
  the existing main-push checks. Regeneration must be committed before merge.
- Document the checked OpenClaw source pin, 196 source-path/blob matches, import
  and alias counts, upstream manifest scope differences, and manual sync policy.
- Add a worked Mispriced CMO handoff to marketing, sales and product, with owner
  acceptance, evidence limits, stopping rules and installation commands.
- Add a historical division-count comparison and runbook index to the README.
- Clarify checked-in validation dependencies, simulated Hermes test boundaries
  and Solana specialist governance outside HTP.

## Consolidation and functional installation

[PR #6](https://github.com/bionic0x/Ante-agency-agents/pull/6) introduced the
11-agent Mispriced CMO division, two runbooks and the generated complete catalog,
taking the roster from 476 to 487 agents across 19 divisions and eight runbooks.
It also repaired damaged headings and consolidated doctrine references.

[PR #7](https://github.com/bionic0x/Ante-agency-agents/pull/7), merged as
`6a506f174747fd34d1efc542f4fe316e32dd28a9`, hardened filtered installation,
parallel argument handling, failure propagation, destination handling,
conversion freshness and Hermes lifecycle validation; added runbook selection
and release verification; and removed obsolete bootstrap machinery.

The 186 normalized community imports and 10 aliases predate those two PRs.
They derive from `mergisi/awesome-openclaw-agents` at
`05820c51125e86a979432e21651d34dc9b14621f`.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for attribution and
[strategy/UPSTREAM-SYNC.md](strategy/UPSTREAM-SYNC.md) for verification limits.

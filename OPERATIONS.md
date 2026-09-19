# Operating this repository

This repository provides 492 agent profiles, 19 divisions, eight NEXUS runbooks,
and adapters for 16 AI tools. It is a catalog and installation system. The host
tool supplies the model, execution loop, authentication, and external access.

## Install a bounded team

From the cloned repository, use:

```bash
bash scripts/install.sh --list runbooks
bash scripts/install.sh --tool claude-code --runbook htp-gate0-solana-arbitrum --dry-run
bash scripts/install.sh --tool claude-code --runbook htp-gate0-solana-arbitrum
```

The runbook resolves nine unique agents, including the Strategic Assurance Lead
and Legal Compliance Checker. The roster includes conditional specialists;
their activation conditions remain in `strategy/runbooks.json`. Start the host
in this checkout so relative `strategy/` references resolve. Read the scenario,
the network overlays, and the six Gate 0 artifacts before beginning the work.
The Solana and Arbitrum tracks retain separate evidence and decisions.

Use `--agent` or `--agents-file` with canonical filename IDs from `CATALOG.md`,
adapter slugs, or display names. Filters combine as a union. Empty or unknown
selections fail before installation. `--runbook` installs profiles; it does not
execute a scenario, sign off evidence, or authorize live actions.

## Other tools and destinations

```bash
# Install a selected team into two tools; workers preserve quoted arguments.
bash scripts/install.sh --tool claude-code,codex --division mispriced-cmo --parallel --jobs 2

# Project-scoped Claude profiles, with an explicit destination.
bash scripts/install.sh --tool claude-code --runbook htp-gate0-solana-arbitrum --path .claude/agents
```

`--path` is a destination directory. Conflicting tool formats cannot share it.
Copilot uses only the explicit path when provided; without an override it writes
both default locations. Aider and Windsurf also honor `--path`.

Aider, Windsurf, and Hermes install a whole-roster file or plugin. They reject
selection flags rather than silently installing more agents than requested.
Hermes loads specialist prompts lazily. Other adapters support selection.

The installer checks source and generated-output hashes before reusing converted
adapters. Missing or changed output is regenerated. `--no-convert` deliberately
skips freshness checks but still rejects an incomplete selected roster. A failed
conversion, copy, registration, or worker must not be treated as success; earlier
tools in a multi-tool install may already have completed. Re-run after fixing the
reported cause. The installer does not remove unrelated pre-existing profiles.

`--link` links installed files to this checkout's source or generated adapters.
Keep the checkout at the same path. Switching back to copy mode replaces the
link without modifying its source.

## Agent tool privileges

Agent `tools:` metadata is a runtime capability request, not authorization. The
canonical source form is one comma-separated scalar because that is the contract
consumed by `lib.sh` and the adapters that preserve tool metadata.

`scripts/agent-tools.json` is the closed privilege registry. The reviewed roster
uses exactly five registered tokens: `Read`, `WebSearch`, `WebFetch`, `Write`,
and `Edit`. Their current declared classes are `read`, `network-read`, and
`write`; the schema reserves `execute` as the next-higher class but **no execution
tool is registered and no explicit declaration is classified `execute`**. The 11 profiles that
previously declared `Bash` were individually reviewed and did not require shell
execution for their stated workflows, so that token was removed from both those
profiles and the registry.

Unknown or malformed tokens fail CI until their security semantics are explicitly
added to the registry. Reintroducing `Bash` or any execution capability therefore
requires a reviewed registry change as well as the requesting profile change.
Changing the registry is lint infrastructure and forces a full-roster privilege
validation.

The registry describes capability, not entitlement. Host sandboxing, credentials,
the user mandate, repository policy and runbook decision rights still govern use.
Prefer the minimum declared tool set and do not infer permission to mutate files
or perform external I/O from the presence of a token alone.

## Verify before release

Use Python 3.11+ for validation:

```bash
python3 -m pip install -r scripts/requirements-validation.txt
bash scripts/verify-release.sh
```

The gate checks registry consistency, changed-agent discovery, the closed agent
privilege schema, full agent lint, offline OpenClaw provenance-verifier regression
tests, all runbook resolutions, catalog freshness, Hermes routing and lifecycle
behavior, installer regressions, all 16 installation routes in isolated fixtures,
and strict parsing, counts and drift for every agent across the 14 converted
formats. Pull-request CI also exercises Linux and macOS installation behavior.

After intentional profile or converter changes:

```bash
python3 scripts/build-catalog.py
bash scripts/test-convert-outputs.sh --update
```

Commit the regenerated catalog and hash manifest with the change. Do not update
a golden hash to hide a converter, registry, or contract drift: inspect the
manifest delta first. The public upstream desktop app and live host/model
sessions are separate compatibility surfaces: file installation and offline
validation do not establish that a host has authenticated, discovered, or
successfully executed a specialist. Restart the host and verify the selected
profiles there. Claude's current loading rules are documented in its
[subagent reference](https://code.claude.com/docs/en/sub-agents); Copilot's are
in its [configuration reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration).

## Doctrine alignment and closure review

The claim register distinguishes `ATTRIBUTED_INTENT`; the assurance profile
retains all fourteen strategic pathologies. Coherence tests may declare
`NOT_APPLICABLE` with a reason, except for the Epistemic and Exit tests.

Every registered runbook now carries a structured `termination_contract`.
`check-runbooks.sh` requires all eight contracts and rejects missing fields,
placeholder values, unknown keys, malformed optional fields and unresolved
artifact/roster references. The contract answers what was achieved, what remains
outstanding, who is accountable and what happens on breach. Optional conservation
and revision fields remain scoped extensions; their thresholds are runbook-local,
not universal doctrine. Structural validity does not establish that a real closure
decision was adequate.

Before release or a governance change, the release owner records the
[institutional self-test](strategy/INSTITUTIONAL-SELF-TEST.md), with evidence,
scope, unresolved gaps and accountability. CI cannot certify independence or
institutional functioning. The baseline records those predicates as
`NOT_DEMONSTRATED`; it does not invent completed governance exercises. The dated
[institutional exercise plan](strategy/INSTITUTIONAL-SELF-TEST-EXERCISE-2026-09.md)
is a plan for collecting that evidence, not a certificate or score.

## Repository ruleset — Admin-required enforcement

Repository settings are part of the release boundary. At the 2026-09-14 review,
the active ruleset `mAIN` (ID `23156139`) targeted `~ALL`, blocked ordinary
updates to feature branches, and did not require pull requests or CI checks on
`main`. This was observed directly when a temporary PR #16 generation job was
rejected with `GH013: Cannot update this protected ref` on a feature branch.

This cannot be repaired from repository contents alone. An administrator must
edit **Settings → Rules → Rulesets** so that the protection targets `main` (not
all branches), blocks deletion and force-push there, requires a pull request, and
requires these current job contexts before merge:

- `Validate agent frontmatter and structure`
- `divisions.json is the single source of truth`
- `runbook rosters reference real agent slugs`
- `tools.json is the single source of truth`
- `install.sh hermes config rewrite`
- `install.sh behavior (ubuntu-latest)`
- `install.sh behavior (macos-latest)`

Broad always-bypass roles/integrations should be removed unless they have a
named emergency or release purpose. Acceptance is operational, not textual:
an ordinary feature branch must be creatable/updatable/deletable without bypass;
a PR to `main` must remain unmergeable while a required check is pending/failing;
and direct force-push/delete/update of `main` must remain blocked for ordinary
actors. Do not treat this section as evidence that the setting has been changed.

## Validation implementations and upstream updates

The validation dependencies and checked implementations include:

- [requirements-validation.txt](scripts/requirements-validation.txt)
- [agent-tools.json](scripts/agent-tools.json)
- [check-agent-privileges.py](scripts/check-agent-privileges.py)
- [test-agent-privileges.py](scripts/test-agent-privileges.py)
- [test-openclaw-import-provenance.py](scripts/test-openclaw-import-provenance.py)
- [check-hermes-plugin.py](scripts/check-hermes-plugin.py)
- [test-hermes-plugin.py](scripts/test-hermes-plugin.py)
- [build-catalog.py](scripts/build-catalog.py)
- [list-changed-agent-files.py](scripts/list-changed-agent-files.py)
- [test-changed-agent-files.py](scripts/test-changed-agent-files.py)

Hermes lifecycle tests use a simulated lifecycle and a fresh generated plugin;
they do not replace an authenticated host smoke test. Catalog freshness and
converted-output drift fail CI on pull requests as well as pushes to main.
Regenerate and commit both artifacts before merge.

See the [source verification and sync policy](strategy/UPSTREAM-SYNC.md) and
[Mispriced CMO cross-division example](examples/mispricing-cross-division.md).

## Solana specialist outside HTP

The Solana Program Engineer is registered in the nine-agent HTP runbook alongside
assurance, research, product, legal and security roles. Resolution and installation
tests verify those profiles are available; they do not certify the technical
correctness of generated Solana code.

For another project, invoke it under that project's named owner, scope and
applicable runbook. A bounded code review can return account/CPI findings and
tests without granting deployment authority. A material product or architecture
decision uses the general strategic decision process; do not carry HTP's
14-day horizon, network scope, or Gate 0 decision rights into unrelated work.
The profile's technical vocabulary about signer or upgrade authority does not
confer business authority. When the owner or authorization is unresolved, return
the technical analysis and escalate the pending decision.

## NEXUS contract hardening

The runbook validator now resolves real agents through the same catalog used by
installation, rejects empty document paths, placeholder decision owners and
unknown modes, and handles malformed fields without a traceback. The strategic
vocabulary lives in `strategy/contracts.json`; CI checks that the claim-register
and handoff templates preserve it. BORING WINS material decisions now also
require a Strategic Decision Record. A role in a runbook template is not a named
appointment; resolve the owner in each live instance.

The Agents Orchestrator coordinates by dependencies and intent. Task acceptance
never lifts a strategic HOLD. Retry budgets belong to instances, evidence must
fit the claim, and independent work may continue under its existing mandate.

### Prepared ruleset correction — not applied

`.github/rulesets/main.json` is a proposed replacement for ruleset `23156139`.
It requires PRs and the seven current check contexts on `main`, removes blanket
branch creation/update restrictions, and contains no always-bypass entries.
No human approval count is imposed: required review-thread resolution and passing
checks remain mandatory. The lint workflow runs for every PR and main push so
its required context cannot be absent due to path filtering.

The connected GitHub tools can read this ruleset but expose no administration
write operation. An authorized administrator can apply the reviewed payload:

```bash
gh api --method PUT repos/bionic0x/Ante-agency-agents/rulesets/23156139 \
  --input .github/rulesets/main.json
```

Before applying, confirm the live check names and the removal of each historical
bypass entry. After applying, read back the ruleset and run the operational
acceptance checks above with an ordinary actor. The presence of this JSON file
is not evidence that GitHub settings changed. Do not work around a rejected
branch operation by editing protections or invoking a bypass from automation.

## Live host acceptance — recorded, with its method attached

Installation tests establish what a file contains. A **host acceptance record**
contains supplied observations of a host. It does not authenticate the operator,
authority label, host process or evidence producer. `scripts/probe-host-claude-code.py` drives a
real Claude Code host and writes one record per agent under
`evidence/host-acceptance/`; `scripts/host-acceptance.py` validates records and
derives their status. The record never grades itself.

```bash
python3 scripts/probe-host-claude-code.py --agent <slug> \
  --policy scope-policy.json --out evidence/host-acceptance/<host>-<slug>.json
python3 scripts/host-acceptance.py validate evidence/host-acceptance/*.json
python3 scripts/host-acceptance.py emit-observation evidence/host-acceptance/<file>.json \
  | python3 scripts/agent-capabilities.py inspect --agent <slug> --observation /dev/stdin
```

Every probe carries the method that produced it, and the validator refuses an
outcome its method cannot support. `filesystem` never establishes enforcement.
`host-resolution` — the host binary reporting its own agent resolution, with no
model turn — can settle what the host *offers*: discovery, revocation, scope
isolation, post-expiry availability. Only `live-session` can settle what the host
*executed*: the resolved tool set, a permitted call, a refused one. A record that
reports `ENFORCED` from a file read is rejected rather than downgraded. For the
three session probes, the validator also reads the referenced transcript, checks
the resolved tools and refuses positive execution claims unsupported by its
events. Method labels alone do not establish those outcomes. Host-listing and
filesystem observations remain supplied attestations; this is not an adversarial
attestation or independent certification system.

Derived status is `ACCEPTED` only when all eight probes are positive;
`BOUNDARY_NOT_ENFORCED` when a boundary demonstrably failed; `NOT_DEMONSTRATED`
when any probe was not attempted. An untested boundary never reads as a pass.

### Recorded result — Claude Code 2.1.276, one agent, project scope

`evidence/host-acceptance/claude-code-specialized-pricing-analyst.json` records a
scoped profile (`allowed_tools: ["Read"]`, rendered by `agent-capabilities.py`)
reported on Claude Code 2.1.276 in the user-supplied historical run. The recorded
init event exposes only `Read`; the completed session withholds `Write`. The
supplied record reports discovery, installed-profile body equality, scope
isolation and revocation. Body equality is a filesystem observation, not proof
of the host's actual system prompt. The retained frontmatter excerpt alone does
not independently verify that equality.

**The permitted Read is INCONCLUSIVE:** the supplied transcript contains its
request but omits its `tool_result`. Model prose saying it succeeded is not an
execution oracle. Future probes retain matching tool results and require a
non-error result for the expected target content. **Expiry remains reported
NOT_ENFORCED:** the supplied post-expiry listing still offers the profile. This
is availability evidence for this configuration, not proof that every version
or mode lacks expiry support. Overall status remains `BOUNDARY_NOT_ENFORCED`.

This integration did not rerun a live host: no Claude CLI was available in the
review environment. The record's original timestamps and source binding are
retained. Session evidence is minimized to decision-relevant event fields;
plugin inventories, local plugin paths and unrelated telemetry are omitted.
The original uploaded files remain unchanged. Historical fixture validation
uses the observation clock; it never makes expired evidence current again.

Two mechanical findings from the same run:

- The host addresses a profile by its frontmatter `name` (`Pricing Analyst`), not
  by its file slug (`specialized-pricing-analyst`) in the supplied run. The probe
  therefore parses the YAML `name` rather than assuming a filename identifier.
  This observation is limited to the recorded host version and profile.
- An out-of-allowlist tool is **withheld**, not denied at call time, so the
  session's `permission_denials` stays empty. Treating that array as the oracle
  for allowlist enforcement would read a withheld tool as a successful call.

Scope of the claim: one agent, one host version, project scope, one sandbox. It is
not a certification of the other 489 agents, of user scope, or of any other host.
The probe currently rejects scopes other than `project` and allowlists other
than `["Read"]`; its fixed Read/Write protocol cannot measure arbitrary policies.
Kimi has no probe yet and therefore no record; absence of a record is
`NOT_DEMONSTRATED`, not a pass.

## Declared capabilities versus host behavior

An absent `tools` field is `unspecified`, not proof of no tools. Claude Code may
inherit capabilities from the parent session. The closed registry validates
explicit requests; it cannot establish the tool pool or permissions of a host.
Explicit YAML null is invalid and cannot disguise an omitted policy.

```bash
python3 scripts/agent-capabilities.py inspect --agent agents-orchestrator
python3 scripts/agent-capabilities.py inspect --agent agents-orchestrator \
  --observation host-observation.json --policy scope-policy.json
python3 scripts/agent-capabilities.py render --agent agents-orchestrator \
  --policy scope-policy.json --output /tmp/scoped-agent.md
```

The diagnostic reports declarations, supplied host observations and the candidate
intersection with the supplied scope policy separately. It does not authenticate
an authority record or claim live enforcement. Observations must include the
source SHA-256, host/version, configuration/evidence references, observed time,
valid-until time and resolved tool names. Reject expired or mismatched records.

A scope policy contains `host: claude-code`, canonical `agent_id`, `scope`, `owner`,
`authority_ref`, zoned ISO `expires`, and a non-empty `allowed_tools` array from the
closed registry. Rendering cannot expand an explicit source allowlist or overwrite
an existing file. It prepares a profile for review; it does not install it or
prove enforcement. The host/operator must enforce expiry and revoke/remove stale
profiles. For other hosts, capability translation remains unverified; do not
apply Claude syntax and label it portable. The next live smoke test must verify
actual discovery, resolved tools and denied operations in that host version.

Primary host semantics: https://code.claude.com/docs/en/sub-agents#available-tools

## NEXUS instance pilot

See [NEXUS-INSTANCE.md](strategy/NEXUS-INSTANCE.md) for the executable offline
planner, typed events, claim revision/expiry, selective HOLD, cumulative budgets,
resource ownership, termination and replay recovery. The pilot reuses three
canonical agents from `strategic-decision`; it does not activate the full roster.

`nexus-options.py` compares admissible options without weighted scoring and exposes
sensitivity to declared scenario values. `evaluate-nexus.py` joins recorded
three-variant host trials with blind reviewer judgments under the protocol in
[NEXUS-MEASUREMENT-PROTOCOL.md](strategy/NEXUS-MEASUREMENT-PROTOCOL.md). The
checked-in trial and judgment files are empty and yield `NOT_MEASURED`: no
model-quality gain or host enforcement is claimed.

Nine metrics are reported separately — five counted by the runner (cost, tokens,
wall time, invalid decisions, rework cycles) and four by a blind reviewer (factual
errors, fatal defects, constraint violations, evidence coverage as a fraction).
There is no composite score and no ranking: the metrics trade against each other,
any weighting encodes a purpose the tool does not hold, and a single number would
make a fatal defect purchasable with a lower token count. Inputs carrying a
`score`, `rank`, `overall`, `winner` or `composite` field are rejected.

`nexus-blind.py seal` prepares opaque artifact names, a shuffled index, case
scenarios, expected behavior and artifact hashes. It rejects unsafe IDs, symlinks
and known self-narration before publishing a packet. This reduces direct label
leakage but cannot certify blinding. Preserve original outputs; any redaction
must follow the preregistered protocol, not selective post-run editing.
Reviewer identifiers matching any trial operator are rejected, but identities
are not authenticated. Primary comparisons use only fully judged three-variant
pairs for all nine metrics; execution-only summaries are separate. Missing
submissions and all supplied fatal findings remain visible even when excluded
from comparisons. The evaluator checks equal model, host, input and budget
labels; it does not authenticate counters, budget enforcement or preregistration.

The plan/replay engine performs no model calls or external actions. A live adapter,
authenticated authority, tool enforcement and measured model trials remain separate
acceptance work. Both HTP networks retain their documented HOLD.

`check-htp-gate0.py` guards the machine-readable Gate 0 instance: each handoff names
one network, resolves to a manifest of that network and freeze date, uses the Gate 0
evidence ladder, names HTP roster agents, and keeps live actions prohibited while no
`authority_ref` exists. It checks recording boundaries, not on-chain facts.

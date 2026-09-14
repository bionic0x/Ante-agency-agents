# Operating this repository

This repository provides 487 agent profiles, 19 divisions, eight NEXUS runbooks,
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

## Verify before release

Use Python 3.11+ for validation:

```bash
python3 -m pip install -r scripts/requirements-validation.txt
bash scripts/verify-release.sh
```

The gate checks registry consistency, agent lint, all runbook resolutions,
catalog freshness, Hermes routing and lifecycle behavior, installer regressions,
all 16 installation routes in isolated fixtures, and strict parsing, counts and
drift for every agent across the 14 converted formats.

After intentional profile or converter changes:

```bash
python3 scripts/build-catalog.py
bash scripts/test-convert-outputs.sh --update
```

Commit the regenerated catalog and hash manifest with the change. CI runs the
installer suites on Linux and macOS. The public upstream desktop app and live
host/model sessions are separate compatibility surfaces: file installation and
offline validation do not establish that a host has authenticated, discovered,
or successfully executed a specialist. Restart the host and verify the selected
profiles there. Claude's current loading rules are documented in its
[subagent reference](https://code.claude.com/docs/en/sub-agents);
Copilot's are in its [configuration reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration).

## Doctrine alignment and closure review

The claim register distinguishes `ATTRIBUTED_INTENT`; the assurance profile
retains all fourteen strategic pathologies. Coherence tests may declare
`NOT_APPLICABLE` with a reason, except for the Epistemic and Exit tests.

`check-runbooks.sh` rejects placeholder termination criteria and validates
structured `termination_contract` fields when supplied. Absence is advisory;
an explicit null, incomplete object, unknown key, or invalid optional field is
an error. This checks structure, not the adequacy of a closure decision.
The mispricing diagnostic and manuscript runbooks carry contracts (2/8);
the other six retain their existing criteria pending owner-authored contracts.
Thresholds in a domain contract are scoped to that runbook, not universal rules.

Before release or a governance change, the release owner records the
[institutional self-test](strategy/INSTITUTIONAL-SELF-TEST.md), with evidence,
scope, unresolved gaps and accountability. CI cannot certify independence or
institutional functioning. The baseline records those predicates as
`NOT_DEMONSTRATED`; it does not invent completed governance exercises.

## Validation implementations and upstream updates

The validation dependencies and Hermes/catalog implementations are checked in:

- [requirements-validation.txt](scripts/requirements-validation.txt)
- [check-hermes-plugin.py](scripts/check-hermes-plugin.py)
- [test-hermes-plugin.py](scripts/test-hermes-plugin.py)
- [build-catalog.py](scripts/build-catalog.py)

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

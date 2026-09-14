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

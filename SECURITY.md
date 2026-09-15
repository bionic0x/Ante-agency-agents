# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, report it responsibly. Do **not** open a public GitHub issue for security vulnerabilities. Open a private security advisory through the GitHub Security tab.

## Response Timeline

- Acknowledgment: within 48 hours
- Initial assessment: within 7 days
- Fix or mitigation: depends on severity

## Scope

This repository contains Markdown-based agent definitions plus executable installation, conversion, validation, and import tooling.

### Agent files (`*.md`)

Agent Markdown is data in this repository; storing a prompt does not itself execute code. After installation, however, a host may interpret frontmatter such as `tools:` as a request for runtime capabilities. Tool metadata therefore belongs to the security boundary.

The canonical source representation is one comma-separated scalar. `scripts/agent-tools.json` is the closed registry for recognized capabilities and their security semantics. CI rejects malformed declarations, duplicate tokens, and any tool token that has not first been added to that registry.

Privilege classes are ordered by maximum capability:

- `read` — local/context reads (`Read`)
- `network-read` — external lookup/fetch without repository mutation (`WebSearch`, `WebFetch`)
- `write` — host-exposed local mutation (`Write`, `Edit`)
- `execute` — reserved for process/shell execution; **no execute-capability tool is registered in the current baseline**

The reviewed 490-agent baseline contains five registered/observed tool tokens and zero explicit `execute` declarations. Reintroducing `Bash` or another execution capability therefore requires both an explicit security-registry change and the requesting agent change; adding the token to an agent alone fails CI.

A tool declaration is **not authorization**. The host, sandbox, user mandate, repository policy, credentials, and applicable runbook still determine whether a capability is actually available or permitted. Do not store API keys, tokens, passwords, or other secrets in agent files.

### Executable repository tooling

Files under `scripts/` include executable shell and Python programs. Contributors must review their behavior before running them. Shell scripts are syntax-checked and statically analyzed in CI; release validation exercises installer and converter failure modes on Linux and macOS.

### Imported-source provenance

OpenClaw community imports are pinned to a full 40-hex Git commit SHA. The importer obtains blob IDs from that commit's recursive Git tree and verifies the exact downloaded bytes for `agents.json` and every imported `SOUL.md` using the Git blob object hash before decoding or normalizing content.

A missing file, malformed expected blob ID, byte mismatch, decode failure, or source-fetch failure aborts the import before repository files are written. Provenance verification establishes byte identity with the pinned Git tree; it does not establish that upstream content is safe, correct, compatible with a runtime, or appropriate to grant tools.

## Best Practices for Contributors

- Never commit API keys, tokens, credentials, or private signing material.
- Treat additions to `scripts/agent-tools.json` as security-sensitive capability changes.
- Prefer the minimum tool set needed by an agent. Shell/process execution is intentionally absent from the current agent registry.
- Never infer runtime authorization from an agent's `tools:` field.
- Review executable scripts and generated-install behavior before merging.
- Report suspicious prompt instructions, provenance mismatches, privilege escalation, or attempts to bypass repository/runbook authority boundaries.

Missing tool metadata is classified as `unspecified`. It may mean host inheritance;
it does not prove zero process execution or zero external access. Keep declared,
host-resolved and authorized capabilities separate. `agent-capabilities.py`
validates supplied observations and prepares narrowed Claude profiles, but cannot
authenticate the operator mandate or enforce expiry. The actual host remains the
security boundary. Do not interpret an offline diagnostic as a sandbox test.

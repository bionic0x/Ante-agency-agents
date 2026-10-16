# Ante — Specialist AI agents, governed by evidence

**A 506-agent catalog and NEXUS coordination toolkit for teams that need traceable decisions, explicit authority, and reproducible workflows.**

[![Runbook CI](https://github.com/bionic0x/Ante-agency-agents/actions/workflows/check-runbooks.yml/badge.svg)](https://github.com/bionic0x/Ante-agency-agents/actions/workflows/check-runbooks.yml)
[![MIT license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**506 agents** · **19 divisions** · **9 runbooks** · **17 registered tool targets**

> **Project maturity:** Agent profiles and offline NEXUS contracts are usable now. NEXUS Relay is a local execution pilot. Overdrive's planner, scheduler, reviewer and optimizer are implemented but **not validated as improving live-model outcomes**. This is not a production-ready autonomous agency or an autonomous trading system.

Ante extends [The Agency](https://github.com/msitarzewski/agency-agents) with strategic assurance, NEXUS orchestration, security controls, specialized research, and evidence-first runbooks. The fork also includes normalized OpenClaw community profiles; see [provenance and synchronization](strategy/UPSTREAM-SYNC.md).

## Start here

| Your goal | What to use | Next step |
|---|---|---|
| Find a specialist | [Generated agent catalog](CATALOG.md) | Select one profile or division |
| Install profiles in an AI tool | [Installer](scripts/install.sh) and [tool registry](tools.json) | Run a dry-run before installation |
| Coordinate a project | [Nine scenario runbooks](strategy/runbooks.json) | Select a scoped team with a named decision owner |
| Validate a decision or task graph | [NEXUS instance contracts](strategy/NEXUS-INSTANCE.md) | Validate and replay a synthetic instance |
| Run a small, owner-controlled group | [NEXUS Relay](relay/README.md) | Review its threat model and host prerequisites |
| Evaluate whether NEXUS adds value | [Overdrive protocol](strategy/NEXUS-MEASUREMENT-PROTOCOL.md) | Establish genuinely unseen cases and independent review |

## Quick start

**Prerequisites:** Git, Bash 3.2+, Python 3 for the installer, and your separately installed AI host. Full validation needs Python 3.11+, PyYAML and the dependencies described in [Operations](OPERATIONS.md). On Windows, use WSL or a compatible Bash environment with `python3` available.

```bash
git clone https://github.com/bionic0x/Ante-agency-agents.git
cd Ante-agency-agents

# Inspect the available runbooks without installing anything.
bash scripts/install.sh --list runbooks

# Preview a bounded team for Claude Code. No files are installed.
bash scripts/install.sh --tool claude-code --runbook strategic-decision --dry-run

# Install only after reviewing the preview and the destination.
bash scripts/install.sh --tool claude-code --runbook strategic-decision
```

The installer makes **profiles available to the host**; it does not summon models, authenticate authority, start NEXUS Relay, or authorize live actions. Your AI host controls invocation and tool access. For a smaller selection:

```bash
bash scripts/install.sh --tool claude-code --agent specialized-strategic-assurance-lead --dry-run
bash scripts/install.sh --tool claude-code --division security --dry-run
```

Discover other targets in [`tools.json`](tools.json), then consult [`OPERATIONS.md`](OPERATIONS.md) for installation, conversion, supported flags, permissions, platform notes, and failure recovery. The [upstream desktop app](https://github.com/msitarzewski/agency-agents-app) is a separate product; support for this fork's custom agents is not established.

## How Ante works

```text
Specialist catalog ──> Select profiles ──> Install to AI host
        │                                         │
        └──> Runbooks ──> NEXUS contracts         │
                          │                      │
                          ├─ Validate / plan / replay (offline)
                          ├─ Evidence, budgets, HOLD, challenger veto
                          └─ Optional local Relay ──> Host-mediated run
                                                        │
                                             Human review / acceptance
```

| Component | Implemented capability | Important boundary |
|---|---|---|
| **Agent catalog** | Profiles with missions, workflows, outputs and proposed success metrics | A written capability is not a measured model capability |
| **Installers/adapters** | Selective installation and conversion for registered targets | Target registration is not a guarantee of host compatibility |
| **Runbooks** | Scoped teams, deliverables, handoffs and exit conditions | Installing a team is not authorization to execute its plan |
| **NEXUS engine** | Task/dependency validation, evidence lineage, claim states, resource budgets, selective `HOLD` and replay | Offline checks do not enforce live host permissions |
| **Relay** | Local, owner-controlled room, bounded container runs, model proxy, evidence accounting and recovery | Pilot; containers share a host kernel and require hardening |
| **Overdrive** | Trial/reviewer tooling; Phase 2 throughput scheduling; Phase 3 planner, decision brief and guarded profile improvement | **Prepared, not empirically adopted**; human gates and Phase 1 measurements remain prerequisites |

The control flow separates **proposal**, **independent challenge**, **owner authority**, and **observed results**. For example, the Macro → Quant pair has a challenger veto, and the [Alpha Research Suite](strategy/alpha-research-suite/README.md) adds six non-executing investment-research specialists. No research profile may authorize a trade.

## Try NEXUS without credentials

The following uses **synthetic, checked-in fixtures** and does not call a live model:

```bash
python3 scripts/nexus-instance.py validate examples/nexus/strategic-decision.instance.json
python3 scripts/nexus-instance.py replay examples/nexus/strategic-decision.instance.json \
  --events examples/nexus/strategic-decision.events.jsonl

# The checked-in trial and judgment records do not establish measured performance.
python3 scripts/evaluate-nexus.py \
  --runs examples/nexus/host-trials.json \
  --judgments examples/nexus/host-judgments.json
```

For contracts, state transitions, and replay semantics, read [NEXUS instances](strategy/NEXUS-INSTANCE.md). For live execution, start with the [Relay threat model](relay/DESIGN.md) and [operations guide](relay/README.md); do not treat the offline example as proof of runtime isolation.

## Evidence, safety, and project status

**As verified on 16 October 2026:**

| Question | Evidence-backed answer |
|---|---|
| How many profiles and workflows? | 506 agents in 19 divisions; 9 runbooks; 17 registered tool targets. [Catalog](CATALOG.md) / [registries](strategy/runbooks.json) |
| Can NEXUS validate task state? | Yes, against its declared contract and synthetic tests. [Specification](strategy/NEXUS-INSTANCE.md) |
| Is multi-provider execution verified? | No. Five providers are declared; the registry has **zero observed/accepted models**. [Provider registry](strategy/providers.json) |
| Has Overdrive shown improvement over a fixed team? | **No recorded independent live comparison** in the checked-in trials and judgments. [Measurement protocol](strategy/NEXUS-MEASUREMENT-PROTOCOL.md) |
| Is Phase 2/3 functionality implemented? | Scheduler, reviewer kit, planner, brief and guarded optimizer are present, but adoption requires gates; implementation ≠ validation. [Overdrive](strategy/NEXUS-OVERDRIVE.md) |
| Can HTP transact on Solana or Arbitrum? | No. The documented Gate 0 instance remains **HOLD** pending network-specific runtime evidence. [Gate 0 status](strategy/htp-gate0/instances/2026-09-13-kamino-aave/instance-status.md) |
| Is Relay a hosted production service? | No. It is a local pilot with owner approvals, container limits and documented residual risks. [Relay](relay/README.md) |

**Independent evaluation matters.** Public example casepacks are exposed fixtures, not unseen test data. Overdrive requires at least **six previously undisclosed evaluator-controlled packs** and **36 live runs** (six cases × three variants × two trials), with a frozen rubric, comparable budgets, and blind judgments. Its decision gate is pre-registered, **not** a statistical significance test. Read the [evaluation boundary](strategy/NEXUS-CASEPACK-AUTHORING.md) before making superiority claims.

**Authority is not a YAML field.** A profile, generated plan, passing CI check, or favorable offline verdict cannot grant access to accounts, funds, production systems or other people's data. Live action requires a valid human mandate, actual host-side enforcement, and applicable approvals. Follow the [security policy](SECURITY.md), [operational limits](OPERATIONS.md), and [institutional self-test](strategy/INSTITUTIONAL-SELF-TEST.md).

## Validation and contribution

From a trusted local checkout, run the reproducible release gate:

```bash
python3 -m pip install -r scripts/requirements-validation.txt
bash scripts/verify-release.sh
```

This verifies repository contracts, catalogs, agent metadata, converters, installers and NEXUS regressions. It does **not** benchmark real model accuracy, establish independent review, or certify a production deployment. GitHub Actions additionally checks platform-specific behavior and security tooling.

To contribute: start with [CONTRIBUTING.md](CONTRIBUTING.md), use the [pull request template](.github/PULL_REQUEST_TEMPLATE.md), regenerate [CATALOG.md](CATALOG.md) and conversion manifests when source contracts change, and include tests for executable changes. Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md). See [CHANGELOG.md](CHANGELOG.md) for releases and historical updates.

## Documentation

| Read | For |
|---|---|
| [Catalog](CATALOG.md) | Search the full agent inventory instead of browsing a giant README roster |
| [Runbook registry](strategy/runbooks.json) · [Quickstart](strategy/QUICKSTART.md) | Select a governing scope, team and handoffs |
| [Operations](OPERATIONS.md) · [Tool registry](tools.json) | Install, configure, validate and troubleshoot adapters |
| [General Strategy Doctrine](strategy/GENERAL-STRATEGY-DOCTRINE.md) | Purpose, non-object, levels, evidence and decision ownership |
| [NEXUS contract](strategy/NEXUS-INSTANCE.md) · [Overdrive](strategy/NEXUS-OVERDRIVE.md) | Engine semantics, tests, optimizer and measured exits |
| [Relay](relay/README.md) · [Threat model](relay/DESIGN.md) | Bounded local execution and residual risks |
| [HTP Gate 0](strategy/runbooks/scenario-htp-gate0-solana-arbitrum.md) · [Alpha Research](strategy/alpha-research-suite/README.md) | Domain-specific non-executing workflows |
| [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) | Responsible changes, disclosures and project history |

### Origins and license

This fork incorporates work from [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) and normalized OpenClaw community sources. Attribution, pinned source verification and sync expectations are documented in [UPSTREAM-SYNC](strategy/UPSTREAM-SYNC.md) and [third-party notices](THIRD_PARTY_NOTICES.md). See the [MIT license](LICENSE).

Need the former long-form roster and tool walkthrough? [Read the previous README snapshot](https://github.com/bionic0x/Ante-agency-agents/blob/5bcc8fbcfd00d95437f0dbac91272dbe445fc6b1/README.md); it is historical and may describe older counts or behavior.

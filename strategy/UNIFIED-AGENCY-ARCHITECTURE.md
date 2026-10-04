# Unified Agency Architecture

> **Decision**: Agency Agents is one agency. External agent collections are capability sources, not parallel agencies.

## 1. Canonical model

The system has one hierarchy:

```text
GENERAL STRATEGY DOCTRINE
        ↓
UNIFIED CANONICAL AGENT CATALOG
        ↓
NEXUS + RUNBOOKS
        ↓
BOUNDED SPECIALIST EXECUTION
        ↓
TOOL ADAPTERS / CONVERTERS
```

The canonical source of an installable agent is a frontmatter agent file inside a division registered in `divisions.json`.

External repositories may contribute capability, patterns, examples, or runtime-specific assets. They do not create a second catalog, second strategy layer, or second orchestration authority.

## 2. Source classes

### Native Agency Agents

Agents maintained directly in this repository remain canonical unless deliberately superseded.

### Imported community capability

Community agents are normalized into the canonical Agency schema when they add a distinct capability.

Every imported agent receives:

- one canonical filename slug;
- one existing Agency division;
- standard Agency frontmatter;
- General Strategy Doctrine subordination;
- explicit authority and tool boundaries;
- source repository, path, commit, and license provenance;
- normal conversion to every supported target via the same `convert.sh` system.

### Alias / merged capability

If an external agent substantially duplicates an existing canonical agent, the external source is registered as an alias/provenance contribution instead of creating another installable persona.

The rule is:

```text
same strategic/technical job
+ same decision level
+ no material capability delta
→ MERGE / ALIAS

materially distinct job, mechanism, domain, or operating context
→ IMPORT AS CANONICAL CAPABILITY
```

Similarity of names alone is not enough to merge. Distinct decision responsibilities remain distinct.

## 3. Awesome OpenClaw Agents integration

`mergisi/awesome-openclaw-agents` is treated as an MIT-licensed capability source.

The source includes OpenClaw-specific `SOUL.md` templates and also runtime/configuration assets. We deliberately separate these:

### Canonicalized

- agent role/capability doctrine from `agents/**/SOUL.md`;
- source identity and provenance;
- useful operating rules that remain valid across targets.

### Kept adapter-specific

- OpenClaw registration syntax;
- OpenClaw gateway assumptions;
- Telegram/cron/provider integrations that are not guaranteed by the current runtime;
- model/provider config examples;
- OpenClaw-only memory/runtime conventions;
- deployment packaging that does not define the agent's strategic role.

This prevents a tool-specific implementation from becoming the agency architecture.

## 4. Import contract

Every community import is wrapped by this contract:

1. **Agency doctrine has priority.** `strategy/GENERAL-STRATEGY-DOCTRINE.md` governs purpose, authority, evidence, interaction, and termination.
2. **The user/runtime language wins.** Source defaults such as “always respond in English” are presentation suggestions, not immutable rules.
3. **Tools are capabilities, not assumptions.** A source may mention Telegram, cron, browser, sheets, shell, trading, or other integrations. The canonical agent may use only tools that actually exist and are authorized in the current runtime.
4. **Never fabricate access or execution.** If a required integration is absent, report the gap or produce a plan/artifact instead of claiming the action happened.
5. **Source cadences and numeric thresholds are contextual defaults.** They are not universal doctrine unless independently justified for the case.
6. **Higher-risk domains retain applicable safeguards.** Financial, legal, healthcare, security, employment, privacy, and regulated-domain work remains bounded by applicable policy, law, professional limits, and human authority.
7. **Evidence remains typed.** Facts, hypotheses, attributed intentions, predictions, and unknowns stay distinguishable.
8. **External templates do not gain decision authority.** Capability does not imply permission to commit resources, publish, transact, deploy, contact third parties, or accept risk.

## 5. Canonical identity and slugs

Imported novel capabilities use stable canonical slugs:

```text
openclaw-<source-id>
```

If the upstream source contains duplicate IDs across categories, the slug becomes:

```text
openclaw-<source-category>-<source-id>
```

The display name does not need to carry the OpenClaw brand. Provenance lives in metadata and the unified source registry.

Merged/aliased external agents retain no duplicate installable slug. Their external source ID points to the existing Agency canonical slug.

## 6. Division mapping

External categories are mapped into the existing Agency taxonomy rather than creating 24 parallel divisions.

Typical mapping:

| External category | Canonical Agency division |
|---|---|
| development | engineering / testing by role |
| devops | engineering / support / security by role |
| marketing | marketing / research by role |
| creative | design / marketing by role |
| business | sales / support / specialized by role |
| data | research / support / specialized by role |
| finance | finance |
| healthcare | healthcare |
| security | security |
| education | academic |
| productivity | project-management / support |
| ecommerce | sales / marketing / specialized |
| customer-success | support / sales |
| legal / compliance | support / security |
| automation / supply-chain / personal / SaaS / real-estate / freelance | closest existing division, otherwise specialized |

The import manifest records the actual resolution for every source agent.

## 7. Deduplication order

For each external source agent:

1. curated explicit alias to a known canonical agent;
2. exact canonical slug match;
3. unambiguous canonical suffix/name match;
4. otherwise import as a novel capability.

Ambiguous matches are not auto-merged. False consolidation is worse than a temporary duplicate because it can erase a real capability difference.

The source registry preserves enough provenance to review and merge further semantic overlaps later without losing source history.

## 8. One orchestration authority

External collections do not ship their own top-level orchestration into the canonical system.

All multi-agent work routes through:

- `strategy/GENERAL-STRATEGY-DOCTRINE.md` for material strategic choice;
- `strategy/nexus-strategy.md` for orchestration;
- `strategy/runbooks.json` for deployable scenario teams;
- the human decision owner for decisions that exceed delegated bounds.

Imported agents can appear in Runbooks once their role is justified. They do not autonomously assemble a shadow crew.

## 9. One target-conversion layer

A canonical agent is defined once and converted through the repository's supported targets.

OpenClaw is therefore one deployment target among the supported tools, not a separate source of strategic authority.

```text
canonical agent
→ antigravity
→ gemini-cli
→ opencode
→ cursor
→ aider
→ windsurf
→ openclaw
→ qwen
→ zcode
→ kimi
→ codex
→ osaurus
→ hermes
→ vibe
→ other registered targets
```

Tool-specific differences belong in converters/adapters, not in competing agent definitions.

## 10. Source synchronization

The OpenClaw community import is pinned to a source commit and regenerated deterministically.

A sync must report:

- source commit;
- declared `agents.json` count;
- discovered `SOUL.md` count;
- source-manifest/tree inconsistencies;
- aliases/merges;
- novel imports;
- missing/failed source files;
- removed upstream agents;
- canonical paths and slugs.

A source update never silently overwrites a native canonical agent.

## 11. Final rule

**One agency means one decision architecture, one canonical identity per capability, one orchestration system, and one set of tool adapters — not one repository copied into another without reconciliation.**

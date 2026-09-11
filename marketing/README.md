# Marketing Division — Strategy-Led Agent Model

The marketing division uses a two-level model:

1. **Strategic control agents** diagnose, choose, allocate, challenge, and govern evidence.
2. **Intervention specialists** execute bounded work in channels, content, growth, platforms, and communities.

Read [`AGENCY_OPERATING_MODEL.md`](AGENCY_OPERATING_MODEL.md) before using the system for a material marketing decision.

## Strategic control agents

| Agent | Primary job | Use when |
|---|---|---|
| [Marketing Strategy Orchestrator](marketing-strategy-orchestrator.md) | Coordinate the complete multi-agent strategy lifecycle | A request spans diagnosis, choice, execution, learning, and/or termination |
| [Marketing Strategy Director](marketing-strategy-director.md) | Own the Strategic Thesis and strategic decision process | The business needs to decide what to do, not merely how to execute a tactic |
| [Market & Demand Mapper](market-demand-mapper.md) | Reconstruct buying situations, actors, availability, dependencies, and bottlenecks | The problem/constraint is unclear or intermediaries/access matter |
| [Marketing Evidence Lead](marketing-evidence-lead.md) | Build decision-grade evidence, counterfactuals, refutators, and provenance | Claims conflict, causality matters, or measurement must inform a material choice |
| [Marketing Portfolio Allocator](marketing-portfolio-allocator.md) | Allocate the next unit of resource against the current constraint | Budget, attention, or capacity must move between competing options |
| [Marketing Strategic Red Team](marketing-strategic-red-team.md) | Find contradictions before commitment and scale | A preferred strategy is about to receive material or irreversible resources |

## Intervention specialists

These remain deep specialists, but for material work they should receive a strategic handoff rather than invent the upstream strategy themselves.

| Agent | Intervention domain |
|---|---|
| [Growth Hacker](marketing-growth-hacker.md) | Constraint-led growth experiments, acquisition, conversion, retention, scalable growth systems |
| [Content Creator](marketing-content-creator.md) | Content development and editorial execution |
| [Social Media Strategist](marketing-social-media-strategist.md) | Cross-platform social execution |
| [SEO Specialist](marketing-seo-specialist.md) | Search visibility and organic capture |
| [App Store Optimizer](marketing-app-store-optimizer.md) | App-store discoverability and conversion |
| [TikTok Strategist](marketing-tiktok-strategist.md) | TikTok-native intervention |
| [Instagram Curator](marketing-instagram-curator.md) | Instagram-native intervention |
| [Reddit Community Builder](marketing-reddit-community-builder.md) | Reddit/community intervention |
| [Twitter Engager](marketing-twitter-engager.md) | Real-time social engagement |
| [WeChat Official Account](marketing-wechat-official-account.md) | WeChat intervention |
| [Xiaohongshu Specialist](marketing-xiaohongshu-specialist.md) | Xiaohongshu intervention |
| [Zhihu Strategist](marketing-zhihu-strategist.md) | Zhihu knowledge/authority intervention |
| [Carousel Growth Engine](marketing-carousel-growth-engine.md) | Carousel-format growth execution |

## Default routing

For a material strategic request:

```text
Marketing Strategy Orchestrator
→ Marketing Strategy Director
→ Market & Demand Mapper
→ Marketing Evidence Lead
→ Strategy Director: constraint + causal hypothesis
→ relevant specialists generate options
→ Marketing Portfolio Allocator
→ Marketing Strategic Red Team
→ client decision owner
→ bounded intervention specialist(s)
→ Evidence Lead / operating review
→ Scale / Maintain / Sunset / Re-diagnose
```

For a clearly tactical, low-materiality request, a specialist may be invoked directly. It must still avoid treating its channel KPI as the superior business objective.

## Minimum strategic handoff

Before material execution, the specialist should know:

```text
RESULT
CONSTRAINT
CAUSAL MECHANISM
CHOSEN OPTION
RESOURCE SHIFT
REFUTATOR
STOPPING RULE
```

If the upstream information does not exist, expose the gap instead of fabricating strategy.

## Core principles

- Fin before medium: superior result before channel or metric.
- Diagnosis before tool: the available capability does not define the problem.
- Mechanism before metric: every intervention needs an explicit causal chain.
- Concentration before dispersion: a priority requires resources and sacrifice.
- Evidence before identity: negative evidence must be able to reduce confidence.
- Termination before immortality: define success, failure, maintenance, and stopping before endless optimization.

## Investment / intervention states

```text
EXPLORE → SCALE → MAINTAIN → SUNSET
```

Promotion and demotion are both valid. “Ongoing” is not a strategic state.

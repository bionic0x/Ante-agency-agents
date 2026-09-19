# NEXUS: multi-level, multi-vector, multi-factor, multi-provider

Three of these four dimensions were already in the engine. The fourth did not
exist. That asymmetry is what this change addresses, and it explains why the
work is smaller and more useful than "add five providers" suggests.

| Dimension | State before | State now |
|---|---|---|
| Multi-level | `task.level` validated against the five canonical planes in `contracts.json` | Unchanged — it was already a contract |
| Multi-vector | `task.vector` accepted as free text; nothing checked it | Closed registry in `strategy/vectors.json`, enforced by the validator and the router |
| Multi-factor | `nexus-options.py` compares factors with admissibility, dominance and per-factor evidence status, no weighted score | Unchanged — and reused by the router |
| Multi-provider | Nothing. Zero provider or model references in 430 lines of engine | Closed provider registry + router, plus one bounded Anthropic/Claude Code adapter and pilot |

The conversion layer was never the gap: 492 profiles already convert to 16
destinations, including Gemini CLI, Kimi and Codex. Conversion is not execution.
The gap was that NEXUS had no notion of an execution target at all.

## The vector registry

`level` answers *which plane a task belongs to*. `vector` answers *how the task
contributes*, and until now any string passed. A vector now declares its
contribution kind — `sequential` or `cumulative`, the distinction the framework
draws between a chain that breaks and an accumulation that gets absorbed — plus
the domain it acts in, the evidence that would show it, and its characteristic
failure.

| Vector | Kind | Characteristic failure |
|---|---|---|
| `causal` | sequential | a necessary dependency is missing, so no later step is enabled |
| `evidence` | cumulative | findings accumulate without changing the decisive uncertainty |
| `assurance` | sequential | a technical PASS is promoted into authority it does not carry |
| `adversarial` | sequential | the plan only works while the other party stays passive |
| `legitimacy` | cumulative | the method wins the objective and destroys the cooperation that sustains it |
| `resource` | cumulative | reserve is spent on ordinary work and counted as available |
| `termination` | sequential | the objective is reached and the result decays for lack of an owner |

Coverage rules say which vectors an instance must carry. Running them against
the shipped example found a real gap on the first try: `strategic-decision`
declares a budget and acceptance predicates but carries no `resource` and no
`termination` vector. A missing vector is reported as a gap, never treated as
satisfied.

## The provider registry ships zero models, on purpose

`strategy/providers.json` declares five providers — Anthropic, OpenAI, Google,
Moonshot, xAI — and **no verified models**. Its status is `MODELS_NOT_OBSERVED`.

This is not an omission. A model catalog written from memory is stale the week it
merges, and an unverified model id is a claim this repository cannot check. The
registry therefore describes what a task may *require* — reasoning depth, context
class, modality, tool use, determinism — and a model becomes selectable only when
an observation supplies its id, host, version, declared limits, evidence
reference and `valid_until`. Expired or incomplete observations are named and
dropped.

That is the contract `agent-capabilities.py` already applies to tool
capabilities, and the reason `host-trials.json` ships empty rather than
plausible. Costs and context windows in an observation are the operator's own
declared figures, used for admissibility; they are never presented as a vendor's
current pricing.

## Routing refuses to rank

`nexus-routing.py route` answers one question per task: given its plane, its
vector and its declared requirements, which observed targets are admissible?

- **Admissibility first.** A target that misses a requirement is excluded with the
  specific reason, never scored lower.
- **No composite score, no winner.** The output is the undominated set and the
  dominance edges, each labelled `measured: false` because declared cost and
  context are not measured performance. Where a genuine trade-off exists — cheaper
  but smaller against pricier but roomier — the router returns both and picks
  neither.
- **UNKNOWN survives.** No observed target returns `NO_OBSERVED_TARGET`; none
  admissible returns `NO_ADMISSIBLE_TARGET`. Neither falls back to a guess.
- **Provider diversity is not a benefit in itself.** It is justified by a
  requirement no single observed target satisfies, or by a measured difference
  under the evaluation protocol. Otherwise it is cost and maintenance with no
  evidenced return.

One defect found and fixed during construction: the first cut compared a task's
`cost_limit` — a budget allowance in the instance's own unit — against a price
per 1k output tokens, which excluded every target for a unit mismatch. The
ceiling now applies only when a task states one in the observation's own unit.

## One adapter, without collapsing the control planes

Anthropic is now the one implemented execution adapter. The other four provider
entries remain `unimplemented`, and the registry still ships **zero model
observations**. Implementing a provider is not observing a model.

`nexus-anthropic.py observe` makes one real Claude Code call and records the
model/session/host fields the stream actually exposes. It does not manufacture a
price from a cached turn: per-1k costs stay `UNKNOWN` until the operator supplies
them, so the existing router continues to reject an incomplete observation.

`nexus-pilot.py` keeps the three authorities separate. The instance engine says
which task is ready; the router says which observed target is admissible; an
expiring operator record names the instance, task set, provider and budget unit.
A `step` performs at most one live model call, with a temporary project profile
whose host-resolved tools must be exactly `[Read]`, then stops in
`AWAITING_ACCEPTANCE`. Host `COMPLETED` is evidence, not a NEXUS acceptance.
Only a separate `accept`/reject decision appends the engine's `finish` event and
unblocks a dependency. After all tasks succeed the pilot stops at
`AWAITING_TERMINATION`; it never closes the instance by itself.

This is deliberately not general multi-provider execution. It proves that the
provider abstraction can carry one real adapter without allowing that adapter to
choose the task, target, authority or acceptance result. Quality claims remain the
job of the matched measurement protocol, not the execution record.

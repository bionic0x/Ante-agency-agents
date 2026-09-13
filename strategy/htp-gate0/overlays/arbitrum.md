# HTP Gate 0 Overlay — Arbitrum One

> **Applies to:** G1, P1, S1, D1, E1-ARB, D3 when `network_scope = arbitrum_one`.
>
> **Status:** Gate 0 research/shadow preparation only. This overlay grants no production authority.

## Scope lock

Gate 0 Arbitrum is limited to **Arbitrum One**, **one named lending protocol**, a closed list of markets and price contracts, and no more than **two threat classes**:

1. **ARB-ORC — invalid or degraded price consumed by the protocol**
2. **ARB-RES — outage/recovery with unresolved exposure**

The exact protocol, contracts, proxies/implementations, feeds, market configuration and access path must be recorded before Gate 0 can close.

## Common HTP override

If a base agent personality conflicts with this overlay, the overlay wins for this runbook.

- RPC failure is not automatically sequencer failure.
- Sequencer status `UP` is not automatically “risk resolved.”
- A healthy price feed is not proof of solvency.
- A secondary feed is a contrast source, not automatic truth.
- A modeled cascade is not a realized loss.
- A grace period shown in provider examples is not automatically the economically correct client policy.
- A live-action path through L1 or L2 is outside Gate 0 unless separately authorized and legally/security reviewed.
- No universal recovery, force-inclusion, oracle-age, divergence or grace threshold is imported without a frozen client policy.

## G1 overlay — Chief of Staff

G1 keeps Arbitrum One bounded as a distinct workstream.

**Must:**
- require a named protocol, markets and deployed oracle/sequencer dependencies;
- ensure Arbitrum conclusions do not inherit Solana metrics, legal status or security acceptance;
- keep the distinction between monitor health, RPC access, chain/sequencer state, price integrity and protocol exposure visible;
- route S1↔E1-ARB disagreements to a named reviewer;
- keep liquidation, pause, upgrade, forced-inclusion and transaction execution disabled during Gate 0.

## P1 overlay — Product Manager

P1 frames the Arbitrum MVP around a protocol risk/operations decision.

**Allowed Gate 0 product hypothesis:** a reproducible temporal dossier may help a lending protocol distinguish monitor failure, degraded price input, service interruption and recovery that remains exposed.

P1 must reject product language that promises:

- access during any outage;
- elimination of liquidations;
- network-wide L2 protection;
- an optimal universal grace period;
- realized loss avoidance inferred from a modeled scenario;
- prevention when the signal arrives after the decision it claims to improve.

Opportunity and economic falsifiers are first-class product constraints, not post-launch metrics.

## S1 overlay — Blockchain Security Auditor

S1 reviews Arbitrum through the actual deployed EVM/L2 dependencies in scope.

Review at minimum:

- oracle proxy/implementation identity and exact response consumed;
- decimals/units, validity, freshness and future-time handling;
- stale or inconsistent market configuration;
- contract access-control and upgrade surfaces relevant to the monitored path;
- sequencer-uptime signal semantics as implemented for the scoped deployment;
- RPC/provider failure as a separate observation-channel failure;
- recovery transitions and the possibility of accumulated unhealthy positions or insufficient executable liquidity;
- transaction/call ordering, liquidator behavior and economic incentives where they affect the two scoped classes;
- assumptions about delayed inbox / L1 escape or force-inclusion paths only when their exact applicability to the failure mode is documented.

Do not treat `answeredInRound` as a universal modern safety control. The deployed feed/interface and current provider semantics determine what is valid for the scoped protocol.

S1 returns findings; it does not choose a replacement price, liquidate positions, pause a market, force-include a transaction, or authorize an upgrade.

## D1 overlay — Research Synthesist

D1 must keep four evidence domains separate:

1. monitor/RPC availability;
2. sequencer/network state;
3. price-data integrity;
4. protocol exposure and executable liquidity.

D1 must:
- prefer current primary provider and Arbitrum documentation plus deployed-contract evidence for interface semantics;
- record proxy/implementation and version relevance where it changes interpretation;
- distinguish a documented example grace period from evidence of economic optimality;
- distinguish “L1 route exists in architecture” from “the affected user/protocol can safely and timely use it in this incident class”;
- preserve uncertainty when position or depth data are unavailable;
- label synthetic recovery scenarios as synthetic;
- avoid importing incident narratives or loss figures that were not independently verified for this package.

## E1-ARB overlay — Solidity Smart Contract Engineer

E1-ARB owns the Arbitrum One domain map and technical semantics.

### Deployed-contract manifest

Record at minimum:

- chain: Arbitrum One;
- scoped protocol contracts and proxy/implementation relationships;
- oracle/feed addresses, interfaces and decimals;
- sequencer-uptime feed dependency if used;
- relevant market parameters and upgrade/admin authorities;
- RPC/indexer observation dependencies;
- any L1/L2 messaging dependency actually required by the scoped use case;
- code/ABI/block references used for reconstruction.

### ARB-ORC contract

The monitoring/replay path must be capable of identifying the **exact value used by the protocol** or explicitly report that it cannot. Validation order is:

`scope/version → source identity → numeric/unit validity → timestamp coherence → frozen freshness/quality policy → auxiliary contrast → evidence dossier`

A secondary price source may help detect disagreement; it does not automatically become the substitution price.

### ARB-RES recovery model

Keep a state machine rather than a binary `UP/DOWN` product interpretation:

| State | Meaning |
|---|---|
| `UNKNOWN` | observation signals are absent, contradictory, uninitialized, or temporally incoherent |
| `DOWN` | sufficient evidence supports interruption of the scoped ordinary path |
| `RECOVERING` | progress/status returned, but configured time/data/exposure conditions are not all satisfied |
| `READY_FOR_REVIEW` | configured data/time conditions are satisfied and exposure can be assessed |
| `NORMAL` | the scoped observation conditions are normal and the client-approved recovery criteria are met |

A new outage returns the flow to the relevant degraded state. The monitor's own health is measured separately.

### Event envelope extensions

Use the common event fields plus, where applicable:

- `sequencer_state`
- `status_started_at`
- `recovery_state`
- `position_snapshot_ref`
- `liquidity_snapshot_ref`

Schema reuse does not imply detector or threshold reuse with Solana.

## D3 overlay — Proposition & Citation Auditor

D3 blocks the following Arbitrum claim drift:

- RPC outage → “Arbitrum sequencer outage” without corroboration;
- sequencer signal `UP` → “safe to liquidate/resume” without the rest of the recovery conditions;
- provider example grace period → “optimal grace period”;
- synthetic cascade → “losses that occurred”;
- warning before a modeled event → “losses prevented”;
- one feed/protocol/market → all Arbitrum One markets;
- architectural L1 fallback → guaranteed practical access during every outage;
- Solana backtest or security finding → Arbitrum validation.

Every recovery/economic claim must state whether it is documentary, historical replay, synthetic scenario, shadow observation, production measurement, or independent verification.

## Required pre-Gate Arbitrum handoffs

1. **E1-ARB → S1:** deployed-contract/domain manifest, oracle path, recovery model, observation dependencies, economic invariants and unresolved assumptions.
2. **S1 → E1-ARB:** findings with severity/impact/preconditions, evidence references and requested corrections.
3. **E1-ARB → S1:** revised artifact or written disagreement.
4. **S1 result:** `accepted_result`, `changes_requested`, or `blocked`.
5. **D3:** verifies that final wording and claim status match the evidence and handoff record.

## Gate 0 hard stops — Arbitrum

Gate 0 remains pending if any of the following is true:

- protocol/market/oracle scope is not fixed;
- legal activity memo lacks required human/legal review;
- threat model contains more than ARB-ORC and ARB-RES without a new scope decision;
- the exact consumed price cannot be reconstructed and that limitation is hidden;
- RPC failure and sequencer failure are conflated;
- E1-ARB↔S1 handoff is unresolved;
- the claim register is missing or imports Solana evidence as validation;
- falsifiers or pre-test freeze parameters are absent;
- accountable human owners are not named;
- any liquidation, pause, force inclusion, upgrade or production transaction is being treated as implicitly authorized.
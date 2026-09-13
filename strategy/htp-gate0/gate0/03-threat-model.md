# Gate 0 Artifact 03 — Dual-Network Threat Model

> **Leads:** S1 Blockchain Security Auditor + D1 Research Synthesist  
> **Chain review:** E1-SOL / E1-ARB  
> **Claim review:** D3 Proposition & Citation Auditor  
> **Status:** DRAFT — protocol manifests pending  
> **Constraint:** ≤2 threat classes per network

## Threat-model rule

The unit of analysis is not “Solana” or “Arbitrum” in the abstract. Before benchmark construction, each workstream must identify one protocol, the relevant programs/contracts, markets, feeds/adapters and versions. Anything outside that manifest is out of the evaluated population unless explicitly added by a new scope decision.

This threat model is defensive. It supports detection/replay/shadow preparation and remediation design; it does not authorize live exploitation, transaction submission, liquidation, pause, forced inclusion, or public attribution.

---

# A. Solana

## A1. Scope manifest — required before close

```yaml
solana_scope:
  protocol: PENDING
  program_ids: []
  upgrade_authorities: []
  markets: []
  assets: []
  oracle_feeds: []
  oracle_adapter_versions: []
  token_programs: []
  token_2022_extensions_in_scope: []
  rpc_indexer_sources: []
  observation_window: PENDING
  dataset_ref: PENDING
```

## A2. Trust boundaries

| Boundary | Trusted property that must be proved | Failure consequence |
|---|---|---|
| Chain observation → event reconstruction | correct tx/instruction/state provenance and clocks | false sequence or missing state |
| Program/account input → protocol interpretation | program ID, account address, runtime owner, signer/writable/type relationships | account substitution or false state attribution |
| Oracle feed → valuation evidence | feed identity, exact value consumed, verification/quality, time semantics, units | degraded/invalid valuation misclassified |
| Token program → economic accounting | Token vs Token-2022 identity and relevant extension semantics | gross/net balance error or hidden authority behavior |
| CPI boundary → state transition | callee identity and propagated privileges | false authority model / missed mutation |
| Detection → client decision | delivery timing and recipient authority | ex-post signal marketed as prevention |

## A3. SOL-ORD — observable adverse ordering

### Mechanism under investigation

A sequence of swaps/instructions is associated with worse execution for the scoped client flow than a defensible comparison path. This is a **harm mechanism hypothesis**, not automatic proof of adversarial intent or actor provenance.

### Evidence required

At minimum, where reconstructible:

- transaction signatures and instruction order;
- slot/block context and finality status;
- route and pool identities;
- pool state/liquidity before and after relevant operations;
- trade sizes, fees and received amounts;
- available market/reference information at the relevant time;
- observation quality and missing state;
- evidence specifically supporting any claimed Jito/bundle provenance rather than inferring it from shape alone.

### Required labels

Keep three propositions separate:

| Label | Question |
|---|---|
| `pattern_candidate` | Does the sequence match the defined structural pattern? |
| `harm_supported` | Does evidence support incremental deterioration relative to the frozen comparison? |
| `provenance_supported` | Is the claimed execution/order-flow provenance actually evidenced? |

None implies the others automatically.

### Alternative explanations to preserve

- ordinary arbitrage;
- external market movement;
- shallow liquidity;
- client/router path inefficiency;
- omitted transaction/state observations;
- unrelated trades that create similar local geometry;
- comparison model error.

### Critical dependency

A defensible reconstruction and counterfactual/reference execution. If that cannot be built, the system may report a structural pattern but cannot upgrade the harm claim.

### Timing limit

A signal built from a transaction after it is included cannot protect that same transaction. A preventive product claim therefore requires a distinct prospective channel, measured evidence-availability clocks and a later shadow/pilot test.

### Failure modes for the detector

- hindsight leakage from later state;
- classifying legitimate arbitrage as hostile;
- attributing intent/provenance without evidence;
- using one market's slippage/impact threshold universally;
- denominator defined only from discovered alerts rather than the eligible population;
- silently excluding non-reconstructible cases.

## A4. SOL-ORC — degraded valuation input

### Mechanism under investigation

A protocol risk calculation consumes a price/update whose identity, verification, age, uncertainty/quality, scale or temporal coherence fails the market policy that was frozen for the evaluation.

The condition may harm borrowers, liquidity providers, or protocol solvency. A degraded input does **not** by itself prove an incorrect liquidation or realized loss.

### Evidence required

- the exact price/update consumed or a verifiable proof of it;
- feed identity and provider/adapter version;
- market configuration effective at the event;
- price publication/update time and, separately, on-chain inclusion/posted slot where applicable;
- verification/quality/confidence fields applicable to that provider/version;
- units/exponent/decimals;
- state of the affected position before the operation;
- instruction sequence and relevant CPI path;
- policy thresholds/version used in the classification.

### Provider-specific discipline

- **Pyth:** keep publication/update time distinct from the on-chain slot/observation clock; evaluate the actual feed/SDK semantics in scope.
- **Switchboard:** do not assume one universal account/API shape. Until the scoped deployment and adapter version are fixed and supported, the result is `UNSUPPORTED`, not healthy.

### Alternative explanations / limitations

- monitor read differs from value actually consumed by the program;
- provider update is valid but the market policy is wrong or stale;
- numeric/unit normalization error exists in the replay rather than the protocol;
- a liquidation is economically correct despite a degraded auxiliary signal;
- a price disagreement reflects timing rather than manipulation.

### Out of Solana Gate 0 threat scope

- bridge security;
- listing/governance manipulation;
- autonomous flash-loan detection as a third class;
- generic protocol accounting defects not necessary to evaluate SOL-ORD/SOL-ORC;
- identity/intent attribution beyond supported evidence.

---

# B. Arbitrum One

## B1. Scope manifest — required before close

```yaml
arbitrum_scope:
  network: arbitrum_one
  protocol: PENDING
  protocol_entity: PENDING
  markets: []
  contracts: []
  proxy_implementation_pairs: []
  oracle_feeds: []
  oracle_interfaces_versions: []
  sequencer_uptime_feed: PENDING_IF_USED
  rpc_indexer_sources: []
  market_recovery_policy_version: PENDING
  observation_window: PENDING
  dataset_ref: PENDING
```

## B2. Trust boundaries

| Boundary | Trusted property that must be proved | Failure consequence |
|---|---|---|
| RPC/indexer → monitor | observation channel is live and correctly identifies block/time | RPC outage misclassified as network outage |
| Sequencer-status feed → recovery state | correct feed/contract and status/time semantics | false DOWN/UP transition |
| Oracle proxy/implementation → valuation | correct address/interface/units/value/timestamp | invalid/degraded price hidden or fabricated |
| Chain state → protocol exposure | positions, configuration and executable liquidity correspond to the same relevant time | synthetic cascade presented as measured exposure |
| Recovery signal → policy advice | configured grace/data/exposure criteria are satisfied | “UP” promoted to “safe” too early |
| Detection → client action | signal delivered before the target decision and to an authorized actor | ex-post reconstruction marketed as prevention |

## B3. ARB-ORC — invalid or degraded price consumed

### Mechanism under investigation

The scoped lending protocol consumes a value that is not fit under its frozen policy because of source identity, invalid numeric/scale semantics, timestamp inconsistency, staleness, unsupported interface/implementation or unexplained disagreement requiring review.

### Evidence required

- exact feed/aggregator/proxy and implementation where relevant;
- exact response/value used;
- decimals/units and conversion logic;
- block and transaction context;
- market configuration effective at the event;
- protocol operation that consumed the value;
- adapter/policy version;
- auxiliary/reference feeds with their own timestamps and dependencies.

### Validation order

1. resolve scope and interface/version;
2. verify source identity;
3. validate numeric structure, units/decimals and non-future time;
4. evaluate frozen freshness/quality policy;
5. compare auxiliary signals only as contrast evidence;
6. produce the dossier and uncertainty state.

A secondary feed is not automatic ground truth and the HTP layer does not choose a substitute price for the client.

### Specific control caution

Do not rely on `answeredInRound` as a universal contemporary completeness control. The exact deployed interface/provider semantics in scope must determine the valid checks.

## B4. ARB-RES — outage/recovery with unresolved exposure

### Mechanism under investigation

The ordinary L2 path experiences an interruption or degradation; when progress/status returns, positions, prices, liquidity, timing or client recovery conditions may still make immediate resumption risky.

This is a hypothesis about **recovery exposure**, not a presumption that every outage creates a liquidation cascade or that delaying activity is always beneficial.

### Inputs

- sequencer/status evidence when relevant;
- independent evidence of chain progress and monitor health;
- RPC/provider health separately;
- price references available at the relevant times;
- position snapshot before/during recovery where authorized and reliable;
- executable liquidity/depth snapshot;
- client market configuration;
- client-approved recovery/grace policy;
- timestamps for detection, evidence availability and delivery.

### Required separations

Do not collapse:

- RPC/provider outage;
- sequencer/L2 ordinary-path interruption;
- return of chain progress;
- configured grace period;
- price-data normalization;
- position repair;
- executable liquidity;
- final client decision.

### Recovery states

| State | Minimum interpretation |
|---|---|
| `UNKNOWN` | signals absent, contradictory, uninitialized or temporally incoherent |
| `DOWN` | sufficient evidence supports the scoped interruption |
| `RECOVERING` | progress/status returned but required configured conditions remain unmet |
| `READY_FOR_REVIEW` | data/time conditions are satisfied and exposure can be assessed |
| `NORMAL` | client-approved normality/recovery criteria are met for the scoped observation |

One status signal cannot by itself prove all downstream conditions.

### Competing economic scenarios

Evaluation must include at least:

- market continues falling during recovery;
- market reverses;
- users repair positions;
- liquidity is inadequate;
- liquidations cluster;
- a longer delay reduces immediate liquidation pressure but increases insolvency/bad-debt exposure.

A protective control is judged on net client objective, not a single count of avoided immediate liquidations.

### L1 / forced-path caution

The architecture may expose delayed/L1 paths under certain conditions. Gate 0 does not assume that such a path is available, timely, safe or authorized for every affected user/protocol or outage mode. Applicability must be established for the exact scenario before it appears in a product claim.

---

# C. Common adversarial review questions

For each network and threat class S1+D1 must answer:

1. What observation would distinguish the threat hypothesis from its strongest alternative explanation?
2. What data would be required but is currently unavailable?
3. Can an attacker/user/provider change the observation itself or only the underlying state?
4. Which assumption, if false, invalidates most of the detector?
5. Which state is non-evaluable and how is it represented?
6. Is the proposed evidence available early enough for the product claim?
7. What does the detector still **not** prove after a positive result?
8. Which chain-specific dependency could substitute or regenerate after failure?
9. What is the economic failure mode of the proposed mitigation itself?
10. What explicit observation would force the threat model to be revised?

# D. Gate 0 threat-model acceptance checklist

### Solana
- [ ] named protocol/program/market/feed manifest exists;
- [ ] no more than SOL-ORD + SOL-ORC in MVP scope;
- [ ] provider/adapter versions are fixed or explicitly `UNSUPPORTED`;
- [ ] transaction/slot/publication/observation clocks are distinct;
- [ ] ordering alternatives and non-evaluable cases are represented;
- [ ] E1-SOL→S1 handoff completed or unresolved items block the Gate.

### Arbitrum One
- [ ] named protocol/market/contract/feed manifest exists;
- [ ] no more than ARB-ORC + ARB-RES in MVP scope;
- [ ] RPC outage and sequencer/network state are distinct;
- [ ] consumed-price reconstruction path is specified;
- [ ] recovery uses multiple configured conditions rather than binary `UP` alone;
- [ ] E1-ARB→S1 handoff completed or unresolved items block the Gate.

### Common
- [ ] every material threat assertion has evidence or is labeled hypothesis;
- [ ] no live exploitation is required to validate Gate 0;
- [ ] no chain's evidence upgrades the other chain's status;
- [ ] D3 has reviewed the final wording for evidence-status inflation.

Until these conditions are met: **Gate 0 pending**.
# Gate 0 Artifact 01 — Object / Non-Object

> **Leads:** G1 Chief of Staff + P1 Product Manager  
> **Review:** D3 Proposition & Citation Auditor  
> **Status:** DRAFT — Gate 0 pending  
> **Authority:** named human owner pending

## Package rule

This is one Gate 0 artifact with two independent network scopes. Shared product vocabulary does not allow evidence, metrics, approvals, thresholds or legal conclusions to transfer between Solana and Arbitrum One without an explicit transfer argument.

---

## A. Solana

### Object

Determine whether HTP can, for **one bounded Solana protocol and enumerated markets/programs/feeds**:

1. identify reproducibly evidence consistent with **SOL-ORD — observable adverse ordering** and **SOL-ORC — degraded valuation input**;
2. distinguish supported findings from `UNKNOWN`, `UNSUPPORTED` and alternative explanations;
3. establish when the relevant evidence became available; and
4. test whether a resulting dossier could reach a protocol risk decision-maker early enough to support a later, separately authorized loss-reduction pilot.

The product at Gate 0 is an **evidence and decision-support hypothesis**, not an execution engine.

### Intended buyer and beneficiaries

- **Candidate buyer:** risk/operations team of a protocol not yet named.
- **Potential beneficiaries:** users exposed to execution or valuation harm and the protocol's risk function.
- **Open issue:** a real contractual buyer has not yet been identified. If the selected customer exposes only one of the two threat surfaces, scope reduces to that class rather than inventing a second use case.

### Non-object

HTP is **not**, in this Gate 0 scope:

- coverage of all Solana;
- a universal MEV detector;
- a system that classifies every arbitrage as hostile;
- a competitor for extraction/order-flow revenue;
- a product promising “MEV eliminated”;
- an actor-attribution engine based on transaction proximity, profit or reversal alone;
- a liquidator or liquidation blocker;
- a transaction signer/sender;
- a custodian;
- an authority to modify programs or market parameters;
- a mechanism that counts alerts as losses or euros avoided.

### Operating boundary

Allowed preparation:

- historical/on-chain research;
- frozen replay where reconstruction is sufficient;
- isolated/local simulation;
- adapter and policy specification;
- evidence-schema work;
- future shadow-plan design.

Not authorized by Gate 0:

- production writes;
- signing or submitting transactions;
- custody;
- live pause/market control;
- program upgrades;
- third-party exploitation;
- public attribution of alleged attackers.

### Success question

Not “can we emit an alert?” but:

> Can we produce a reproducible, correctly scoped and timely evidence dossier for the selected class, with known missingness and falsifiers, that a real risk team could later evaluate without granting HTP execution authority?

---

## B. Arbitrum One

### Object

Determine whether HTP can, for **one bounded Arbitrum One lending protocol and a closed list of markets/oracle contracts**:

1. reconstruct when the protocol's price information or operating conditions ceased to support a trustworthy risk decision;
2. distinguish **ARB-ORC — invalid/degraded price consumed** from **ARB-RES — outage/recovery with unresolved exposure**;
3. separate observation-channel failure, sequencer/network state, price-data integrity, and protocol exposure; and
4. measure when evidence would have been available to a protocol risk/operations decision-maker during both failure and recovery.

### Intended buyer and beneficiaries

- **Candidate buyer:** risk/operations team of a lending protocol not yet named.
- **Potential beneficiaries:** borrowers and liquidity providers.
- **Constraint:** their interests can diverge. A delay that protects one position can increase bad-debt or liquidity costs elsewhere, so “fewer immediate liquidations” is not the final economic objective.

### Non-object

HTP is **not**, in this Gate 0 scope:

- protection for every L2;
- a guarantee of access during an outage;
- a guarantee of zero liquidations;
- an RPC provider;
- a sequencer operator;
- a liquidator;
- a forced-inclusion transaction operator;
- a contract pauser/upgrader;
- a system that changes client contracts;
- a system that presents a synthetic cascade as realized loss;
- a source of a universal or “optimal” grace period.

### Operating boundary

Allowed preparation:

- historical event reconstruction;
- contract/feed/interface mapping;
- replay/fork analysis where inputs are sufficient;
- clearly labeled synthetic recovery scenarios;
- shadow timing design;
- evidence and recovery-state specification.

Not authorized by Gate 0:

- liquidations;
- pauses;
- upgrades;
- force inclusion;
- production transaction submission;
- custody;
- direct borrower communication;
- regulator reporting;
- public incident/actor attribution.

### Success question

> Can we produce a reproducible temporal dossier that distinguishes monitor/RPC failure, degraded price, service interruption and recovery that remains exposed — without treating any one signal as permission to resume protocol action?

---

## Cross-network constraints

The following may be shared:

- artifact format;
- evidence-status vocabulary;
- claim-register schema;
- higher-level distinction between observation, detection, policy and execution;
- review/handoff mechanics.

The following remain independent:

- detector logic;
- performance;
- thresholds;
- protocol/feed adapters;
- economic effect;
- security review outcome;
- legal classification;
- Gate approval.

## Exit criteria for Artifact 01

This artifact is ready for Gate review only when:

- [ ] one candidate protocol is named for Solana;
- [ ] one candidate protocol is named for Arbitrum One;
- [ ] buyer/risk-decision owner is identified or explicitly marked unavailable with a scope consequence;
- [ ] non-goals are accepted by the named human product/governance owner;
- [ ] no prohibited execution capability has entered the Gate 0 scope;
- [ ] D3 confirms that object language does not claim evidence that belongs to later artifacts or later stages.

Until then: **Gate 0 pending**.
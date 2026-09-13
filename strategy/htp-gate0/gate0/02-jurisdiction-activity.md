# Gate 0 Artifact 02 — Jurisdiction & Activity Memo

> **Drafting/review seat:** G2 Legal Compliance Checker  
> **Routing:** G1 Chief of Staff  
> **Citation/scope audit:** D3 Proposition & Citation Auditor  
> **Status:** ISSUE-SPOTTING DRAFT — not a signed legal opinion  
> **Working jurisdiction assumption:** Spain / European Union only for issue identification; entity domicile and service footprint remain to be established

## Purpose and limitation

This memo identifies facts and legal questions that must be resolved before a live HTP service is authorized. It does **not** conclude that HTP is or is not a CASP, an investment service, a person professionally arranging/executing crypto-asset transactions, a market-abuse monitor, or any other regulated category merely from the proposed technical architecture.

The user's residence in Spain does not establish the domicile, establishment or regulatory perimeter of a future HTP entity. A real review must fix at least:

- operating entity and establishment;
- contracting entity and client jurisdiction;
- users/persons affected;
- assets and instruments covered;
- exact service description;
- data sources and personal-data exposure;
- whether HTP only observes, recommends, communicates, routes, signs, submits, pauses, liquidates, holds assets/keys, or performs another function;
- who makes and executes the client's risk decision.

## EU / MiCA issue map

The Gate 0 source package identifies the EU Markets in Crypto-Assets Regulation (MiCA), including its market-abuse regime and obligations that can apply to persons professionally arranging or executing transactions in crypto-assets. Those provisions are **questions for classification**, not proof that a read-only analytics product falls within them.

A competent reviewer must verify the law and implementing/regulatory material current at the time of service, plus any other applicable regimes. This memo does not claim regulatory completeness.

Primary legal reference carried forward from the source package:

- Regulation (EU) 2023/1114 (MiCA): https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng

## Common activity matrix

| Proposed activity | Facts that must be fixed | Gate 0 legal question | Gate 0 status |
|---|---|---|---|
| Historical replay of public/on-chain data | source, terms/licence, retention, enrichment, personal-data linkage | permitted acquisition/use/retention and contractual restrictions | PENDING |
| Risk alert to protocol team | recipient, decision owner, content, latency, client data used | contractual duty, liability, regulatory characterization, records | PENDING |
| Recommendation of parameter/route/recovery condition | level of personalization, determinism, integration into client workflow | whether advice/recommendation changes service classification or duty | PENDING |
| Automated policy output | whether output is advisory or directly action-enabling | authority, liability and regulatory consequences | OUT OF LIVE SCOPE UNTIL REVIEWED |
| Signing or transaction submission | signer, keys, custody/control, transaction type | new regulated/contractual/security analysis | EXCLUDED FROM GATE 0 |
| Custody/key control | asset/key/control model | custody and operational perimeter | EXCLUDED FROM GATE 0 |
| Pause/liquidation/force inclusion/program or contract change | exact authority and execution path | material new activity and liability analysis | EXCLUDED FROM GATE 0 |
| Suspicion/incident/actor report | evidentiary threshold, recipient, legal basis/obligation | defamation/confidentiality/reporting/market-abuse procedure | PENDING; NO PUBLIC ATTRIBUTION |
| Borrower/user communication | personal data, contact source, message purpose | privacy/e-communications/contractual authority | NOT AUTHORIZED BY THIS MEMO |

## Data and privacy questions

Before live service, identify:

- whether wallet addresses, contact data, account/position data or enriched identities constitute personal data in the actual context;
- controller/processor roles and contractual allocation;
- legal basis, purpose limitation, minimization and retention;
- access controls and audit trail;
- international transfers and vendor/subprocessor footprint;
- data-subject rights process where applicable;
- incident/breach responsibilities.

No claim is made here that on-chain data is automatically non-personal or automatically personal in every context; classification depends on the real processing and identifiability context.

---

## A. Solana-specific activity questions

### Current Gate 0 technical posture

The Solana charter is limited to historical/replay/simulation preparation and later shadow design. It excludes custody, signing, transaction submission and program changes.

### Facts to establish

| Solana fact | Why it matters |
|---|---|
| Named protocol, legal entity and markets | identifies the client, service object and affected users |
| Program IDs and upgrade/admin authorities | separates observation from any possible control relationship |
| Whether HTP receives private order flow or only public chain/feed data | affects confidentiality, contractual and potential market-abuse analysis |
| Whether HTP recommends a transaction route or market parameter | may move beyond passive analytics |
| Whether alerts identify suspected extractors/attackers | raises evidence, confidentiality and attribution issues |
| Whether HTP ever receives signing authority, PDA/admin capability, API key or operational credential | changes the technical and potentially regulatory activity perimeter |
| Whether positions/user identities are enriched off-chain | privacy and client-data obligations |

### Solana legal hard stop

Any future addition of:

- private order-flow handling;
- signing/submission;
- custody/key control;
- program/admin authority;
- autonomous transaction routing;
- direct user intervention;

requires a fresh activity analysis before implementation or pilot authorization.

No absence-of-custody statement is treated as an automatic legal exemption.

---

## B. Arbitrum One-specific activity questions

### Current Gate 0 technical posture

The Arbitrum charter is limited to historical reconstruction, clearly labeled simulation and shadow-plan preparation. It excludes liquidation, pause, upgrade, force inclusion and production transaction execution.

### Facts to establish

| Arbitrum One fact | Why it matters |
|---|---|
| Named lending protocol, contracting entity and markets | fixes client/service scope |
| External monitor vs embedded client component | affects control, responsibility and technical integration |
| Access to user positions or borrower contact information | affects data/privacy and contractual permissions |
| Whether HTP merely reports sequencer/oracle state or recommends suspension/recovery | separates observation from risk-policy advice |
| Whether a client policy automatically consumes the HTP output | affects reliance, control and liability analysis |
| Any future L1/L2 transaction path, forced-inclusion workflow or liquidation function | material activity change requiring separate review |
| Incident/borrower communications | requires defined authority, confidentiality and data basis |

### Arbitrum legal hard stop

A technical fact such as “the service runs on or monitors an L2” does not determine legal category. Likewise, the existence of an L1 escape/message path does not itself authorize HTP to use it.

Any future pause, liquidation, forced-inclusion, transaction-submission or upgrade capability requires a new legal/security authorization record.

---

## Contractual questions before a live pilot

At minimum a real client agreement should allocate or address:

- exact service scope and non-reliance/decision responsibilities appropriate to the service;
- data sources and permissions;
- confidentiality and incident handling;
- client decision authority;
- availability/support expectations;
- limitations and known non-evaluable states;
- record/audit retention;
- security responsibilities;
- change control when protocols, feeds or policies change;
- termination and safe shutdown;
- liability/indemnity as advised by competent counsel;
- governing law and dispute process.

This list is issue-spotting, not model contract language.

## Required legal closeout artifact

Before any live service or protected pilot, replace this draft status with a versioned record containing:

```yaml
legal_closeout:
  htp_entity: PENDING
  establishment_and_jurisdictions: []
  client_entity: PENDING
  client_jurisdictions: []
  networks:
    - solana
    - arbitrum_one
  activities:
    observation: PENDING_CLASSIFICATION
    alerting: PENDING_CLASSIFICATION
    personalized_recommendation: PENDING_CLASSIFICATION
    transaction_submission: EXCLUDED
    signing_or_custody: EXCLUDED
    pause_or_liquidation: EXCLUDED
    forced_inclusion: EXCLUDED
  data_roles: PENDING
  contractual_conditions: []
  legal_sources_checked_at: PENDING
  counsel_or_authorized_reviewer: PENDING
  reviewer_capacity: PENDING
  signed_or_approved_at: PENDING
  conditions_and_expiry: []
```

## Gate decision

Artifact 02 is **documentarily prepared but legally open**.

Gate 0 cannot be marked passed while the service-relevant jurisdiction/activity questions remain unsigned/unresolved by the required competent authority. The Legal Compliance Checker agent can structure and challenge this memo; it does not substitute for a legally accountable human opinion where one is required.
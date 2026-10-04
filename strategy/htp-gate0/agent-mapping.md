# HTP Gate 0 — Concrete Agent Mapping for Solana + Arbitrum

> **Status:** operational mapping for the Gate 0 package. Human accountable owners, legal sign-off, and governance approval remain unassigned unless explicitly recorded elsewhere.

## Purpose

This mapping replaces abstract Gate 0 seats with concrete agents from this repository while preserving the HTP rule that seats are **accountabilities**, not autonomous authority. An agent can prepare, challenge, or review an artifact; it cannot invent legal authority, security acceptance, production permission, or a human signature.

## Closed mapping

| Seat | Concrete agent | Repository path | Gate 0 mandate | Hard boundary |
|---|---|---|---|---|
| **G1** | Chief of Staff | `specialized/specialized-chief-of-staff.md` | Route Gate 0 work, keep the six-artifact package synchronized, surface unresolved decisions, and obtain named accountable owners | Does not set security thresholds, issue legal opinions, or authorize live execution |
| **P1** | Product Manager | `product/product-manager.md` | Own object/non-object, buyer/beneficiary framing, MVP definition, loss-to-buy-down logic, success/failure conditions, and falsifiers | Does not convert an attractive opportunity into evidence or authorization |
| **S1** | Blockchain Security Auditor | `security/security-blockchain-security-auditor.md` | Transversal adversarial review across both networks; challenge trust boundaries, economic assumptions, oracle paths, composability, and security invariants | Common reviewer does **not** mean common implementation semantics or shared approval across chains |
| **D1** | Research Synthesist | `research/research-synthesist.md` | Build source-weighted evidence maps, trace claims to primary sources, preserve disagreements, and identify evidence gaps | Does not upgrade hypotheses to findings or treat repeated citations as independent evidence |
| **E1-SOL** | Solana Program Engineer | `engineering/engineering-solana-program-engineer.md` | Solana-specific domain map and technical contract: Rust/Anchor, accounts, ownership, PDAs, CPI, signer seeds, SPL Token/Token-2022, transaction boundaries, and Solana DeFi invariants | No production writes, signing, transaction submission, custody, or protocol changes during Gate 0 |
| **E1-ARB** | Solidity Smart Contract Engineer | `engineering/engineering-solidity-smart-contract-engineer.md` | Arbitrum-specific domain map and technical contract: Solidity/EVM, deployed contract dependencies, oracle integration, L2 recovery semantics, and EVM DeFi invariants | No production writes, liquidation, forced inclusion, pause, upgrade, or contract changes during Gate 0 |
| **D3** | Proposition & Citation Auditor | `research/research-proposition-citation-auditor.md` | Own the claim registers, evidence-status discipline, source-to-claim traceability, citation drift, cross-network scope control, and derivative-artifact review | Does not certify legal/security conclusions or authorize production behavior |

## Mandatory supporting seat

The six-seat mapping above does not eliminate the legal work required by Runbook A. The jurisdiction/activity memo is prepared and reviewed with:

| Supporting seat | Concrete agent | Repository path | Authority note |
|---|---|---|---|
| **G2** | Legal Compliance Checker | `support/support-legal-compliance-checker.md` | Produces issue spotting, regulatory mapping, and a draft compliance analysis. It is **not** external counsel and does not turn the memo into a signed legal opinion. |

If a real legal opinion or authorization is required, a named competent human/legal authority must be recorded in the Gate 0 decision.

## Why E1 is split

The original E1 mandate was to preserve domain boundaries — observation ≠ detection ≠ policy ≠ execution. That accountability remains common, but the implementation model is not portable enough to assign to one generic engineering personality.

- **E1-SOL** reasons from Solana accounts, program ownership, signer privileges, PDAs, CPIs, Token/Token-2022 semantics, slots and transaction composition.
- **E1-ARB** reasons from the EVM/L2 execution model, Solidity contracts, call graphs, proxies, oracle contracts, sequencer/recovery dependencies, and EVM transaction semantics.
- They share an architectural vocabulary and event/evidence envelope only where the relationship is genuinely conserved.

A common field name is not evidence that the underlying semantics are common.

## Why S1 is transversal

S1 is the common adversarial reviewer because the security questions share higher-level mechanisms: authority, trusted inputs, composability, valuation, economic manipulation, failure modes, and unsafe transitions. The chain overlays prevent this common role from flattening important differences.

S1 therefore:

1. reviews each chain independently against its own overlay;
2. may identify a `common_mechanism`, but must attach separate Solana and Arbitrum evidence;
3. may not port an EVM remediation directly into Solana or a Solana control directly into Arbitrum without the relevant E1 accepting the adapted design;
4. returns findings rather than silently editing an E1 artifact;
5. cannot grant production authorization.

## D1 vs D3

These roles deliberately overlap at the evidence boundary but are not interchangeable.

- **D1** asks: *What does the external and internal evidence actually support, how strong is it, and what remains unknown?*
- **D3** asks: *Is every proposition in our artifacts still traceable to that evidence at the correct scope, status, version, denominator, and uncertainty?*

D1 can discover a stronger source. D3 controls whether that source justifies changing the claim record.

## Authority model

| Decision | Agent contribution | Final authority |
|---|---|---|
| Object/non-object | G1 + P1 draft and challenge | Named human product/governance owner |
| Jurisdiction/activity | G2 analysis | Competent legal/human authority where required |
| Threat model | S1 + D1 | Named security/risk owner for acceptance |
| Domain maps | E1-SOL / E1-ARB, challenged by S1 | Named architecture/security owner |
| Claim status | D3 audit + evidence record | Named reviewer recorded in claim history |
| Gate 0 pass/fail | Package prepared by mapped agents | Human governance authority |
| Any live action | Out of Gate 0 | Explicitly authorized production control path only |

## Cross-network independence rule

The package may share schemas, review mechanics, and higher-level vocabulary. It may **not** share by implication:

- detector validation;
- performance metrics;
- security acceptance;
- oracle thresholds;
- recovery thresholds;
- legal classification;
- buyer economics;
- claim status;
- Gate approval.

A transfer from one network to the other requires an explicit transfer proposition with conserved relations, limits, and chain-specific verification.

## Gate 0 package ownership

| Artifact | Lead seats | Supporting review |
|---|---|---|
| `gate0/01-object-non-object.md` | G1 + P1 | D3 scope/claim audit |
| `gate0/02-jurisdiction-activity.md` | G2 (supporting mandatory seat) | G1 routing; D3 citation/scope audit |
| `gate0/03-threat-model.md` | S1 + D1 | E1-SOL / E1-ARB for chain semantics |
| `gate0/04-domain-map.md` | E1-SOL + E1-ARB | S1 adversarial review; G1 boundary consistency |
| `gate0/05-claim-registers.yaml` | D3 | D1 source lineage; G1 package sync |
| `gate0/06-mvp-falsifiers.md` | P1 | D1/D3 methodological traceability; S1/E1 feasibility |

## Operational rule

Until the six Gate 0 artifacts, named human owners, mandatory legal review, E1↔S1 handoffs, and independent governance review are complete, this package remains **Gate 0 pending**. No agent in this mapping is authorized by the mapping itself to write production paths or move a security control out of shadow/research mode.
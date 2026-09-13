# HTP Gate 0 — E1-SOL / E1-ARB / S1 Handoff Contract

> **Scope:** Gate 0 Solana + Arbitrum One.
>
> **Rule:** Every handoff is a versioned artifact, not conversational context. The receiving agent checks scope, artifact version, evidence status and authority before acting.

## Roles

| Seat | Agent | Responsibility in this contract |
|---|---|---|
| **E1-SOL** | Solana Program Engineer | Produce and revise Solana-specific domain/authority/dependency artifacts |
| **E1-ARB** | Solidity Smart Contract Engineer | Produce and revise Arbitrum-specific domain/contract/dependency artifacts |
| **S1** | Blockchain Security Auditor | Independently challenge each chain artifact, document findings and return a review disposition |

S1 is transversal at the **review mechanism** level, not at the implementation-semantics level. E1-SOL and E1-ARB remain separate owners of chain-specific technical meaning.

## Non-negotiable separation

- E1-SOL does not approve Arbitrum semantics.
- E1-ARB does not approve Solana semantics.
- S1 may identify a shared mechanism, but a common mechanism must carry separate evidence and remediation paths for each chain.
- An EVM remediation is not copied into Solana without E1-SOL adapting and accepting it.
- A Solana account/CPI control is not copied into Arbitrum without E1-ARB translating the relevant invariant into EVM/L2 semantics.
- Neither E1 marks its own artifact “security accepted.”
- S1 does not silently edit an E1 artifact. It returns findings or accepts a submitted revision.
- A disagreement remains unresolved until a named reviewer records a decision; schedule pressure is not resolution.

## Handoff lifecycle

Allowed states:

`proposed → accepted → working → submitted → accepted_result | changes_requested`

Exceptional terminal/intermediate states:

- `blocked`
- `expired`

A receiver must reject or block a handoff when scope, version, authority or evidence references are insufficient for the requested work.

## Canonical handoff schema

```yaml
handoff:
  id: hnd_<network>_<sequence>
  from_seat: E1-SOL | E1-ARB | S1
  to_seat: S1 | E1-SOL | E1-ARB
  network_scope: solana | arbitrum_one
  governing_object: "bounded description of the decision/review object"
  non_object: "what this handoff cannot decide or authorize"
  artifact_ref: "versioned repository artifact"
  artifact_hash: "sha256 or immutable git reference"
  evidence_refs: []
  evidence_status: hypothesis | backtested | shadow_validated | production_validated | independently_verified
  environment: documentary | local | replay | fork | shadow
  authority_ref: null
  requested_work: review | revise | verify_remediation | resolve_scope
  allowed_tools: []
  prohibited_actions:
    - production_write
    - external_disclosure
    - transaction_signing
    - transaction_submission
    - custody
    - live_pause
    - forced_inclusion
    - liquidation
    - unauthorized_upgrade
    - live_third_party_exploitation
  unresolved_questions: []
  acceptance_criteria: []
  budget: "approved task/evidence budget"
  expires_at: "UTC timestamp or explicit Gate 0 milestone"
  reviewer: "named accountable reviewer or PENDING"
  status: proposed
```

`authority_ref: null` means the handoff grants **no live operational authority**. It must never be interpreted as implicit permission.

## Required E1 → S1 package

### E1-SOL → S1

The submitted Solana package must include:

- scoped protocol/program/market/feed manifest;
- instruction/account contract for relevant paths;
- runtime-owner, signer/writable and authority relationships;
- PDA seeds/bumps and signer-capability boundaries where relevant;
- CPI targets and privilege propagation assumptions;
- SPL Token / Token-2022 compatibility matrix for relevant assets;
- exact oracle adapter/version semantics and consumed-value path;
- transaction/slot timing model;
- economic invariants and known non-evaluable states;
- domain map showing observation ≠ detection ≠ policy ≠ execution ≠ evidence;
- explicit unresolved questions.

### E1-ARB → S1

The submitted Arbitrum package must include:

- Arbitrum One protocol/market/contract manifest;
- proxy/implementation and relevant admin/upgrade relationships;
- exact oracle/feed contract path, units/decimals and consumed-value semantics;
- sequencer-status dependency if used;
- RPC/indexer observation dependencies kept separate from chain state;
- recovery-state model;
- any L1/L2 messaging or delayed-path assumption actually relevant to the scoped use case;
- economic invariants, liquidity/position dependencies and known non-evaluable states;
- domain map showing observation ≠ detection ≠ policy ≠ execution ≠ evidence;
- explicit unresolved questions.

## Required S1 → E1 review

Every S1 finding must contain:

```yaml
finding:
  id: SEC_<network>_<nnn>
  network_scope: solana | arbitrum_one
  severity: critical | high | medium | low | informational
  invariant: "property expected to hold"
  observed_or_assumed_behavior: "what the artifact/code/evidence says"
  attack_or_failure_scenario: "defensive scenario; no live exploitation"
  preconditions: []
  impact: "bounded impact statement"
  evidence_refs: []
  uncertainty: "what remains unproved"
  requested_change: "specific correction or additional evidence"
  verification_criteria: []
  disposition: open
```

S1 must distinguish:

- demonstrated defect;
- unsupported assumption;
- incomplete evidence;
- design trade-off;
- out-of-scope concern.

A finding is not upgraded in severity merely because the scenario is rhetorically alarming.

## Remediation loop

1. E1 submits versioned artifact.
2. S1 accepts the handoff and records review scope.
3. S1 returns findings; no silent rewrite.
4. E1 responds finding-by-finding with:
   - `fixed` + artifact/evidence reference;
   - `accepted_risk` + named human authority reference;
   - `disputed` + reasoning/evidence;
   - `out_of_scope` + scope rationale.
5. S1 verifies relevant remediations and returns `accepted_result`, `changes_requested`, or `blocked`.
6. D3 checks that final artifact wording does not overstate the review result.
7. G1 ensures unresolved material disagreements are escalated to the named human reviewer before Gate 0 decision.

No agent may translate `accepted_result` into “production certified.” It means the requested Gate 0 review scope was completed with the recorded evidence and limitations.

## Cross-chain common-mechanism record

When S1 believes a mechanism is common across both networks, record it like this:

```yaml
common_mechanism:
  id: CM_<nnn>
  statement: "higher-level mechanism only"
  solana:
    evidence_refs: []
    implementation_semantics: "Solana-specific"
    e1_owner: E1-SOL
    status: hypothesis
  arbitrum_one:
    evidence_refs: []
    implementation_semantics: "Arbitrum/EVM-specific"
    e1_owner: E1-ARB
    status: hypothesis
  prohibited_inference: "One chain's evidence does not upgrade the other chain's status"
  reviewer: S1
```

Examples of potentially common mechanisms include stale valuation, authority overreach or loss of observability. Their controls and evidence remain chain-specific.

## Gate 0 required handoffs

### `hnd_gate0_sol_e1_to_s1`

```yaml
handoff:
  id: hnd_gate0_sol_e1_to_s1
  from_seat: E1-SOL
  to_seat: S1
  network_scope: solana
  governing_object: "Review Solana domain map and technical assumptions for SOL-ORD and SOL-ORC"
  non_object: "Authorize deployment, transactions, custody, pauses, or public attribution"
  artifact_ref: strategy/htp-gate0/gate0/04-domain-map.md
  artifact_hash: PENDING_GIT_REVISION
  evidence_refs:
    - strategy/htp-gate0/overlays/solana.md
    - strategy/htp-gate0/gate0/03-threat-model.md
  evidence_status: hypothesis
  environment: documentary
  authority_ref: null
  requested_work: review
  allowed_tools: [read, static_review, local_test, replay, simulation]
  prohibited_actions: [production_write, external_disclosure, transaction_signing, transaction_submission, custody, live_pause, liquidation, live_third_party_exploitation]
  unresolved_questions: [named_protocol, deployed_program_manifest, oracle_adapter_versions]
  acceptance_criteria: [account_and_authority_boundaries_explicit, cpi_and_token_semantics_reviewed, execution_domain_disabled, uncertainties_recorded]
  budget: Gate0
  expires_at: GATE0_DECISION
  reviewer: PENDING_HUMAN_OWNER
  status: proposed
```

### `hnd_gate0_arb_e1_to_s1`

```yaml
handoff:
  id: hnd_gate0_arb_e1_to_s1
  from_seat: E1-ARB
  to_seat: S1
  network_scope: arbitrum_one
  governing_object: "Review Arbitrum One domain map and technical assumptions for ARB-ORC and ARB-RES"
  non_object: "Authorize deployment, liquidations, force inclusion, pauses, upgrades, or public attribution"
  artifact_ref: strategy/htp-gate0/gate0/04-domain-map.md
  artifact_hash: PENDING_GIT_REVISION
  evidence_refs:
    - strategy/htp-gate0/overlays/arbitrum.md
    - strategy/htp-gate0/gate0/03-threat-model.md
  evidence_status: hypothesis
  environment: documentary
  authority_ref: null
  requested_work: review
  allowed_tools: [read, static_review, local_test, fork, replay, simulation]
  prohibited_actions: [production_write, external_disclosure, transaction_signing, transaction_submission, custody, live_pause, forced_inclusion, liquidation, unauthorized_upgrade, live_third_party_exploitation]
  unresolved_questions: [named_protocol, market_and_contract_manifest, exact_oracle_implementations]
  acceptance_criteria: [oracle_path_explicit, rpc_vs_sequencer_state_separated, recovery_model_reviewed, execution_domain_disabled, uncertainties_recorded]
  budget: Gate0
  expires_at: GATE0_DECISION
  reviewer: PENDING_HUMAN_OWNER
  status: proposed
```

## Scope-dispute escalation

If E1 and S1 disagree about whether an issue belongs in Gate 0:

1. D1 supplies the strongest available evidence and alternatives.
2. D3 states what can be claimed at the current evidence level.
3. G1 frames the unresolved decision and its consequence for the Gate.
4. A named human reviewer decides whether to fix, accept as bounded residual risk, reduce scope, or block the Gate.

The review cannot be closed by averaging agent opinions.

## Completion condition

This handoff contract is satisfied for Gate 0 only when both chain-specific E1→S1 cycles reach a recorded disposition and D3 confirms the resulting language is consistent with the evidence record. A complete Solana cycle cannot substitute for an incomplete Arbitrum cycle, or vice versa.
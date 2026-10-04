# S1 Review — Kamino Lend / Solana

> **Handoff:** `hnd_gate0_sol_kamino_001`  
> **Reviewer:** S1 — Blockchain Security Auditor  
> **Input owner:** E1-SOL — Solana Program Engineer  
> **Review scope:** Kamino Lend Main Market, SOL/USDC, `SOL-ORC` + candidate `SOL-ORD`  
> **Disposition:** **BLOCKED** pending runtime manifest completion

## Executive disposition

The documentary deployment identity is sufficiently concrete to stop using an abstract “Solana lending protocol” placeholder: the Kamino lending program, Main market and SOL/USDC reserve surface are named and source revisions are pinned.

That is **not yet sufficient** to construct a security-valid Gate 0 benchmark. The highest-risk missing evidence is the exact live reserve/oracle configuration. The current manifest deliberately records that gap rather than substituting documentation examples. S1 accepts that epistemic handling and blocks advancement until the live snapshot exists.

`SOL-ORC` remains the primary active class. `SOL-ORD` is held because the current manifest freezes a lending program and reserves but does not yet freeze the external swap/router/DEX or liquidation path required to define an ordering population.

## Findings

### SEC_SOL_001 — High — Exact live oracle contract is not frozen

**Invariant:** A valuation-quality detector must evaluate the exact oracle configuration consumed by the scoped reserve path at the frozen state.

**Observed state:** The manifest identifies the SOL and USDC reserves but records `oracle_configuration`, price-feed mappings and age/quality parameters as `PENDING_RUNTIME_SNAPSHOT`.

**Impact:** Without the live `tokenInfo`/oracle configuration, HTP cannot prove feed identity, provider/version, scale/time semantics, or the policy inputs needed to label a reserve observation `DEGRADED`, `INVALID`, `UNSUPPORTED` or `HEALTHY_OBSERVED`. Using a documentation example would create a false security boundary.

**Preconditions for remediation:** read-only capture of the exact reserve accounts at an immutable slot, including the full reserve configuration and oracle mappings.

**Required change:** freeze the SOL and USDC reserve configs, account hashes and exact oracle accounts/provider modalities at a named slot. Record provider-specific publication/update fields separately from monitor observation time.

**Verification criteria:**
- immutable slot/block time recorded;
- reserve account hashes and owners recorded;
- exact oracle addresses and configuration fields recorded;
- scale/decimals/exponent semantics documented;
- current max-age/quality policy distinguished from HTP/client evaluation policy;
- unsupported modality fails to `UNSUPPORTED`, never healthy.

**Disposition:** open — **Gate blocker**.

---

### SEC_SOL_002 — Medium — Pinned source release is not proven equal to deployed program bytes

**Invariant:** Source-level assumptions must not be attributed to a deployed program without establishing the deployment relationship relevant to the claim.

**Observed state:** `Kamino-Finance/klend@a087609...` identifies the public mainnet program ID, but the instance has not frozen ProgramData, upgrade authority or a deployed binary/hash relationship.

**Impact:** Source review may describe code that is not byte-identical to the deployed upgradeable program at the benchmark slot. This weakens findings about account constraints, CPI paths and instruction semantics.

**Required change:** capture program account, ProgramData account, upgrade authority and a reproducible deployed-binary/source-build identity statement. If exact reproducible byte parity cannot be established, narrow claims to interface/account observations and label source-derived internals accordingly.

**Disposition:** open — changes required before code-level security acceptance.

---

### SEC_SOL_003 — Medium / Scope Blocker — SOL-ORD execution surface is incomplete

**Invariant:** An adverse-ordering benchmark must define an eligible transaction population and the execution venues whose ordering can alter the client outcome.

**Observed state:** The frozen scope names Kamino Lend, the Main market and reserves. It does not name the swap router/aggregator, DEX programs/pools, Multiply/leveraged flow, or liquidation flow whose ordering would be evaluated.

**Impact:** A generic “Kamino adverse ordering” claim would conflate lending state transitions with external swap/order-flow behavior and make both the denominator and counterfactual undefined.

**Required change:** either:

1. freeze one actual Kamino user flow that invokes a named swap/router/DEX or liquidation path, then enumerate the programs/pools and eligible transaction population; or
2. remove `SOL-ORD` from the first Kamino benchmark and run Gate 0 on `SOL-ORC` only.

**Disposition:** `SOL-ORD` **HOLD** until one of the two paths above is chosen.

---

### SEC_SOL_004 — Informational — Token semantics remain runtime assertions

**Invariant:** Mint/account authority and token-program identity must be verified from chain state rather than assumed from asset labels.

**Observed state:** SOL/USDC mints are frozen but token-program identity and relevant token-account relationships are pending runtime capture.

**Impact:** Low for the documentary manifest, material if future accounting logic assumes vanilla token behavior or a particular account authority without verification.

**Required change:** capture token-program IDs and relevant token account/mint relationships for the scoped paths. Explicitly record whether Token-2022 is absent or present; do not infer absence by symbol.

**Disposition:** open; not independently Gate-blocking once runtime account contract is captured.

## S1 acceptance of what is already frozen

S1 accepts the following as the **documentary identity layer**, subject to runtime verification rather than as deployment-byte proof:

- Kamino Lend mainnet program ID is explicitly named in the pinned public source.
- Main market is fixed as `7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF`.
- SOL reserve is fixed as `d4A2prbA2whesmvHaL88BH6Ewn5N4bTSU2Ze8P6Bc4Q`.
- USDC Main-market reserve is fixed as `D6q6wuQSrifJKZYpR1M8R4YawnLDtDsMmWM1NbBmgJ59`.
- Missing runtime state is represented as missing rather than silently inferred.

## Required E1-SOL resubmission

E1-SOL should resubmit only after adding a runtime snapshot appendix containing:

1. immutable slot/time;
2. program + ProgramData + upgrade authority;
3. market and reserve owners/hashes;
4. complete SOL/USDC reserve configs;
5. exact oracle accounts/provider versions/policy-relevant fields;
6. token-program/account relationships;
7. either a concrete SOL-ORD execution surface or explicit removal of SOL-ORD from the initial benchmark.

## Review result

```yaml
review_result:
  handoff: hnd_gate0_sol_kamino_001
  network: solana
  protocol: Kamino_Lend
  disposition: blocked
  SOL_ORC: blocked_pending_runtime_oracle_manifest
  SOL_ORD: hold_pending_execution_surface
  security_acceptance: false
  production_authority: false
  next_owner: E1-SOL
```

This result is a Gate 0 review disposition, not a claim that Kamino is insecure and not a production security certification.
# Gate 0 Instance Status — 2026-09-13

> **Instance:** Kamino Lend Main Market (SOL/USDC) + Aave V3.7 Arbitrum One (WETH/native USDC)  
> **Gate:** 0  
> **Overall:** **HOLD** — concrete protocols instantiated; runtime manifests incomplete

## Network decisions after first E1→S1 loop

| Network | Protocol | Static manifest | First S1 disposition | Gate 0 state |
|---|---|---|---|---|
| Solana | Kamino Lend Main Market | frozen with explicit gaps | **BLOCKED** | **HOLD** |
| Arbitrum One | Aave V3.7 | static deployment accepted | **CHANGES_REQUESTED** | **HOLD** |

## Solana — Kamino

### Frozen now

- Kamino Lend mainnet program ID.
- Pinned public source release (`Kamino-Finance/klend@a087609...`).
- Pinned SDK constants (`Kamino-Finance/klend-sdk@388452...`).
- Main market and lookup table.
- SOL reserve and mint.
- USDC Main-market reserve and mint.
- Threat-class treatment: `SOL-ORC` active; `SOL-ORD` held until an external execution surface is named.

### Blocks advancement

1. no immutable live SOL/USDC reserve-config/oracle dump;
2. no ProgramData/upgrade-authority/deployed-byte parity record;
3. no frozen router/DEX/liquidation execution surface for `SOL-ORD`.

### Next E1-SOL deliverable

A read-only runtime appendix at one immutable slot with account owners/hashes, ProgramData, full reserve configs, exact oracle configuration and either a named `SOL-ORD` execution path or explicit removal of `SOL-ORD` from the first benchmark.

---

## Arbitrum — Aave V3.7

### Frozen now

- Arbitrum One chain scope.
- Current Aave address-book release on the freeze date.
- Pool/implementation, PoolConfigurator/implementation, AaveOracle and ProtocolDataProvider.
- WETH underlying/aToken/debt token/oracle source.
- native USDC (`USDCn`) underlying/aToken/debt token/oracle source.
- v3.7 architectural rule: borrow/liquidation validation no longer uses PriceOracleSentinel/SequencerOracle gating.
- `ARB-RES` redefined as external recovery/exposure observation rather than an Aave protocol permission gate.

### Blocks advancement

1. reserve risk parameters not frozen at an immutable block;
2. oracle-source runtime/unit/time semantics not frozen;
3. external recovery observation stack and client recovery policy not frozen.

### Next E1-ARB deliverable

A read-only runtime appendix at one immutable block with proxy implementation-slot verification, WETH/native-USDC reserve configuration, relevant eMode/user state, AaveOracle source resolution/interface semantics and a versioned external `ARB-RES` observation/recovery policy.

---

## What the first handoffs changed

The first review cycle produced two concrete scope corrections rather than a paper PASS:

1. **Kamino:** the initial `SOL-ORD` class is not benchmark-ready merely because Kamino is a Solana DeFi protocol. The ordering surface must include a real swap/router/DEX or liquidation path; otherwise the first benchmark should be `SOL-ORC` only.
2. **Aave:** the old L2 PriceOracleSentinel/sequencer-gating mental model is invalid for v3.7. Recovery monitoring can still be commercially/security relevant, but it is external observation and exposure analysis, not an internal Aave permission state.

## Gate 0 decision

```yaml
gate0_instance:
  id: gate0-2026-09-13-kamino-aave
  solana:
    protocol: Kamino_Lend
    state: HOLD
    s1_disposition: BLOCKED
    next_owner: E1-SOL
  arbitrum_one:
    protocol: Aave_V3_7
    state: HOLD
    s1_disposition: CHANGES_REQUESTED
    next_owner: E1-ARB
  production_authority: false
  benchmark_authority: false
  claim_register_status: unchanged_empty
  legal_status: unchanged_pending
```

The correct next step is **runtime evidence capture**, not more abstract agent design and not a production build.
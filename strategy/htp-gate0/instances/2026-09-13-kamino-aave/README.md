# Gate 0 Instance — Kamino Lend + Aave V3.7 Arbitrum

> **Instance ID:** `gate0-2026-09-13-kamino-aave`  
> **Freeze date:** 2026-09-13  
> **Parent runbook:** `strategy/runbooks/scenario-htp-gate0-solana-arbitrum.md`  
> **Status:** instantiated; both network tracks remain pre-pass

## Concrete scopes

### Solana

- **Protocol:** Kamino Lend
- **Network:** Solana mainnet-beta
- **Market:** Kamino Main Market
- **Assets:** SOL and USDC
- **Threat classes:** `SOL-ORD`, `SOL-ORC`
- **Engineering seat:** E1-SOL — Solana Program Engineer
- **Security review:** S1 — Blockchain Security Auditor

### Arbitrum

- **Protocol:** Aave V3.7
- **Network:** Arbitrum One (chain ID 42161)
- **Assets:** WETH and native USDC (`USDCn` in the Aave address book)
- **Threat classes:** `ARB-ORC`, `ARB-RES`
- **Engineering seat:** E1-ARB — Solidity Smart Contract Engineer
- **Security review:** S1 — Blockchain Security Auditor

## Freeze semantics

A **frozen manifest** means that every populated identifier is pinned to a named primary source and immutable source revision. It does **not** mean that every live runtime field has been captured.

Dynamic values that were not independently read from chain state at the freeze point are recorded as `PENDING_RUNTIME_SNAPSHOT` or `UNVERIFIED`. They are not inferred from examples, generic documentation, historical values, or another network.

This distinction is deliberate:

- repository/source identity ≠ deployed byte identity;
- documented reserve address ≠ current reserve configuration;
- oracle source address ≠ proven current oracle answer/heartbeat policy;
- program/contract architecture ≠ runtime risk parameters;
- source commit date ≠ block/slot snapshot.

## Frozen primary source revisions

| Scope | Repository | Frozen revision | Purpose |
|---|---|---|---|
| Kamino lending program | `Kamino-Finance/klend` | `a08760976f51a3a58c4a0c6ea27b4a0e565bca79` | Mainnet program identity and source release (1.25.0) |
| Kamino market/reserve constants | `Kamino-Finance/klend-sdk` | `38845294447623f6de3afc9dec29875f959f6f48` | Main market, LUT, SOL/USDC reserve constants |
| Aave Arbitrum deployment | `aave-dao/aave-address-book` | `02748a20592a019e834aee193b6c40c9bc7bd059` | Current address-book release 4.67.4 on freeze date |
| Aave v3.7 sentinel semantics | `aave-dao/aave-v3-origin` | v3.7 documentation | Confirms PriceOracleSentinel/SequencerOracle removal and resulting validation semantics |

## Instance files

- `solana-kamino-manifest.yaml` — frozen Solana scope and unresolved runtime state.
- `arbitrum-aave-manifest.yaml` — frozen Arbitrum/Aave deployment scope and unresolved runtime state.
- `handoff-e1-sol-to-s1.yaml` — submitted E1-SOL handoff.
- `review-s1-solana.md` — first S1 review and disposition.
- `handoff-e1-arb-to-s1.yaml` — submitted E1-ARB handoff.
- `review-s1-arbitrum.md` — first S1 review and disposition.
- `instance-status.md` — combined Gate 0 status after the first review loop.

## Non-authority statement

This instance freezes research/review scope only. It does not authorize transaction signing/submission, custody, liquidation, pause/unpause, forced inclusion, program/contract upgrade, public attribution, or live intervention against either protocol.

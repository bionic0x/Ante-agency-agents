# S1 Review — Aave V3.7 / Arbitrum One

> **Handoff:** `hnd_gate0_arb_aave_001`  
> **Reviewer:** S1 — Blockchain Security Auditor  
> **Input owner:** E1-ARB — Solidity Smart Contract Engineer  
> **Review scope:** Aave V3.7 Arbitrum One, WETH/native USDC, `ARB-ORC` + `ARB-RES`  
> **Disposition:** **CHANGES_REQUESTED** — static deployment accepted, runtime/evaluation layer incomplete

## Executive disposition

The Aave track is materially more instantiated than the Solana track at the static-deployment layer. A current Aave address-book revision freezes the Pool, Pool implementation, PoolConfigurator, AaveOracle, WETH/native-USDC token surfaces and their oracle source addresses.

The first review also resolves a design error that would have invalidated `ARB-RES`: **Aave v3.7 removed `PriceOracleSentinel` / `SequencerOracle` checks from borrow and liquidation validation.** Therefore HTP must not represent sequencer uptime as an internal Aave permission gate. `ARB-RES` remains valid only as an **external risk-observation and recovery-exposure** class.

S1 does not block the architectural instance, but requires runtime reserve/oracle state and an explicit external recovery policy before benchmark construction.

## Findings

### SEC_ARB_001 — Medium / Design Blocker — Legacy sequencer-sentinel model is invalid for Aave v3.7

**Invariant:** The threat model must reflect the deployed protocol's actual validation dependencies.

**Observed state:** Aave v3.7 documentation removes `PriceOracleSentinel` and `SequencerOracle` from borrow/liquidation validation. Borrow and liquidation no longer consult sequencer uptime through this mechanism.

**Impact:** Any HTP model that treats sequencer status as Aave's protocol-level `ALLOW/DENY` control would produce false architecture, false recovery semantics and potentially misleading product claims. An external `UP` signal could also be misrepresented as evidence that Aave itself considers positions safe to resume or liquidate.

**Required change:** Retain `ARB-RES` only as an external observation/recovery-exposure state machine. Keep:

- monitor/RPC health;
- chain/sequencer progress evidence;
- oracle integrity;
- position state;
- executable liquidity; and
- client recovery policy

as separate inputs. None is automatically an Aave execution permission.

**Verification criteria:**
- no PriceOracleSentinel dependency appears in the frozen protocol core;
- no `UP = safe` rule exists;
- external sequencer/chain-progress inputs are labeled HTP/client observation dependencies;
- borrow/liquidation eligibility is reconstructed from current Aave v3.7 mechanics and runtime state, not v3.6 sentinel behavior.

**Disposition:** architecture correction accepted in the submitted manifest; retain as a permanent regression requirement.

---

### SEC_ARB_002 — High / Gate Blocker — Runtime reserve risk parameters are not frozen

**Invariant:** A liquidation/recovery replay must use the reserve and user-risk parameters actually effective at a named block.

**Observed state:** Static token/oracle/Pool identities are pinned, but WETH/native-USDC reserve configuration, liquidation thresholds/bonuses, caps, flags and eMode state remain `PENDING_RUNTIME_SNAPSHOT`.

**Impact:** Without those values, HTP cannot reconstruct health factor transitions, determine whether a modeled liquidation is eligible under the selected configuration, or quantify recovery exposure. A synthetic scenario could accidentally be presented as protocol-realistic while using stale or generic parameters.

**Required change:** capture at one immutable Arbitrum block:

- reserve configuration for WETH and native USDC;
- liquidation threshold and bonus;
- borrow/supply caps;
- active/frozen/paused state;
- eMode configuration/membership relevant to the evaluated accounts;
- implementation slots for the core proxies;
- position state for the eligible evaluation population.

**Disposition:** open — blocks benchmark execution, not the static manifest itself.

---

### SEC_ARB_003 — Medium — Oracle source addresses are frozen; source semantics are not

**Invariant:** `ARB-ORC` must validate the exact value semantics and timing properties of the price source used by Aave at the evaluation block.

**Observed state:** The manifest pins AaveOracle and WETH/native-USDC source addresses. It does not yet freeze runtime source resolution, units/base-currency semantics, round/update timestamp behavior, provider-specific validity conditions or any client-defined staleness policy.

**Impact:** A detector could incorrectly apply a universal age/heartbeat threshold, interpret source output in the wrong unit/base, or treat an auxiliary feed as authoritative replacement truth.

**Required change:** at the evaluation block, resolve AaveOracle→asset source, document returned units/base-currency conversion and verify provider/interface timing semantics. Freeze any HTP/client freshness/divergence policy separately from the protocol's own validation behavior.

**Disposition:** open — required before `ARB-ORC` benchmark.

---

### SEC_ARB_004 — Medium — ARB-RES observation stack and recovery policy remain undefined

**Invariant:** A recovery-state detector must identify independent evidence channels and a versioned policy for state transitions.

**Observed state:** The protocol no longer supplies a sequencer sentinel decision path. The instance has not yet selected external chain-progress/sequencer evidence, RPC providers, reference prices, position/liquidity evidence, or the client policy that maps those signals into `RECOVERING`, `READY_FOR_REVIEW` and `NORMAL`.

**Impact:** Without a frozen external observation stack, `ARB-RES` can degrade into an informal narrative based on whichever signal is available after an incident.

**Required change:** freeze at least one chain-progress source independent of each monitored RPC path, observation-channel health, price inputs and a client-owned recovery policy. Define missing/contradictory evidence as `UNKNOWN` rather than defaulting to normal.

**Disposition:** open — changes requested before shadow/benchmark work.

## S1 acceptance of what is already frozen

S1 accepts the following as the **static documentary deployment layer** for this instance:

- Arbitrum One / chain ID 42161 is the selected network.
- Aave address-book revision `02748a20592a019e834aee193b6c40c9bc7bd059` is the frozen deployment reference.
- Pool proxy and current address-book implementation are explicitly pinned.
- PoolConfigurator, AaveOracle and ProtocolDataProvider are explicitly pinned.
- WETH and native USDC (`USDCn`) underlying/aToken/variable-debt/oracle-source addresses are explicitly pinned.
- The manifest correctly models Aave v3.7 as having no sequencer-sentinel borrow/liquidation gate.

This acceptance does not prove implementation-slot state or source-feed runtime behavior at a future benchmark block; those must be captured from chain state.

## Required E1-ARB resubmission

E1-ARB should resubmit after adding a runtime snapshot appendix containing:

1. immutable block number/time;
2. proxy implementation-slot verification;
3. WETH/native-USDC reserve configuration;
4. relevant eMode and user-position state;
5. current AaveOracle source resolution plus source interface/time/unit semantics;
6. external ARB-RES observation sources;
7. versioned client recovery policy and non-evaluable-state handling.

## Review result

```yaml
review_result:
  handoff: hnd_gate0_arb_aave_001
  network: arbitrum_one
  protocol: Aave_V3_7
  disposition: changes_requested
  static_deployment_manifest: accepted
  ARB_ORC: changes_requested_pending_runtime_oracle_and_reserve_snapshot
  ARB_RES: changes_requested_external_monitor_model_accepted_but_inputs_pending
  security_acceptance: false
  production_authority: false
  next_owner: E1-ARB
```

This is a Gate 0 design/security review. It is not a claim that Aave is insecure, that an incident is occurring, or that HTP has authority to act on Aave.
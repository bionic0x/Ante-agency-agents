# Gate 0 Artifact 06 — MVP Statements & Falsifiers

> **Lead:** P1 Product Manager  
> **Evidence/method review:** D1 + D3  
> **Technical feasibility:** S1 + E1-SOL / E1-ARB  
> **Status:** DRAFT — test parameters and client scopes pending

## Product discipline

The MVP is not “a detector that emits alerts.” It is a bounded decision-support product whose value proposition must survive four separate tests:

1. **observability** — can the relevant state be reconstructed or observed at all?
2. **classification** — can the scoped condition be distinguished from alternatives with useful error rates and coverage?
3. **timeliness** — is the evidence available before the decision the product claims to improve?
4. **economic usefulness** — when adopted, does the intervention improve the client's net outcome after costs and induced harms?

Failure at an earlier link cannot be repaired by stronger language at a later link.

---

# A. Solana MVP

## MVP statement

For one named Solana protocol and no more than the two scoped classes, produce a **reproducible event dossier** that distinguishes:

- `SOL-ORD`: supported adverse-ordering harm vs structural pattern only vs non-evaluable/alternative explanation;
- `SOL-ORC`: degraded/invalid valuation input vs healthy-observed vs unsupported/unknown;
- lack of observability as an explicit product state.

The first evaluable deliverable is a **closed benchmark** with frozen scope, labels, missingness, errors and non-evaluable cases. Only after that may the design proceed to a prospective shadow test with no intervention.

## Solana customer hypothesis

A protocol risk/operations team will pay for a dossier only if it improves a real decision beyond existing monitoring/review at an acceptable total cost and without requiring HTP to hold keys or execute protocol actions.

This buyer remains hypothetical until a named protocol/team is identified.

## Solana causal chain

```text
sufficient/reconstructible data
        ↓
valid class label with known error/missingness
        ↓
signal available with useful lead time
        ↓
client receives and adopts a decision
        ↓
net economic outcome improves relative to frozen alternative
```

Replay can test the first two links. Shadow can test prospective availability/delivery. Adoption and economic benefit require a later authorized pilot.

## Solana technical falsifiers

The class is **redesigned or narrowed** if, on a frozen evaluation set sufficient for the pre-registered decision:

- the required protocol state cannot be reconstructed for a material share of the eligible population and the product thesis requires that coverage;
- precision/recall/coverage intervals fail the minimum useful thresholds frozen before evaluation;
- SOL-ORD cannot distinguish the defined harm mechanism from ordinary arbitrage/external movement/low depth/route inefficiency at the required decision quality;
- SOL-ORC cannot identify the price/update actually consumed or the relevant provider/version remains unsupported;
- the detector silently maps `UNKNOWN`/`UNSUPPORTED` into a healthy state;
- the result depends materially on information that was not available at the event time.

An underpowered or highly uncertain result is `INCONCLUSIVE`, not automatic falsification or success.

## Solana opportunity falsifier

If the evidence required for a positive signal becomes available **after** the transaction/decision it claims to protect, the preventive proposition is rejected for that event/channel.

If this timing failure dominates the pre-specified eligible population, the product must either:

- obtain a genuinely prospective authorized data channel and retest; or
- redefine the product explicitly as retrospective audit/forensics rather than prevention.

## Solana economic falsifier

With a sufficiently informative authorized pilot, reject the commercial thesis for the scoped use case if the **upper bound** of the estimated net benefit remains below the pre-specified minimum economically useful effect after accounting for:

- service/operational cost;
- review/adoption cost;
- delay imposed by the policy;
- induced execution/slippage costs;
- solvency/bad-debt effects where relevant;
- false-positive and false-negative consequences;
- transfers between participants that are not net harm reduction.

A wide interval spanning meaningful benefit and harm is `INCONCLUSIVE` and consumes only the pre-approved evidence budget before redesign/termination review.

---

# B. Arbitrum One MVP

## MVP statement

For one named Arbitrum One lending protocol, produce a **reproducible temporal dossier** that distinguishes:

- monitor/RPC observation failure;
- `ARB-ORC`: invalid/degraded price consumed by the scoped protocol path;
- `ARB-RES`: service interruption and recovery state;
- recovery whose data/time conditions improved but whose position/liquidity exposure remains unresolved.

The first evaluable deliverable is a frozen set of historical events and labeled synthetic scenarios that tests invariants, reconstruction and timing without production intervention.

## Arbitrum customer hypothesis

A lending-protocol risk/operations team will pay for evidence that reduces ambiguity during price-data degradation and sequencer/service recovery **only if** the dossier changes a real decision early enough and the policy does not create larger net insolvency/liquidity costs than it avoids.

## Arbitrum causal chain

```text
independent monitor + chain/feed observations
        ↓
correct separation of observation failure / price failure / outage / recovery
        ↓
state available before the target risk decision
        ↓
client adopts an authorized response
        ↓
net outcome improves under the pre-specified comparison policy
```

## Arbitrum technical falsifiers

Redesign the relevant class if the system materially:

- treats isolated RPC/provider failure as sequencer/network outage;
- declares recovery from one `UP` signal while configured price/time/exposure conditions remain unmet;
- cannot reconstruct the price actually consumed by the protocol when the product claim depends on it;
- conflates a healthy oracle response with protocol solvency;
- uses a synthetic cascade as if it were observed loss;
- relies on a fallback/L1 path without establishing applicability to the scoped failure mode;
- depends on an example grace period or generic threshold rather than the frozen client policy;
- hides missing position/depth data instead of reporting exposure `UNKNOWN`.

## Arbitrum opportunity falsifier

If the dossier/warning becomes available only after the first client decision it claims to improve, there is no prospective benefit for that event.

If this dominates a sufficient pre-specified sample, abandon the prevention claim for that delivery channel or redesign the data/integration path before further validation.

## Arbitrum economic falsifier

Reject a proposed protective/recovery policy if, under the frozen client objective and sufficiently informative evidence, the policy's delay or restriction increases expected **net** cost beyond the accepted risk budget — even when it reduces the count of immediate liquidations.

Costs may include:

- borrower harm;
- liquidity-provider/protocol bad debt;
- missed repairs or deleveraging opportunities;
- liquidity deterioration;
- execution concentration after recovery;
- false alarms and operational intervention cost;
- service/review cost.

A delayed policy is not “safer” by definition.

## Arbitrum comparison set for future evaluation

Subject to client approval and exact protocol mechanics, compare under the same trajectories:

1. current client policy;
2. validation of data integrity only;
3. the client's configured fixed grace/recovery rule;
4. the proposed conditioned recovery review.

Any dynamic grace or rate-limiting policy remains experimental until separately specified and tested.

---

# C. Parameters that must be frozen before evaluation

No values are invented in Gate 0 merely to make the charter look complete.

| Parameter | Freeze rule |
|---|---|
| network/protocol/markets | define before evaluation labels are constructed |
| eligible event population | define inclusion/exclusion criteria in advance |
| threat-class label rules | one definition per class/network; versioned |
| minimum useful precision | set from cost of false alert/review burden |
| minimum useful recall/sensitivity | set per class with positive-case denominator |
| minimum useful coverage | include non-evaluable proportion explicitly |
| oracle freshness/quality/divergence | per feed + market + client policy, not universal |
| prospective time margin | based on real evidence availability + client reaction channel |
| minimum economic effect | must exceed service/change cost plus client-required margin |
| sample size / information target | based on prevalence, dependence and minimum effect; not arbitrary N |
| uncertainty method | defined before result inspection where practicable |
| evidence budget | cap time/cost for inconclusive collection |
| termination/review date | force continue/redesign/stop decision |

## Required metrics

Report by network and threat class, not only in aggregate:

- precision with uncertainty;
- recall/sensitivity with uncertainty;
- eligible-population coverage;
- non-evaluable fraction;
- false-positive and false-negative definitions/counts with correct denominators;
- evidence-availability latency;
- delivery latency in shadow/pilot;
- adoption/action rate in later pilot;
- operating/review cost;
- induced harm/cost;
- economic effect with uncertainty when causally supportable.

`UNKNOWN` is not a true negative.

## Minimum future test cases

### Data/adapter
- invalid identity/source;
- unsupported provider/version;
- invalid/missing scale/decimals/exponent;
- future or incoherent timestamp;
- repeated reading mistaken for a new update;
- delayed monitor observation;
- invalid denominator/zero where a ratio requires non-zero.

### Sequence
- price update and dependent operation in the same transaction/block context;
- instruction/call ordering changes;
- omitted/reordered observation;
- finality/reorg/late-data correction where applicable.

### Solana ordering
- legitimate arbitrage;
- harmful pattern candidate;
- provenance unsupported;
- event that cannot be evaluated with available state.

### Arbitrum recovery
- isolated RPC failure;
- uninitialized/unknown sequencer-status condition;
- recovery then rapid relapse;
- price/data ready but exposure still unknown;
- positions repaired before normal resumption;
- inadequate liquidity;
- falling versus reversing market.

## Gate 0 disposition

Artifact 06 defines the product hypotheses and falsification logic but does **not** close them. The following remain pending:

- named clients/protocols;
- frozen market/feed/adapter/policy scopes;
- quantitative useful-effect thresholds;
- sample/information plans;
- evidence budgets;
- authorized reviewers;
- independent Gate approval.

Current result for both networks: **Gate 0 pending**.
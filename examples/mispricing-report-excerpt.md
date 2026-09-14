# Worked Example: The Marketing Mispricing Report (excerpt)

> **Fictional.** Northwind Outdoor, its figures, and its people do not exist. This file exists to
> show *register and evidence discipline*, not to demonstrate a result. Nothing here is a
> benchmark, a case study, or usable proof. Real engagements never reuse these numbers.
>
> **Runbook**: `strategy/runbooks/scenario-marketing-mispricing-diagnostic.md`
> **Agents shown**: Mispricing Diagnostic Lead · Availability Ledger Analyst · Measurement Bias
> Reviewer · Repricing Memo Writer · Mispricing Claim Auditor · MAXX Profit Offer Architect

---

## 1. Executive summary `[CLIENT-SAFE]`

Northwind Outdoor's marketing capital is priced for measurable harvest rather than for the
availability that produces it. Roughly a third of what the budget calls brand investment is
reaching people who have already chosen Northwind in the last 90 days. The ratio conversation
therefore starts lower than the plan assumes, before any discussion of creative.

**The mispricing thesis**

> We believe Northwind's marketing capital is mispriced toward retargeted and branded-search
> activity because a third of declared brand spend addresses buyers already in market. The binding
> constraint on category-buyer growth is mental and physical availability among light buyers, not
> conversion efficiency, which is already strong. Moving €2.1m from lower-funnel retargeting and
> branded search into broad-reach work and size-curve fulfilment should first show movement in
> unaided recall and out-of-stock rate, and then in first-time buyers. Our confidence falls if the
> branded-search line proves incremental under a holdout test, which has never been run.

**Three decisions available in 90 days**

1. Reclassify the budget by job and adopt the ratio the reclassification reveals, not the declared one.
2. Run a geo holdout on branded search before the next budget lock.
3. Fix the size-curve gap in the two products that carry recognition, ahead of any new campaign.

---

## 2. The Availability Ledger `[CLIENT-SAFE]`

Capital classified by the job it performs, not by the team that owns the line.

| Job | Declared | Reclassified | Movement | Note |
|---|---|---|---|---|
| Create (builds future demand) | €9.4m | €6.2m | −€3.2m | Retargeting and branded search moved to Capture |
| Capture (harvests existing demand) | €5.1m | €8.1m | +€3.0m | |
| Availability (found, stocked, buyable) | €1.8m | €1.9m | +€0.1m | |
| Conserve (defends what exists) | €0.9m | €0.9m | — | |
| Learn (buys knowledge) | €0.3m | €0.1m | −€0.2m | Two of three "tests" had no control group |
| Reserve (uncommitted) | €0.0m | €0.3m | +€0.3m | Underspend, not a decision |
| **Total** | **€17.5m** | **€17.5m** | | |

`[FACT]` The reclassification is arithmetic on the client's own media schedule and platform
exports, reviewed line by line with Finance and accepted on 14 March.
`[JUDGMENT]` Branded search is classified as Capture. Some share is genuinely incremental; no test
exists that can say which. Classification is stated, not hidden, so the client can contest it.

---

## 3. Module finding — Measurement Bias Review `[CLIENT-SAFE]`

**Finding.** The dashboard that governs quarterly allocation credits last-click conversions and
excludes any campaign without a click path. Every line in the Create column is therefore invisible
to the instrument used to judge it.

| | |
|---|---|
| Evidence | `[FACT]` dashboard specification and 12 months of exports; `[FACT]` three of four board KPIs are click-derived; `[INFERENCE]` the allocation shift 2023→2026 tracks the metrics' visibility, not tested return |
| Confidence | High on the mechanism, medium on the magnitude |
| Prior | `[JUDGMENT]` The IPA Databank analyses of Binet and Field shift the burden of proof toward longer-horizon effects being under-credited by short-window attribution. A prior is not a finding about Northwind. |
| Business implication | Allocation decisions are being made with an instrument that cannot see half the portfolio |
| Recommended action | Add one incrementality test per quarter, starting with branded search; report brand and activation on separate horizons |
| Data gap | No holdout, geo test, or MMM has ever been run. Requested; none exists. |

**What must be protected.** `[FACT]` Email and CRM return is genuinely strong and genuinely
measured. Nothing in this report recommends touching it.

**Recorded dissent.** The Performance Director does not accept the branded-search
reclassification. Recorded, unresolved, and testable — the geo holdout settles it either way.

---

## 4. The same finding in two registers

This is the boundary the Mispricing Claim Auditor enforces before release.

**`[INTERNAL]` — pipeline note, never sent**

> Classic Dashboard Alibi. The CMO has been buying her own alibi for three years and the CFO is
> starting to notice. Value at risk on the misallocated third is ~€3m annually, so the diagnostic
> fee is a rounding error against it — price against the misallocation, not the days. Sprint is the
> obvious next rung once the holdout lands; do not raise it before the readout.

**`[CLIENT-SAFE]` — the same substance, in the report**

> The current measurement architecture may be structurally over-crediting demand extraction, which
> makes the present allocation look rational inside the quarter. Roughly €3m of annual spend is
> exposed to that bias. A single incrementality test would resolve the largest open question at a
> cost well below the amount in question.

What changed, and why each change is mandatory:

| Internal | Client-safe | Rule |
|---|---|---|
| "Dashboard Alibi" | "the current measurement architecture" | Banned lexicon — internal module name |
| "buying her own alibi" | "makes the present allocation look rational inside the quarter" | Blame moved from a named individual to the incentive structure |
| "fee is a rounding error", "next rung" | removed | Pricing logic and ladder position never appear in a client artifact |
| "~€3m" | "roughly €3m … exposed to that bias" | Same number, stated with its basis and its uncertainty |

**Register Separation Check**

```yaml
artifact: "Mispricing Report §3 — Measurement Bias Review"
intended_register: mispriced-cmo
audience: "CMO, CFO, CEO"
banned_terms_found: []        # "Dashboard Alibi" found in draft 2, removed
tone_leakage: []              # blame framing at named individual, removed in draft 2
verdict: clear
```

---

## 5. Method note `[CLIENT-SAFE]`

Received: 4 years of spend by line, platform exports, brand tracker (2 waves), 24 months of
creative, distribution and stock data, dashboard specifications, bonus metrics.
Not received: any incrementality or holdout result, size-level sell-through before 2025, agency
fee breakdown. Absence is reported as a finding, not as a failure.

Every material claim in the full report carries `[FACT]`, `[INFERENCE]`, `[HYPOTHESIS]`, or
`[JUDGMENT]`. Claims that could not be verified were removed from the body rather than softened
into the passive voice.

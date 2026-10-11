# 🧪 Runbook: Investment Hypothesis Validation

> **Mode**: NEXUS-Sprint | **Duration**: Hypothesis-dependent | **Candidate roster**: 6 (the proposer and its validator always activate together)

---

## Scenario

Use this runbook when a macro, liquidity, cross-asset or on-chain investment idea is about to influence capital, a model, or a decision-support output. Typical cases:

- a regime or liquidity signal proposed as an input to allocation;
- a relative-value or timing rule (BTC/ETH/SOL, curve, sector) with a backtest attached;
- a legacy threshold, lag or weight that has never been validated out of sample;
- a hypothesis already in paper tracking whose live results diverge from validation.

Do **not** use it to generate trade ideas faster, to produce orders, or to size positions. No agent in this roster holds trading authority.

## Governing Doctrine

Read `strategy/GENERAL-STRATEGY-DOCTRINE.md` before the first material recommendation. A hypothesis is a causal claim under adaptive opposition; a backtest is evidence about the past, not authority over the future.

## Separation of duties (P8)

This runbook is the reference case for the proposer/challenger rule in `strategy/challenger-pairs.json`, enforced by `scripts/nexus-instance.py`:

| Role | Agent | May | May not |
|---|---|---|---|
| Proposer | Macro Regime Alpha | Write the hypothesis card, run discovery, redesign after a verdict | Validate its own hypothesis, promote past `BACKTESTED`, feed any other task before a verdict |
| Challenger | Quant Research and Alpha Validation | Audit leakage, run walk-forward and costs, attribute alpha vs beta, stress, issue the verdict | Help design or tune the hypothesis it judges |
| Decision owner | Named human | Accept or reject the verdict; override a negative verdict with reason, evidence and expiry | Rewrite the verdict, or open a gate that has no verdict |

In an instance, every proposer task needs a challenger task that depends on it and asserts `verdict:<proposer task id>` with a canonical decision state. Until that verdict is favourable (`PROCEED` or `PROCEED_WITH_CONDITIONS`) or overridden, no other task may consume the proposer's output (`CHALLENGER_PENDING`, `CHALLENGER_VETO` or `CHALLENGER_CONFLICT` blockers), the owner cannot record a favourable decision over a veto, and the instance cannot close as a success. Redesign runs as a new proposer task with its own challenger task.

## Sequence

1. **Card** — the proposer writes the hypothesis card: mechanism, information edge, priced expectation, instrument, horizon, trigger, falsifier, benchmark, costs, risk constraints. Benchmark fixed now.
2. **Freeze** — dataset snapshot, code revision and full trial ledger are frozen and handed over.
3. **Validate** — the challenger audits leakage, runs purged walk-forward against simple and beta-matched baselines, applies the cost model at the proposed size, deflates for the trial count, and stress-tests against the owner's constraints.
4. **Verdict** — the challenger records the decision state with fatal defects, accepted risks and pending information separated.
5. **Decision** — the owner records promotion, paper tracking, redesign or retirement; any override names its reason, evidence and expiry.
6. **Paper track** — timestamped paper decisions before outcomes are known; divergence from validation reopens the hypothesis.

## Roster

| Group | Agents | Activation |
|---|---|---|
| Proposal and Validation | Strategic Assurance Lead, Macro Regime Alpha, Quant Research and Alpha Validation | Always |
| Decision Support | Investment Researcher, Market Data & Research Integrity, On-Chain Capital Flows & Market Structure, Protocol Fundamentals & Token Value Capture, Catalyst & Expectations Analyst, Investment Thesis Challenger, Portfolio Risk & Allocation Architect, Strategic Red Team, Legal Compliance Checker | Activate only for material data, chain flow, fundamentals, event, independent challenge, mandate-risk or legal dependencies. No execution. |

## Boundary

This roster is excluded from the HTP Gate 0 runbook (`excluded_runbooks` in the pair registry, checked in CI). Investment-thesis work never feeds detection, policy or pause decisions in a harm-reduction programme.

## Termination

Close when every submitted hypothesis has a recorded verdict and the owner's resulting decision with falsifiers and a review date. Terminate as `REJECT` or `REDESIGN` when leakage, cost or out-of-sample results are fatal. An expired override returns the hypothesis to the validator.

## Optional Alpha Research Suite handoffs

The [Alpha Research Suite operating contract](../alpha-research-suite/README.md) governs versioned handoffs, as-of cutoffs, corrections, abstention and the separation of suite statuses from canonical NEXUS states.

1. Market Data & Research Integrity supplies point-in-time, versioned records. `QUARANTINED` critical inputs block the affected research use.
2. Macro frames the hypothesis; On-Chain, Fundamentals and Catalyst provide supporting evidence only when material. None can approve the hypothesis it helped create.
3. Quant independently validates Macro and records the **mandatory P8 verdict**. Investment Thesis Challenger may separately examine causal premises, alternatives and coherence; its `PASS_TO_NEXT_REVIEW` never overrides Quant.
4. Portfolio Risk reviews exposures only against a user-confirmed mandate; missing holdings, loss limits or leverage constraints block individualized sizing. Hypothetical scenarios must be labelled.
5. The human owner receives evidence, alternatives (including no action), risk findings, unresolved conditions and review triggers. No agent gains transaction-signing, order placement, custody or autonomous capital authority.

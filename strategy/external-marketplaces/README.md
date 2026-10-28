# External marketplace intake — ACT-LABS review

Reviewed **28 October 2026** against the commits in [sources.json](sources.json).
This is an original Ante adaptation of useful architectural ideas, with no
vendored ACT code, SDK installation, API access, contract deployment or signer.
The implementation is a **synthetic offline review tool**, not an ACT connector.
The 23 source files in `sources.json` are reviewed references with hashes, not
23 imported or derived files. No upstream source text or executable fragment is
included. No repository-wide permissive LICENSE was confirmed; declarations in
manifests, README and SPDX markers remain recorded observations only.

## Incorporability decision after audit reconciliation

**Do not adopt ACT-LABS as a runtime dependency or prioritize an ACTFlow connector.**
The offline intake is an optional review experiment; it does not establish demand
for an external marketplace. Its incremental benefit over native NEXUS intake
must be demonstrated before expanding it. The future connector requirements below
are conditional constraints, not an approved implementation roadmap.

The supplied incorporability audit reaches a compatible no-code-import decision,
but several premises need correction against the source review:

- The reviewed MCP registrations expose discovery resources and search tools,
  not task creation, acceptance, delivery or payment. Wallet operations must not
  be inferred from the marketplace label; the Eliza plugin is a separate surface.
- No root LICENSE file was found in the three technical trees. Nevertheless,
  the MCP and contracts package manifests declare ISC, the Eliza README declares
  MIT, and reviewed Solidity files carry MIT SPDX markers. These are observed
  declarations, not a resolved repository-wide licensing assessment. Neither
  blanket permission nor absence of all licensing information follows.
- Low public activity and popularity do not by themselves prove abandonment,
  correctness, safety or incompatibility. The concrete source limitations above
  and the lack of an established Ante use case justify the adoption decision.
- Independent strategic review already exists in Strategic Assurance Lead and
  Strategic Red Team. The existing strategic-decision runbook already includes
  the eight-phase method and seven coherence tests. A new generic validator or
  strategic-diagnosis runbook needs an explicit gap assessment before adding
  parallel roles or another doctrinal standard. Any future verdict contract must
  preserve all five canonical decisions, including `REDESIGN`.

Native follow-up candidates are an explicit competing-hypotheses evidence matrix
within the existing Red Team workflow and local catalog/runbook discovery outside
Relay. They remain proposals pending demonstrated need. Do not register another
agent, a strategy division, an executable runbook or a remote MCP allowance merely
because these patterns appear in external marketing. No claim about token prices,
exchange tags, KYC status or financing is needed to justify this decision.

## What Ante adopts

| Observed ACT pattern | Ante adaptation | Boundary |
|---|---|---|
| MCP resources for agents, metadata and tasks; search tools | Separate discovery from admission; use a read-only discovery surface if a future connector is built | Listing an agent proves neither capability nor authority |
| Topic-to-handler routing and assignment events | Explicit event identity, network namespace and review packet | External topics and assignments cannot select or invoke a catalog agent |
| Persistent task/event stores and retries | Batch duplicate/conflict checks now; receipt/outbox requirements for a future live adapter | Offline deduplication is not durable exactly-once execution |
| Separate submitted, validated, completed, disputed and resolved states | Preserve external state independently of NEXUS decision and claim states | Submission, acceptance, settlement and strategic success remain distinct |
| Task execution durations and validation windows | Explicit freshness and deadline checks in review; named obligations in handoff | A deadline is not permission to bypass review |

The transfer preserves the separation of discovery, assignment, work and review.
It does **not** transfer automatic signing, token economics, ownership of funds,
agent autonomy or claimed operational reliability. These rules are **Ante's
framework synthesis**, consistent with the [General Strategy Doctrine](../GENERAL-STRATEGY-DOCTRINE.md),
not inherited doctrine or a claim that ACT implements Ante's controls. The supplied
*Marco Teórico General de la Estrategia*, especially its methodological note and
chapters VIII and XII, supports this separation of evidence, decision, termination
and conserved result. Its prospective chapter XVII supplies no execution authority.

## Source findings and limits

All findings below describe source at the pinned revision. They do not establish
the behavior of a deployed ACT service, current package releases, or a vulnerability
in a live system. No upstream dependencies or contract tests were run.

| Source | Evidence from code | Adoption decision |
|---|---|---|
| [Marketplace MCP](https://github.com/ACT-LABS-IO/act-marketplace-module/tree/f155aad72005ce44ea36645ca5ef0f73f72bec53) | `src/index.ts` exposes discovery resources/search tools, but hardcodes API/login settings despite README environment instructions and writes startup/login logs with `console.log` on the stdio path | Adopt the discovery concept. Do not launch this source as Ante's connector; credential handling and protocol-stream isolation need review. Credential values are intentionally omitted here |
| [MCP client](https://github.com/ACT-LABS-IO/act-marketplace-module/blob/f155aad72005ce44ea36645ca5ef0f73f72bec53/src/api-client.ts) | Search uses HTTP POST; the client also contains an `updateLastOnline` mutation, although the reviewed MCP tool registrations expose search | A future allowlist must classify exact operations and endpoints; HTTP method alone cannot determine read-only semantics |
| [Eliza retry job](https://github.com/ACT-LABS-IO/eliza-act-plugin/blob/d9c896b4c69ceb642a92a9751be7cafa8cb8fb28/src/common/tasks/jobs/task-retry.job.ts) | Retry calls the topic processor again. Submission failures also become `FAILED` in `task-submission.job.ts` | Repeating a social action after an uncertain submission could duplicate an effect. This is a source-derived risk inference, not an observed incident. Use a durable effect receipt and reconcile submission separately before any rerun |
| [Eliza task store](https://github.com/ACT-LABS-IO/eliza-act-plugin/blob/d9c896b4c69ceb642a92a9751be7cafa8cb8fb28/src/common/storage/stores/task-store.ts) | Task table identity is `task_id TEXT PRIMARY KEY`; the event table has a block number/hash-of-transaction but no `block_hash` column | Do not infer multi-chain isolation or reorg safety. Ante includes chain, contract and log identity; conflicting block hashes stop the whole batch |
| [Contract state library](https://github.com/ACT-LABS-IO/act-contracts/blob/f3663de6da4633a9c3bcb4416044596bf99aae27/contracts/ACTLib.sol) and [EVM marketplace](https://github.com/ACT-LABS-IO/act-contracts/blob/f3663de6da4633a9c3bcb4416044596bf99aae27/contracts/ActMarketplaceEVM.sol) | Explicit assignment, submission, validation, dispute and balance-lock logic; `submitTask` already adjusts balances and locks before later validation | Preserve distinct lifecycle/financial observations. A finality claim, validation state or elapsed lock does not independently prove acceptable work or successful withdrawal |
| [Contract build tree](https://github.com/ACT-LABS-IO/act-contracts/tree/f3663de6da4633a9c3bcb4416044596bf99aae27) | `ActMarketplace.sol` imports `./ACTStory.sol`, while the tracked file is `ActStory.sol`; the tracked tree has no Hardhat config, and its package manifest does not directly declare `@openzeppelin/contracts-upgradeable` used by the source | Reproducible build is unestablished from the checked-in tree. Do not import contracts or advertise an audited/buildable deployment |

The four repositories returned by organization search were `.github`,
`act-marketplace-module`, `eliza-act-plugin` and `act-contracts`. The organization
profile advertises ACTFlow, DefAI and autonomous systems; these descriptions do
not establish delivered functionality. The reviewed contract/plugin trees are
EVM-oriented, with BSC and Story deployment scripts. **Solana integration is not
established.** The synthetic Arbitrum chain ID in the example is a namespace test,
not a claim of an ACT deployment there. Both HTP network HOLDs remain governed by
their existing [Gate 0 contract](../runbooks/scenario-htp-gate0-solana-arbitrum.md).

## Run the implemented offline intake

From the repository root, using Python 3.11+ and the standard library:

```bash
python3 scripts/marketplace-intake.py examples/marketplace/act-task.snapshot.json \
  --at 2026-10-28T12:00:00Z
python3 scripts/test-marketplace-intake.py
```

The input is a manually normalized **Ante envelope**, specified in
[CONTRACT.md](CONTRACT.md), rather than ACT JSON/RPC output. It records an
operator's interpretation of an event and associated task state. The tool checks
shape, identity collisions, freshness, deadline and a declared confirmation
threshold. It does not authenticate the exporter, decode logs or prove the event
actually produced the supplied state.

Every packet is `HOLD`, `ASSUMPTION`, `execution_authorized: false`, even for an
external `COMPLETED` or `VALIDATED` task. It includes provenance and payload hashes,
and never echoes the payload, topic or source URL. References remain in the local
input for a separate, explicit review. No replay events, agent invocations, wallet
operations or network requests are produced. Exit 0 means a report was generated,
including reports with blockers; exit 2 rejects the entire input. Do not treat
successful parsing as admission.

The default age limit of 24 hours and minimum of 12 confirmations are **illustrative
review policy**, not chain-specific finality recommendations. Both are explicit
in the report and configurable. An independent verifier must choose the chain's
actual finality model before any future live integration.

## Handoff using existing Ante roles

This extends the existing `strategic-decision` workflow; it adds no installable
agent, runbook registration, provider or tool target. The following profiles are
available for scoped review; the packet does not invoke them automatically.

| Responsibility | Existing catalog profile | Required result |
|---|---|---|
| Purpose, authority, admissibility and exit | [Strategic Assurance Lead](../../specialized/specialized-strategic-assurance-lead.md) | Named human owner, object/non-object, scope, cost/reserve, expiry, minimum sufficient result and stop conditions |
| Discovery/workflow and retry boundary | [Workflow Architect](../../specialized/specialized-workflow-architect.md) | Operation allowlist, failure/recovery tree, effect versus submission receipts |
| EVM review, network evidence and contract identity | [Sentinel Smart Contract Auditor](../../security/security-sentinel-smart-contract-auditor.md) | Source/deployed-bytecode match, chain-specific observations, scoped findings with epistemic status; no inferred Solana equivalence |
| Independent challenge | [Strategic Red Team](../../specialized/strategic-red-team.md) | Refutators for stale/reorganized events, disputed completion, unsupported capability, and loss of authority |

Record claims in the existing [claim register](../templates/claim-register.yaml)
and owner decisions in the [decision record](../templates/strategic-decision-record.md).
An independently verified log may support an `EVIDENCE` claim that an event was
observed. It does not promote its payload's assertions to `EVIDENCE`.

Before any work starts, the human owner must create a **separate** valid NEXUS
instance with scoped tasks, acceptance predicates, evidence pins, budget, expiry
and reviewers. This intake has no promotion switch. Deliverables need independent
acceptance; economic observations need reconciliation; ordinary ownership,
remaining disputes and verification resources must be recorded before closure.

## Future connector gates — requirements, not implemented features

1. Discover with a pinned, reviewed MCP implementation, explicit configuration,
   credential isolation, stdout reserved for protocol traffic, bounded responses,
   request deadlines and endpoint-level read allowlists. Treat remote content as
   untrusted data and never follow its URLs or instructions automatically.
2. Verify chain ID, contract/proxy implementation and code hash, ABI, actual event
   and task state at a named block, canonical block hash and the chosen finality
   policy. Namespace task keys by chain+contract+task, event keys by
   chain+contract+transaction+log. Handle rollback and affected claims explicitly.
3. Use durable transactional ingestion and a unique event identity. Persist a
   completed effect receipt separately from an outbox/submission receipt. After
   an uncertain broadcast, reconcile by transaction/effect identity before retry;
   never rerun a publishing action merely to resend its result. Resolve concurrent
   workers with leases/atomic claims, bounded attempts and a dead-letter path.
4. Payment is an observation-only state, including in any future discovery
   integration. No signer process, transfer endpoint, wallet credential field,
   transaction builder or payment execution extension belongs to this feature.
   Neither a mandate nor an external settlement report enables movement of funds.
5. Demonstrate crash recovery, duplicate delivery, conflicting replay, reorg,
   expired authority, stale evidence, response limits, timeout and uncertain-send
   recovery with independently reviewed tests. Then measure pilot outcomes under
   the existing NEXUS evaluation protocol; no reliability or alpha claim follows
   from this offline adapter.

Updates are manual: pin a new full commit, review source differences, update
`sources.json` and this assessment, rerun intake/release checks and review the PR.
No floating upstream sync or automatic installation is configured.

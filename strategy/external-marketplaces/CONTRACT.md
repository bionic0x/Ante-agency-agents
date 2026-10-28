# Offline marketplace review envelope v1

`scripts/marketplace-intake.py` consumes one UTF-8 JSON file with exactly
`schema_version: 1` and `observations: [...]` (1–1000 records, at most 1 MiB).
Unknown fields and duplicate JSON object keys fail closed. Store credentials
elsewhere; the envelope has no credential, executable instruction or owner mandate
field. It does not detect secrets embedded in free text. Keep inputs private if
their contents are sensitive. The checked-in example contains synthetic data only.

Each observation has exactly these fields:

| Field | Contract |
|---|---|
| `chain` | Canonical `eip155:<positive decimal>`; 1–20 decimal digits. Other namespaces require a separate version and verifier |
| `contract` | Nonzero 20-byte `0x` hex address; normalized to lowercase for identity, not an EIP-55 checksum verification |
| `task_id` | Canonical decimal **string**, `0 <= id < 2^96`; never a floating-point number |
| `event` | Exactly `transaction_hash`, `log_index`, `block_number`, `block_hash`, `removed`, `confirmations` |
| `event.transaction_hash`, `event.block_hash` | Nonzero 32-byte `0x` hex; normalized to lowercase |
| `event.log_index`, `event.block_number`, `event.confirmations` | Nonnegative JSON integers; booleans and fractional values rejected |
| `event.removed` | JSON boolean; `true` adds a reconciliation blocker |
| `observed_at`, `deadline` | ISO timestamps with explicit timezone; normalized to UTC. Deadline is the operator-recorded relevant review/execution cutoff, not decoded contract logic |
| `source_ref` | Nonempty text, at most 1024 characters; retained only in input, never fetched |
| `external_state` | One exact state from the table below; an operator assertion about state associated with this observation |
| `payment_state` | Exactly `NOT_OBSERVED`, `PENDING_REPORTED`, `SETTLED_REPORTED` or `DISPUTED_REPORTED`; unverified observation, never derived from task completion |
| `topic` | Nonempty text, at most 128 characters; no mapping to an executable handler |
| `payload` | Nonempty text, at most 65536 characters; hashed as UTF-8, never copied into report or prompt |

Different task lifecycle observations may share a task key; each must have a
different event identity. The tool emits separate review records and does not
project a current task state from event order. A raw event that lacks a task ID
or independently interpretable task state needs operator reconciliation before
it can be represented here. Unknown/malformed data is rejected, not synthesized.

## External states are observations, not verdicts

| External state | Report meaning |
|---|---|
| `PENDING` | `unassigned` |
| `INVITED` | `invitation_reported` |
| `ASSIGNED` | `assignment_reported` |
| `SUBMITTED` | `delivery_reported` |
| `COMPLETED` | `client_acceptance_reported` |
| `VALIDATED` | `validator_acceptance_reported` |
| `DELETED` | `deletion_reported` |
| `DECLINED_BY_OWNER`, `DECLINED_BY_VALIDATOR` | `rejection_reported` |
| `DISPUTED_BY_OWNER`, `DISPUTED_BY_AGENT` | `dispute_reported` |
| `RESOLVED` | `resolution_reported` |

These meanings do not replace the five canonical claim states or NEXUS decision
states. Every output decision remains `HOLD`, with claim status `ASSUMPTION` and
execution disabled. `NOT_AN_ASSIGNED_TASK` marks every other state for lifecycle
review; it does not imply that any external assignment is authorized internally.

## Identity, duplicates, provenance and time

- Task key: `chain:lowercase-contract:task_id`.
- Event key: `chain:lowercase-contract:lowercase-transaction_hash:log_index`.
- Within a batch, identical normalized records sharing an event key produce one
  packet and increment `duplicate_count`. Any different content for that key,
  including block hash, observed time, confirmations or payload, rejects the
  **whole batch**. Reconcile observations explicitly rather than overwriting them.
- This is not a durable inbox, global replay ledger, event database, finality
  verifier or current-state projector. Repeated invocations independently produce
  the same report. A later snapshot is a new review, not a promotion or side effect.
- `--at` is mandatory for reproducibility. Age equal to the configured maximum is
  stale; a deadline equal to the clock has been reached. Future observations,
  removed logs and insufficient declared confirmations add blockers.
- `input_sha256` hashes parsed input serialized with sorted keys, compact
  separators and ASCII escapes. `observation_sha256` hashes the same serialization
  after address/hash/time normalization; `payload_sha256` hashes exact payload
  UTF-8. These fingerprints support comparison, not authenticity. Input array
  order affects the input hash; packet ordering is deterministic by event key.
- Original input is never modified. Reports go only to stdout. Invalid input emits
  a fixed stderr message and exit 2 without echoing attacker-controlled data.
  Exit 0 means report generation, including blocked observations.

Only the schema, collision behavior and review flags are enforced. No source
authenticity, actual confirmation count, mandate, acceptance, settlement, runtime
permissions or claim truth is established by this tool.

## Payment boundary

Every packet preserves `payment_state` and sets `payment_authorized: false`.
No state, including `SETTLED_REPORTED`, verifies actual settlement or authorizes
fund movement. This boundary also applies to any future discovery adapter: no
signer, wallet credential, transfer endpoint or transaction builder is planned
or accepted under this feature. Human review records an assessment only.

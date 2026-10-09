# NEXUS Relay: design and threat model

NEXUS Relay is the execution layer that NEXUS deliberately does not have. It lets a small
group of trusted people work with catalog agents in a shared room, while every agent run
is admitted by the NEXUS contract engine, executed in an isolated container on the
owner's machine, and recorded as a replayable NEXUS event.

Status: v1, local-only. One relay process serves one owner and one machine.

## Goals

1. **Admission by contract.** No agent runs unless `scripts/nexus-instance.py` accepts the
   corresponding `start` event: mandate not expired, decision state allows work, no HOLD on
   the task, dependencies satisfied, attempt and cost budgets available, no overlapping
   resource scope. The relay never re-implements these rules.
2. **Isolation by default.** Each run gets a fresh container with no network, no host
   credentials, a read-only root filesystem and a single writable workspace.
3. **Human authority.** People request runs; only the mandate owner starts them and accepts
   or rejects their results. Acceptance requires every acceptance predicate to be confirmed.
4. **Evidence.** Every room message, approval and run is written to an append-only,
   hash-chained log, and the NEXUS events file replays with the existing CLI.

## Non-goals (v1)

- No cloud service, no multi-machine fleet, no public internet exposure.
- No email, chat-platform or webhook ingress. The only ingress is the authenticated room.
- No autonomous or scheduled runs. Every run starts from an owner approval.
- No claim revisions, holds or decision changes from the UI. Those remain owner edits
  through the existing NEXUS tooling; the relay reads them through replay.

## Trust boundaries

```text
 Browser (member)                     Owner machine
 ───────────────┐    loopback / TLS   ┌──────────────────────────────────────────┐
 room UI        │ ──────────────────▶ │ relay HTTP server (127.0.0.1 only)       │
 (untrusted     │   session cookie    │   auth · rooms · approvals · review      │
  input)        │                     │   NEXUS admission (apply/replay)         │
 ───────────────┘                     │   event log (hash chain, SQLite)         │
                                      │        │ unix socket (per run)           │
                                      │        ▼                                 │
                                      │   model proxy ── HTTPS ──▶ model API     │
                                      │        ▲  key injected, cost metered     │
                                      │ ┌──────┴──────────────────────────────┐  │
                                      │ │ container (per run): --network none │  │
                                      │ │ read-only root · non-root user      │  │
                                      │ │ /workspace rw · no host secrets     │  │
                                      │ └─────────────────────────────────────┘  │
                                      └──────────────────────────────────────────┘
```

Remote members reach the relay through a tunnel that terminates TLS and forwards to
loopback, such as `tailscale serve`. The relay refuses to bind a non-loopback address.

## Threats and controls

| # | Threat | Control |
|---|---|---|
| T1 | An agent is manipulated (prompt injection in a message or file) into harming the host | Container per run: `--network none`, `--read-only`, `--cap-drop ALL`, `--security-opt no-new-privileges`, non-root UID, pids/memory/CPU limits, `--pull never`, no host home, no container-engine socket. The only writable mount is the task workspace; the proxy socket and agent profile are read-only. The relay refuses a root-owned engine unless the owner opts in (`runtime.allow_rootful_engine`), because access to such an engine is root on the host. |
| T2 | An agent exfiltrates data or calls arbitrary hosts | No network interface. The proxy forwards only `POST /v1/messages` to the configured model endpoint; every other path is refused. |
| T3 | An agent steals the model API key | The key never enters the container. The proxy adds it upstream and strips any client-supplied credential headers. |
| T4 | An agent overspends | `reserved_cost` is reserved in NEXUS at `start`. The proxy holds each request's worst case (request bytes + margin + `max_tokens`) under a lock before forwarding, lowers `max_tokens` to what remains, caps requests in flight, settles at metered usage (an incomplete response is charged its full hold) and stops the run when nothing more fits. Spent never exceeds the reservation while the upstream reports usage honestly. |
| T5 | Unauthenticated access to the room | Loopback bind; every route except login requires a session; invite tokens are 256-bit, single-use, expiring and stored only as SHA-256 hashes. |
| T6 | Session theft or CSRF | Session cookie `HttpOnly; SameSite=Strict; Path=/`, named `__Host-relay_session` with `Secure` behind TLS; tokens stored hashed; 14-day absolute and 12-hour idle lifetime; the owner can list and revoke sessions. State-changing requests also require a matching `Origin` and an `X-Relay-CSRF` header bound to the session. |
| T7 | Stored XSS in the room | Server-side length limits; the UI renders all user and agent text with `textContent` only; CSP `default-src 'none'`, `script-src 'self'`, Trusted Types enforced with no policy, `frame-ancestors 'none'`; `nosniff` on every response. |
| T8 | Privilege escalation between members | Roles are fixed per member (`owner`, `operator`, `viewer`). Only the owner approves, rejects, accepts and invites. Operators request. Viewers read. Checked server-side on every route. |
| T9 | Forged or altered history | Append-only log with `prev_hash` chaining. With `NEXUS_RELAY_CHAIN_KEY` (supplied at start, never written to disk) each entry is an HMAC, the key is pinned by fingerprint, and a log rewritten without the key, including a downgrade to plain hashes, fails `verify`. `anchor` prints the head to record off the machine; `verify --expect-head` checks it, and `verify` confirms every log hash cited in NEXUS events exists. Without a key the chain only detects careless edits. |
| T10 | Run escapes its contract | Runs are tied to one NEXUS task: its catalog agent, `resource_scope`, `cost_limit` and `attempt_limit` come from the instance file, never from the request. |
| T11 | Brute force on login | Per-IP and global attempt limits with lockout; constant-time hash comparison. |
| T12 | Secrets at rest | Config and database are created `0600` in a `0700` directory; the model key is read from an environment variable or a `0600` file and never written to the log. |
| T13 | Resource exhaustion of the relay by a container | The proxy caps connections (8), requests in flight (4), body size (8 MB) and idle time (30 s); the HTTP server caps connections (64) and header time (15 s). |
| T14 | A run outlives its limit | Three layers: the engine kill, then the client process, plus a deadline enforced inside the container by the forwarder. Stopping never blocks the caller. |
| T15 | One run plants instructions or hooks for the next | The default agent command runs Claude Code with `--bare --strict-mcp-config`, which ignores workspace settings, hooks and `CLAUDE.md`. Changes to such control files since the task's last accepted run are flagged, and acceptance requires acknowledging each by name. |
| T16 | Acceptance based on what the agent claims rather than what it delivered | Each run records a workspace manifest (files hashed, symlinks never followed); its digest is part of the NEXUS `finish` evidence. A workspace above `runtime.workspace_max` fails the run. |
| T17 | Supply chain of the agent image | The reference image pins its base by digest and Claude Code by version; runs never pull; `serve` warns when the image is a mutable tag. |

Residual risk, stated plainly: a container shares the host kernel, so a kernel or runtime
escape defeats T1. A security audit of v1 and its fixes is summarised in the pull request
that introduced T13 to T17. Run the relay on a machine or VM without personal credentials, and
prefer rootless Podman or Docker with user namespaces.

## Run lifecycle and NEXUS mapping

| Step | Who | Relay record | NEXUS event |
|---|---|---|---|
| 1. Request | operator or owner | `run.requested` (task, instruction) | none |
| 2. Approve | owner | `run.approved` | `start`, issuer = owner, `reserved_cost` = remaining task budget |
| 3. Execute | relay | `run.output`, `run.completed` (cost, artifact digest) | none |
| 4. Review | owner | `run.accepted` or `run.rejected` | `finish`, issuer = owner, `actual_cost` = metered cost, `accepted`, `evidence_refs` = artifact digest, `predicate_results` |

If NEXUS refuses the `start` event, the approval fails with the engine's own reason (for
example `task blocked: HOLD:C-2` or `reserve boundary exceeded`) and nothing executes. A
run that crashes or times out is recorded as completed with an error and still needs a
`finish` so its actual cost is reconciled, as the engine requires.

The instance must declare `mandate.scope` = `local-relay`. Offline tooling continues to
accept `offline-analysis`; the relay refuses to execute any other scope.

## Components

| Module | Responsibility |
|---|---|
| `config.py` | Strict config loading and validation; refuses unsafe values |
| `store.py` | SQLite schema, hash-chained event log, members, invites, sessions |
| `auth.py` | Token generation and hashing, sessions, CSRF, rate limiting |
| `nexus.py` | Loads the instance and events; admits `start`/`finish` through the engine; atomic append |
| `runner.py` | Builds the hardened container command; runs and stops containers |
| `proxy.py` | Per-run unix-socket model proxy: path allowlist, key injection, worst-case holds, metering, budget stop, resource caps |
| `evidence.py` | Workspace manifest and control-file change detection |
| `server.py` | HTTP routes, security headers, log polling endpoint |
| `static/` | Room UI (no inline code) |
| `cli.py` | `init`, `invite`, `serve`, `verify`, `anchor` |

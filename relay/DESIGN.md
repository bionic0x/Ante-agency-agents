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
| T1 | An agent is manipulated (prompt injection in a message or file) into harming the host | Container per run: `--network none`, `--read-only`, `--cap-drop ALL`, `--security-opt no-new-privileges`, non-root UID, pids/memory/CPU limits, no host home, no container-engine socket. The only mount besides the workspace is the run's proxy socket. |
| T2 | An agent exfiltrates data or calls arbitrary hosts | No network interface. The proxy forwards only `POST /v1/messages` to the configured model endpoint; every other path is refused. |
| T3 | An agent steals the model API key | The key never enters the container. The proxy adds it upstream and strips any client-supplied credential headers. |
| T4 | An agent overspends | `reserved_cost` is reserved in NEXUS at `start`; the proxy refuses requests once metered cost reaches the reservation, and the run is stopped. |
| T5 | Unauthenticated access to the room | Loopback bind; every route except login requires a session; invite tokens are 256-bit, single-use, expiring and stored only as SHA-256 hashes. |
| T6 | Session theft or CSRF | Session cookie `HttpOnly; SameSite=Strict; Path=/` (`Secure` when served behind TLS); tokens stored hashed; state-changing requests also require a matching `Origin` and an `X-Relay-CSRF` header bound to the session. |
| T7 | Stored XSS in the room | Server-side length limits; the UI renders all user and agent text with `textContent` only; CSP `default-src 'self'`, no inline script or style, `frame-ancestors 'none'`; `nosniff` on every response. |
| T8 | Privilege escalation between members | Roles are fixed per member (`owner`, `operator`, `viewer`). Only the owner approves, rejects, accepts and invites. Operators request. Viewers read. Checked server-side on every route. |
| T9 | Forged or altered history | Append-only log with `prev_hash` chaining; `nexus-relay verify` recomputes the chain and replays the NEXUS events file through the unmodified engine. |
| T10 | Run escapes its contract | Runs are tied to one NEXUS task: its catalog agent, `resource_scope`, `cost_limit` and `attempt_limit` come from the instance file, never from the request. |
| T11 | Brute force on login | Per-IP and global attempt limits with lockout; constant-time hash comparison. |
| T12 | Secrets at rest | Config and database are created `0600` in a `0700` directory; the model key is read from an environment variable or a `0600` file and never written to the log. |

Residual risk, stated plainly: a container shares the host kernel, so a kernel or runtime
escape defeats T1. Run the relay on a machine or VM without personal credentials, and
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
| `proxy.py` | Per-run unix-socket model proxy: path allowlist, key injection, metering, budget stop |
| `server.py` | HTTP routes, security headers, log polling endpoint |
| `static/` | Room UI (no inline code) |
| `cli.py` | `init`, `invite`, `serve`, `verify` |

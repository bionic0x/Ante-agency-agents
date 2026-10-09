# NEXUS Relay

Run catalog agents for a small, trusted group, on your own machine, under a NEXUS contract.

People join a room with a single-use invite link and request agent runs against tasks in a
NEXUS instance. The owner approves each run. NEXUS decides whether it may start (mandate,
HOLDs, dependencies, attempt and cost budgets). The agent runs in a fresh container with
no network and never sees your API key. The owner then accepts or rejects the result, and
that decision becomes a replayable NEXUS `finish` event.

Read [DESIGN.md](DESIGN.md) for the threat model and what each control defends against.

For single-operator, read-only analysis, [`scripts/nexus-pilot.py`](../scripts/nexus-pilot.py)
remains the simpler path. The relay is for shared rooms and agents that need tools.

## Requirements

- Linux or macOS, Python 3.10+, standard library only.
- Rootless Podman. `serve` checks how the engine runs and refuses a root-owned engine,
  because any account that can use it is root on the host. Rootful Docker or Podman works
  only if you accept that explicitly with `runtime.allow_rootful_engine: true`. Rootless
  Docker is not supported (the proxy socket is unreachable across its uid mapping).
- An agent image with `python3` and your agent CLI. [`container/Dockerfile`](container/Dockerfile)
  builds one with Claude Code.
- A model API key in an environment variable (default `ANTHROPIC_API_KEY`).
- For remote members, a TLS tunnel to loopback, such as `tailscale serve`.

Never run the relay as root, and run it on a machine or VM without personal credentials:
containers share the host kernel.

## Quick start

```bash
podman build -t ante-relay-agent:latest relay/container

# 1. An instance with mandate.scope "local-relay" and budget.unit matching the meter ("tokens")
cp relay/examples/relay-pilot.instance.json ~/my-decision.instance.json   # then edit it

# 2. Initialise; prints the owner's single-use sign-in link
python3 scripts/nexus-relay.py init \
  --instance ~/my-decision.instance.json --events ~/my-decision.events.jsonl \
  --engine podman --image ante-relay-agent:latest

# 3. Serve (loopback only). The chain key makes the room log rewrite-proof; keep it in a
#    secret manager, not on this disk. Set it before `init` to key the log from the start.
export ANTHROPIC_API_KEY=...
export NEXUS_RELAY_CHAIN_KEY="$(your-secret-manager get relay-chain-key)"   # 32+ bytes
python3 scripts/nexus-relay.py serve

# 4. Optional: let tailnet members in over TLS, then set public_origin in relay.json
tailscale serve --bg 8770
```

The owner account is named after `mandate.owner` in the instance; only that account can
approve and review. Invite operators (may request runs) and viewers (read only) from the
Members panel. A lost session needs a new link: `python3 scripts/nexus-relay.py invite <name>`.

## Configuration

`~/.ante-relay/relay.json` (directory `0700`, file `0600`; the relay refuses looser
permissions). Unknown keys are errors.

| Key | Meaning |
|---|---|
| `instance`, `events` | NEXUS instance and its events JSONL |
| `bind` | Loopback host and port; any other address is refused |
| `public_origin` | Origin the browser uses; plain `http` only for loopback |
| `runtime.engine`, `runtime.image` | `podman` or `docker`, and the agent image |
| `runtime.agent_command` | Command run in the container; the instruction arrives on stdin and the catalog profile at `$AGENT_PROFILE` |
| `runtime.memory`, `cpus`, `pids`, `timeout_seconds` | Per-run limits |
| `runtime.workspace_max` | Largest workspace a run may leave (default `10g`); larger runs fail. Put workspaces on a volume with a quota to also stop the disk filling during a run |
| `runtime.allow_rootful_engine` | `false` by default; see Requirements |
| `model.upstream`, `api_key_env` | Model API origin (https) and the variable holding the key |
| `model.cost_unit`, `prices` | `tokens`, or `usd` with per-model prices per million tokens; must equal the instance `budget.unit` |
| `model.extra_request_fields` | Request fields to forward beyond the built-in allowlist (for a newer API option). `mcp_servers`, `container`, `service_tier`, `speed` and `inference_geo` cannot be enabled |

## Verify

```bash
python3 scripts/nexus-relay.py anchor                     # print SEQ:HASH; record it off this machine
python3 scripts/nexus-relay.py verify --expect-head SEQ:HASH   # chain, anchors, NEXUS replay and citations
python3 scripts/nexus-instance.py replay <instance> --events <events> --output /tmp/state.json
```

`verify` also re-hashes archived `output.txt` and `manifest.json` files against the digests
in each run's chained `run.completed` entry, reports a `runs` row that disagrees with that
entry or a NEXUS finish that cites other digests, and reports a
NEXUS finish whose acceptance/rejection was not persisted in SQLite. Acceptance checks
the archived evidence again; a missing, changed or incomplete artifact must be rejected.
This verifies the recorded manifest, not an immutable copy of every delivered file:
task workspaces remain shared by retries. An interrupted review requires reconciliation;
the verifier detects it but does not invent a review note or retry the finish event.

## Tests

```bash
python3 -m unittest discover -s relay/tests               # unit and HTTP tests
RELAY_E2E=1 RELAY_E2E_ENGINE=podman python3 relay/tests/e2e_container.py   # real container escape probe
```

Pin `runtime.image` by digest (`name@sha256:...`); runs never pull, and `serve` warns
about mutable tags. When a run changes files that steer later agent sessions
(`.claude/`, `CLAUDE.md`, hooks, MCP or CI config), the owner must acknowledge each one
before accepting it.

## Limits

- Spend is held at the worst case before each request: request bytes count as input tokens
  (an upper bound for text) plus a 4,096-token margin, plus `max_tokens`. Near the end of a
  reservation this refuses requests that might still have fit; that is deliberate.
- At proxy shutdown, unfinished requests are charged their full holds before the run's
  cost is recorded. Late responses cannot reduce or double-charge that final amount.
- Workspace evidence is capped at 50,000 entries and 2 GiB of hashed data. Reaching a
  limit with unscanned data, or failing to read a file/subtree, makes the run ineligible
  for acceptance, even if `workspace_max` is higher. The size check is post-run;
  a filesystem quota is still needed for a hard disk-use limit during execution.
- The model API is used as a text model only. Requests that make the provider act on the
  network or read account data (remote MCP servers, web search/fetch, code execution, URL or
  Files-API sources, containers) or change the price (`service_tier`, `speed`,
  `inference_geo`) are refused with 403. Agents that need such tools must run them in the
  container, where `--network none` applies.
- Behind a tunnel every client appears as `127.0.0.1`, so the join rate limit is shared.
- Holds, claim revisions and decisions are made with the existing NEXUS tooling, not the UI.

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
- Podman (rootless, recommended) or Docker. Rootless Docker is not supported: the model
  proxy socket must be reachable by the container user, which runs as your own uid.
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

# 3. Serve (loopback only)
export ANTHROPIC_API_KEY=...
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
| `model.upstream`, `api_key_env` | Model API origin (https) and the variable holding the key |
| `model.cost_unit`, `prices` | `tokens`, or `usd` with per-model prices per million tokens; must equal the instance `budget.unit` |

## Verify

```bash
python3 scripts/nexus-relay.py verify                     # log chain + NEXUS replay + run/event consistency
python3 scripts/nexus-instance.py replay <instance> --events <events> --output /tmp/state.json
```

## Tests

```bash
python3 -m unittest discover -s relay/tests               # unit and HTTP tests
RELAY_E2E=1 RELAY_E2E_ENGINE=podman python3 relay/tests/e2e_container.py   # real container escape probe
```

## Limits

- A run can overshoot its reservation by at most one model response: the proxy checks the
  budget before each request and stops the container once it is spent. Size `cost_limit`
  with that margin.
- Behind a tunnel every client appears as `127.0.0.1`, so the join rate limit is shared.
- Holds, claim revisions and decisions are made with the existing NEXUS tooling, not the UI.

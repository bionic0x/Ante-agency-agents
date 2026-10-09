"""Crash recovery between NEXUS and SQLite (the `reconcile` command).

The relay writes each decision to two stores: the NEXUS events file (authoritative for
the contract) and SQLite (the room's state and hash-chained log). A crash between the two
writes leaves them disagreeing. Two windows exist in the code:

* approve: NEXUS `start` appended, process dies before the run is marked running. Also any
  run still approved or running when the relay stopped. `serve` repairs these at startup
  (`Relay.recover`); `reconcile` does the same offline.
* review: NEXUS `finish` appended, process dies before the run is marked accepted or
  rejected. A retried review is refused by NEXUS (the finish already exists), so the run
  is stuck. `reconcile` projects the NEXUS finish into SQLite, but only after checking it
  against the run's chained `run.completed` entry: same owner, cost and evidence digests.

Anything else `verify` reports is not a crash window the relay can produce, so it is
listed for a person to investigate and never changed automatically. The review note of an
interrupted review is lost; it is recorded as absent, never invented.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import evidence
from .store import ChainError

INTERRUPTED = ("approved", "running")


@dataclass
class Plan:
    recover: list[str] = field(default_factory=list)            # run ids left approved/running
    project: list[tuple[str, dict]] = field(default_factory=list)  # (run id, NEXUS finish event)
    manual: list[str] = field(default_factory=list)             # descriptions; never auto-fixed

    @property
    def empty(self) -> bool:
        return not (self.recover or self.project)


def _cited(refs, prefix: str) -> set[str]:
    return {r.split(":", 2)[2] for r in refs or [] if isinstance(r, str) and r.startswith(prefix + ":sha256:")}


def finish_problems(store, row, logged: dict, finish: dict, owner: str) -> list[str]:
    """Why a NEXUS finish must not be projected onto this run, if at all."""
    problems = evidence.record_problems(row, logged)
    if finish.get("issuer") != owner:
        problems.append(f"finish issuer {finish.get('issuer')!r} is not the mandate owner {owner!r}")
    if finish.get("task_id") != row["task_id"]:
        problems.append("finish names a different task")
    if type(finish.get("accepted")) is not bool:
        problems.append("finish has no accepted/rejected decision")
    try:
        if float(finish.get("actual_cost")) != float(logged.get("actual_cost") or 0):
            problems.append("finish cost differs from the chained run.completed entry")
    except (TypeError, ValueError):
        problems.append("finish cost is not a number")
    refs = finish.get("evidence_refs") or []
    for prefix, key in (("relay-output", "artifact_digest"), ("relay-workspace", "workspace_digest")):
        if _cited(refs, prefix) != ({logged[key]} if logged.get(key) else set()):
            problems.append(f"finish cites a {prefix} digest that differs from the chained run.completed entry")
    log_refs = _cited(refs, "relay-log")
    if len(log_refs) != 1 or not store.has_hash(next(iter(log_refs))):
        problems.append("finish does not cite exactly one log entry that is in the chain")
    return problems


def plan(store, contract) -> Plan:
    """Read-only: what reconcile would do, and what needs a person."""
    result = Plan()
    events = contract.events()
    owner = contract.owner()
    starts = {e.get("id") for e in events if e.get("type") == "start"}
    finishes = {e.get("id"): e for e in events if e.get("type") == "finish"}
    for row in store.query("SELECT * FROM runs ORDER BY created_at"):
        run_id, state = row["id"], row["state"]
        started = f"relay-{run_id}-start" in starts
        finish = finishes.get(f"relay-{run_id}-finish")
        if state in INTERRUPTED:
            if finish is not None:
                result.manual.append(f"run {run_id} is {state} but NEXUS already has its finish")
            else:
                result.recover.append(run_id)
        elif state == "completed" and finish is not None:
            try:
                logged = store.run_completion(run_id)
            except ChainError as exc:
                result.manual.append(f"run {run_id}: interrupted review, but its completion entry failed: {exc}")
                continue
            if logged is None:
                result.manual.append(f"run {run_id}: interrupted review, but no run.completed entry in the log")
                continue
            problems = finish_problems(store, row, logged, finish, owner)
            if problems:
                result.manual.append(f"run {run_id}: interrupted review, NEXUS finish not projected: "
                                     + "; ".join(problems))
            else:
                result.project.append((run_id, finish))
        elif state in ("accepted", "rejected"):
            if finish is None:
                result.manual.append(f"run {run_id} is {state} but has no NEXUS finish event")
            elif finish.get("accepted") is not (state == "accepted"):
                result.manual.append(f"run {run_id} is {state} but its NEXUS finish says the opposite")
        elif state in ("requested", "declined", "failed_to_start") and (started or finish is not None):
            result.manual.append(f"run {run_id} is {state} but NEXUS recorded events for it")
    return result


def apply(relay, result: Plan) -> list[str]:
    """Carry out a plan. The caller holds the relay lock and has verified the chain."""
    done = [f"recovered interrupted run {run_id}" for run_id in relay.recover(only=set(result.recover))]
    for run_id, finish in result.project:
        if relay.project_finish(run_id, finish):
            done.append(f"run {run_id}: recorded NEXUS finish as {'accepted' if finish['accepted'] else 'rejected'}")
    return done

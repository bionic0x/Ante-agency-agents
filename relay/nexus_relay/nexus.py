"""NEXUS admission. The relay never decides whether work may start or be accepted: it
builds the event and asks the unmodified engine (`scripts/nexus-instance.py`) to apply it
to the replayed history. Only an event the engine accepts is appended."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import runpy
import threading

from .config import REPO_ROOT

RELAY_SCOPE = "local-relay"
_ENGINE = None
_ENGINE_LOCK = threading.Lock()


class AdmissionError(RuntimeError):
    """The engine refused the event; the message is the engine's own reason."""


def engine() -> dict:
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            _ENGINE = runpy.run_path(str(REPO_ROOT / "scripts" / "nexus-instance.py"), run_name="nexus_engine")
        return _ENGINE


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class Contract:
    def __init__(self, instance_path: Path, events_path: Path):
        self.instance_path = instance_path
        self.events_path = events_path
        self._lock = threading.Lock()

    def instance(self) -> dict:
        instance = json.loads(self.instance_path.read_text())
        if instance.get("mandate", {}).get("scope") != RELAY_SCOPE:
            raise AdmissionError(f"instance mandate.scope must be {RELAY_SCOPE!r} for live execution")
        return instance

    def events(self) -> list[dict]:
        if not self.events_path.exists():
            return []
        out = []
        for number, line in enumerate(self.events_path.read_text().splitlines(), 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise AdmissionError(f"events line {number}: invalid JSON") from exc
        return out

    def state(self) -> tuple[dict, dict]:
        instance = self.instance()
        try:
            return instance, engine()["replay"](instance, self.events())
        except (ValueError, KeyError, TypeError) as exc:
            raise AdmissionError(f"replay failed: {exc}") from exc

    def owner(self) -> str:
        return self.instance()["mandate"]["owner"]

    def task(self, task_id: str) -> dict:
        for task in self.instance()["tasks"]:
            if task["id"] == task_id:
                return task
        raise AdmissionError(f"unknown task {task_id!r}")

    def plan(self) -> dict:
        instance, state = self.state()
        return engine()["plan"](instance, state, utc_now())

    def available_reservation(self, task_id: str) -> float:
        instance, state = self.state()
        task = next(t for t in instance["tasks"] if t["id"] == task_id)
        progress = state["tasks"][task_id]
        committed = state["spent"] + sum(t["reserved"] for t in state["tasks"].values())
        overall = instance["budget"]["cost_limit"] - instance["budget"]["reserve"] - committed
        return max(0.0, min(task["cost_limit"] - progress["spent"], overall))

    def admit(self, event: dict) -> dict:
        """Apply `event` to the replayed history and append it only if the engine accepts it."""
        with self._lock:
            instance, state = self.state()
            try:
                new_state = engine()["apply"](instance, state, event)
            except (ValueError, KeyError, TypeError) as exc:
                raise AdmissionError(str(exc)) from exc
            line = json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
            self.events_path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(self.events_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(fd, line.encode())
                os.fsync(fd)
            finally:
                os.close(fd)
            return new_state

    def start(self, run_id: str, task_id: str, issuer: str) -> float:
        reserved = self.available_reservation(task_id)
        if reserved <= 0:
            raise AdmissionError("no budget left to reserve for this task")
        self.admit({"id": f"relay-{run_id}-start", "at": utc_now(), "issuer": issuer, "type": "start",
                    "task_id": task_id, "reserved_cost": reserved})
        return reserved

    def finish(self, run_id: str, task_id: str, issuer: str, actual_cost: float, accepted: bool,
               evidence_refs: list[str], confirmed_predicates: list[str]) -> None:
        event = {"id": f"relay-{run_id}-finish", "at": utc_now(), "issuer": issuer, "type": "finish",
                 "task_id": task_id, "actual_cost": actual_cost, "accepted": accepted,
                 "evidence_refs": evidence_refs}
        if accepted:
            event["predicate_results"] = {p: True for p in confirmed_predicates}
        self.admit(event)

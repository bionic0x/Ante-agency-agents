"""Room operations. Every method takes the authenticated member and checks its role
here, so the HTTP layer cannot forget a check."""
from __future__ import annotations

import json
import threading
import uuid

from . import auth, evidence
from .config import RelayConfig, model_api_key
from .nexus import AdmissionError, Contract
from .proxy import Meter, ModelProxy
from .runner import ContainerRun, RunError, agent_profile, build_command, new_run_token, prepare
from .store import ChainError, Store, now

MAX_MESSAGE = 8000
MAX_INSTRUCTION = 20000


class Forbidden(PermissionError):
    pass


class Conflict(RuntimeError):
    pass


def _role(member: dict, *roles: str) -> None:
    if member["role"] not in roles:
        raise Forbidden("your role does not allow this")


def _bounded_text(value, limit: int, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{what} is required")
    if len(value) > limit:
        raise ValueError(f"{what} exceeds {limit} characters")
    if "\x00" in value:
        raise ValueError(f"{what} contains a NUL byte")
    return value


class Relay:
    def __init__(self, cfg: RelayConfig, store: Store, contract: Contract, *, runner_factory=None,
                 proxy_factory=None, api_key: str | None = None):
        self.cfg = cfg
        self.store = store
        self.contract = contract
        self._runner_factory = runner_factory or ContainerRun
        self._proxy_factory = proxy_factory or ModelProxy
        self._api_key = api_key
        self._active: dict[str, ContainerRun] = {}
        self._lock = threading.Lock()

    # --- room -----------------------------------------------------------------
    def post_message(self, member: dict, text: str) -> dict:
        text = _bounded_text(text, MAX_MESSAGE, "message")
        with self.store.tx() as db:
            return self.store.append(db, "message", member["id"], {"name": member["name"], "text": text})

    def members(self, member: dict) -> list[dict]:
        rows = self.store.query("SELECT id, name, role, created_at, disabled_at FROM members ORDER BY created_at")
        return [dict(r) for r in rows]

    def invite(self, member: dict, name: str, role: str) -> tuple[str, str]:
        _role(member, "owner")
        if role not in ("operator", "viewer"):
            raise ValueError("invites are for operator or viewer roles")
        member_id = auth.create_member(self.store, name, role, member["id"])
        return member_id, auth.create_invite(self.store, member_id, member["id"])

    def reinvite(self, member: dict, member_id: str) -> str:
        _role(member, "owner")
        return auth.create_invite(self.store, member_id, member["id"])

    def disable(self, member: dict, member_id: str) -> None:
        _role(member, "owner")
        auth.disable_member(self.store, member_id, member["id"])

    def sessions(self, member: dict) -> list[dict]:
        _role(member, "owner")
        return auth.list_sessions(self.store)

    def revoke_session(self, member: dict, sid: str) -> None:
        _role(member, "owner")
        auth.revoke_session_by_id(self.store, sid, member["id"])

    def plan(self, member: dict) -> dict:
        plan = self.contract.plan()
        predicates = {t["id"]: list(t["acceptance_predicates"]) for t in self.contract.instance()["tasks"]}
        for row in plan["tasks"]:
            row["acceptance_predicates"] = predicates.get(row["task_id"], [])
        return plan

    def runs(self, member: dict) -> list[dict]:
        rows = self.store.query("SELECT id, task_id, instruction, requested_by, state, reserved_cost, actual_cost, "
                                "exit_code, error, artifact_digest, workspace_digest, control_changes, created_at, updated_at "
                                "FROM runs ORDER BY created_at DESC LIMIT 200")
        out = []
        for r in rows:
            item = dict(r)
            item["control_changes"] = json.loads(item["control_changes"] or "[]")
            out.append(item)
        return out

    def output(self, member: dict, run_id: str) -> str:
        if self.store.run(run_id) is None:
            raise KeyError("unknown run")
        path = self.cfg.runs_dir / run_id / "output.txt"
        return path.read_text(errors="replace") if path.exists() else ""

    # --- run lifecycle ----------------------------------------------------------
    def _set_state(self, db, run_id: str, state: str, actor: str, kind: str, extra: dict | None = None, **cols) -> None:
        sets = ", ".join(f"{k} = ?" for k in ("state", "updated_at", *cols))
        db.execute(f"UPDATE runs SET {sets} WHERE id = ?", (state, now(), *cols.values(), run_id))
        self.store.append(db, kind, actor, {"run_id": run_id, "state": state, **(extra or {})})

    def request_run(self, member: dict, task_id: str, instruction: str) -> str:
        _role(member, "owner", "operator")
        instruction = _bounded_text(instruction, MAX_INSTRUCTION, "instruction")
        task = self.contract.task(task_id)
        run_id = "r_" + uuid.uuid4().hex
        with self.store.tx() as db:
            db.execute("INSERT INTO runs (id, task_id, instruction, requested_by, state, created_at, updated_at) "
                       "VALUES (?,?,?,?,?,?,?)", (run_id, task["id"], instruction, member["id"], "requested", now(), now()))
            self.store.append(db, "run.requested", member["id"],
                              {"run_id": run_id, "task_id": task["id"], "agent": task["agent"], "instruction": instruction})
        return run_id

    def decline(self, member: dict, run_id: str, reason: str) -> None:
        _role(member, "owner")
        reason = _bounded_text(reason, 2000, "reason")
        with self.store.tx() as db:
            row = db.execute("SELECT state FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row is None or row["state"] != "requested":
                raise Conflict("only a requested run can be declined")
            self._set_state(db, run_id, "declined", member["id"], "run.declined", {"reason": reason})

    def approve(self, member: dict, run_id: str) -> float:
        _role(member, "owner")
        owner = self.contract.owner()
        if member["name"] != owner:
            raise Forbidden(f"the relay owner account must be named after the NEXUS mandate owner ({owner})")
        with self.store.tx() as db:
            row = db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row is None or row["state"] != "requested":
                raise Conflict("only a requested run can be approved")
            # Claim the run before talking to NEXUS so a double click cannot start it twice.
            self._set_state(db, run_id, "approved", member["id"], "run.approved")
        try:
            unit = self.contract.instance()["budget"]["unit"]
            if unit != self.cfg.model.cost_unit:
                raise AdmissionError(f"instance budget unit {unit!r} does not match the relay meter {self.cfg.model.cost_unit!r}")
            task = self.contract.task(row["task_id"])
            profile = agent_profile(task["agent"])
            reserved = self.contract.start(run_id, task["id"], owner)
        except (AdmissionError, RunError) as exc:
            with self.store.tx() as db:
                self._set_state(db, run_id, "failed_to_start", member["id"], "run.refused",
                                {"reason": str(exc)}, error=str(exc)[:2000])
            raise Conflict(f"NEXUS refused the run: {exc}") from exc
        with self.store.tx() as db:
            self._set_state(db, run_id, "running", member["id"], "run.started",
                            {"reserved_cost": reserved, "agent": task["agent"]}, reserved_cost=reserved)
        thread = threading.Thread(target=self._execute, args=(run_id, task, profile, reserved, row["instruction"]),
                                  name=f"relay-run-{run_id}", daemon=True)
        thread.start()
        return reserved

    def _execute(self, run_id: str, task: dict, profile, reserved: float, instruction: str) -> None:
        meter = Meter(self.cfg.model.cost_unit, self.cfg.model.prices, reserved)
        proxy = None
        paths = None
        code, digest, error = -1, None, None
        try:
            paths = prepare(self.cfg, run_id, task)
            token = new_run_token()
            proxy = self._proxy_factory(paths.socket, token, self._api_key or model_api_key(self.cfg),
                                        self.cfg.model.upstream, self.cfg.model.allowed_paths, meter,
                                        extra_request_fields=self.cfg.model.extra_request_fields)
            command = build_command(self.cfg, run_id, paths, profile, token)
            run = self._runner_factory(self.cfg, run_id, command, paths.output)
            proxy.on_exhausted = lambda: run.stop("budget")
            with self._lock:
                self._active[run_id] = run
            proxy.start()
            code, digest = run.run(instruction)
            if run.stop_reason:
                error = f"stopped: {run.stop_reason}"
            elif code != 0:
                error = f"agent exited with status {code}"
        except Exception as exc:  # recorded, never silently lost: the run still needs a NEXUS finish
            error = f"{type(exc).__name__}: {exc}"[:2000]
        finally:
            if proxy is not None:
                proxy.stop()
            with self._lock:
                self._active.pop(run_id, None)
        workspace_digest, changes = None, []
        if paths is not None:
            try:
                workspace_digest, changes, size = self._record_workspace(run_id, task["id"], paths.workspace)
                if size > self.cfg.runtime.workspace_max_bytes:
                    error = error or (f"workspace holds {size} bytes, above the {self.cfg.runtime.workspace_max_bytes}"
                                      " byte limit; clean it before the next run")
            except OSError as exc:
                error = error or f"workspace manifest failed: {exc}"[:2000]
        with self.store.tx() as db:
            self._set_state(db, run_id, "completed", "relay", "run.completed",
                            {"exit_code": code, "actual_cost": meter.spent, "requests": meter.requests,
                             "artifact_digest": digest, "workspace_digest": workspace_digest,
                             "control_changes": changes, "error": error},
                            exit_code=code, actual_cost=meter.spent, artifact_digest=digest, error=error,
                            workspace_digest=workspace_digest, control_changes=json.dumps(changes))

    def _record_workspace(self, run_id: str, task_id: str, workspace) -> tuple[str, list[str], int]:
        man = evidence.manifest(workspace)
        evidence.save(man, self.cfg.runs_dir / run_id / "manifest.json")
        if man["truncated"]:
            raise OSError("workspace manifest incomplete (scan limit or unreadable files); "
                          "its size and control-file inventory cannot establish acceptance")
        last = self.store.one("SELECT id FROM runs WHERE task_id = ? AND state = 'accepted' "
                              "ORDER BY updated_at DESC LIMIT 1", (task_id,))
        previous = evidence.load(self.cfg.runs_dir / last["id"] / "manifest.json") if last else None
        return evidence.digest(man), evidence.control_changes(previous, man), evidence.size_bytes(man)

    def recover(self) -> list[str]:
        """After a restart, no run is executing. Anything left approved or running is
        marked completed with an error so the owner reconciles it with a NEXUS finish."""
        recovered = []
        started = {e.get("id"): e.get("reserved_cost", 0) for e in self.contract.events() if e.get("type") == "start"}
        for row in self.store.query("SELECT id, state, reserved_cost FROM runs WHERE state IN ('approved','running')"):
            run_id = row["id"]
            self._runner_factory(self.cfg, run_id, [], self.cfg.runs_dir / run_id / "output.txt").stop("relay restarted")
            with self.store.tx() as db:
                if f"relay-{run_id}-start" in started:
                    # Metering was in memory; charge the full reservation rather than under-report.
                    charged = float(started[f"relay-{run_id}-start"] or 0)
                    self._set_state(db, run_id, "completed", "relay", "run.completed",
                                    {"error": "relay restarted during the run", "actual_cost": charged},
                                    error="relay restarted during the run", actual_cost=charged)
                else:
                    self._set_state(db, run_id, "failed_to_start", "relay", "run.refused",
                                    {"reason": "relay restarted before NEXUS admitted the run"},
                                    error="relay restarted before admission")
            recovered.append(run_id)
        return recovered

    def cancel(self, member: dict, run_id: str) -> None:
        _role(member, "owner")
        with self._lock:
            run = self._active.get(run_id)
        if run is None:
            raise Conflict("run is not executing")
        run.stop("cancelled by owner")

    def review(self, member: dict, run_id: str, accepted: bool, confirmed_predicates: list[str], note: str,
               acknowledged_control_changes: list[str] | None = None) -> None:
        _role(member, "owner")
        if type(accepted) is not bool:
            raise ValueError("accepted must be a boolean")
        if not isinstance(confirmed_predicates, list) or not all(isinstance(p, str) for p in confirmed_predicates):
            raise ValueError("confirmed_predicates must be a list of strings")
        note = _bounded_text(note, 4000, "review note")
        owner = self.contract.owner()
        if member["name"] != owner:
            raise Forbidden(f"the relay owner account must be named after the NEXUS mandate owner ({owner})")
        row = self.store.run(run_id)
        if row is None or row["state"] != "completed":
            raise Conflict("only a completed run can be reviewed")
        # Decide from the chained completion entry, not from the mutable runs row: both an
        # acceptance and the cost reported to NEXUS must rest on what was recorded at the time.
        try:
            logged = self.store.run_completion(run_id)
        except ChainError as exc:
            raise Conflict(f"run record failed verification: {exc}") from exc
        if logged is None:
            raise Conflict("run record failed verification: no run.completed entry in the log")
        mismatches = evidence.record_problems(row, logged)
        if accepted and mismatches:
            # A rejection still goes through, with the logged cost, so the run can be closed.
            raise Conflict("run record failed verification: " + "; ".join(mismatches))
        if accepted and (logged.get("error") or not logged.get("artifact_digest") or not logged.get("workspace_digest")):
            raise Conflict("a run that failed or produced no output cannot be accepted; reject it instead")
        if accepted:
            problems = evidence.artifact_problems(self.cfg.runs_dir / run_id,
                                                  logged["artifact_digest"], logged["workspace_digest"])
            if problems:
                raise Conflict("run evidence failed verification: " + "; ".join(problems))
        if acknowledged_control_changes is not None and (not isinstance(acknowledged_control_changes, list) or
                                                         not all(isinstance(p, str) for p in acknowledged_control_changes)):
            raise ValueError("acknowledged_control_changes must be a list of strings")
        changes = list(logged.get("control_changes") or [])
        if accepted and changes and sorted(acknowledged_control_changes or []) != sorted(changes):
            raise Conflict("this run changed files that steer future agent sessions; acknowledge each by name "
                           f"before accepting: {', '.join(changes)}")
        head = self.store.one("SELECT hash FROM log ORDER BY seq DESC LIMIT 1")["hash"]
        evidence_refs = [f"relay-output:sha256:{logged['artifact_digest']}"] if logged.get("artifact_digest") else []
        if logged.get("workspace_digest"):
            evidence_refs.append(f"relay-workspace:sha256:{logged['workspace_digest']}")
        evidence_refs.append(f"relay-log:sha256:{head}")
        try:
            self.contract.finish(run_id, row["task_id"], owner, float(logged.get("actual_cost") or 0), accepted,
                                 evidence_refs, confirmed_predicates if accepted else [])
        except AdmissionError as exc:
            raise Conflict(f"NEXUS refused the review: {exc}") from exc
        with self.store.tx() as db:
            self._set_state(db, run_id, "accepted" if accepted else "rejected", member["id"],
                            "run.accepted" if accepted else "run.rejected",
                            {"note": note, "predicates": confirmed_predicates if accepted else [], "evidence_refs": evidence_refs,
                             "acknowledged_control_changes": changes if accepted else [],
                             **({"record_mismatches": mismatches} if mismatches else {})},
                            **(self._logged_columns(logged) if mismatches else {}))

    @staticmethod
    def _logged_columns(logged: dict) -> dict:
        """Restore an edited runs row from its chained completion entry (the source of truth)."""
        cols = {f: logged.get(f) for f in evidence.COMPLETION_FIELDS}
        cols["control_changes"] = json.dumps(list(logged.get("control_changes") or []))
        return cols

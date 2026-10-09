"""SQLite persistence. The `log` table is append-only and hash-chained; other tables are
projections or credentials. Every write that changes room state appends to the log in
the same transaction."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading

GENESIS = "0" * 64
ROLES = ("owner", "operator", "viewer")
RUN_STATES = ("requested", "approved", "running", "completed", "accepted", "rejected", "declined", "failed_to_start")

SCHEMA = """
CREATE TABLE IF NOT EXISTS members (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL CHECK (role IN ('owner','operator','viewer')),
  created_at TEXT NOT NULL,
  disabled_at TEXT
);
CREATE TABLE IF NOT EXISTS invites (
  token_hash TEXT PRIMARY KEY,
  member_id TEXT NOT NULL REFERENCES members(id),
  expires_at TEXT NOT NULL,
  used_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  member_id TEXT NOT NULL REFERENCES members(id),
  csrf_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS log (
  seq INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  kind TEXT NOT NULL,
  actor TEXT NOT NULL,
  payload TEXT NOT NULL,
  prev_hash TEXT NOT NULL,
  hash TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  instruction TEXT NOT NULL,
  requested_by TEXT NOT NULL,
  state TEXT NOT NULL,
  reserved_cost REAL,
  actual_cost REAL,
  exit_code INTEGER,
  error TEXT,
  artifact_digest TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS log_no_update BEFORE UPDATE ON log
BEGIN SELECT RAISE(ABORT, 'log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS log_no_delete BEFORE DELETE ON log
BEGIN SELECT RAISE(ABORT, 'log is append-only'); END;
"""


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def entry_hash(prev_hash: str, seq: int, at: str, kind: str, actor: str, payload: str) -> str:
    material = canonical({"prev": prev_hash, "seq": seq, "at": at, "kind": kind, "actor": actor, "payload": payload})
    return hashlib.sha256(material.encode()).hexdigest()


class ChainError(RuntimeError):
    pass


class Store:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        new = not path.exists()
        if new:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA journal_mode = WAL")
        self._db.execute("PRAGMA synchronous = FULL")
        self._db.executescript(SCHEMA)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(path) + suffix)
            if sidecar.exists():
                os.chmod(sidecar, 0o600)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    @contextlib.contextmanager
    def tx(self):
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield self._db
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
            self._db.execute("COMMIT")

    def query(self, sql: str, params=()) -> list[sqlite3.Row]:
        with self._lock:
            return self._db.execute(sql, params).fetchall()

    def one(self, sql: str, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def append(self, db: sqlite3.Connection, kind: str, actor: str, payload: dict) -> dict:
        """Append to the chain. Must be called inside `tx()`."""
        last = db.execute("SELECT seq, hash FROM log ORDER BY seq DESC LIMIT 1").fetchone()
        seq = (last["seq"] + 1) if last else 1
        prev = last["hash"] if last else GENESIS
        at = now()
        body = canonical(payload)
        digest = entry_hash(prev, seq, at, kind, actor, body)
        db.execute("INSERT INTO log (seq, at, kind, actor, payload, prev_hash, hash) VALUES (?,?,?,?,?,?,?)",
                   (seq, at, kind, actor, body, prev, digest))
        return {"seq": seq, "at": at, "kind": kind, "actor": actor, "payload": payload, "hash": digest}

    def entries_after(self, seq: int, limit: int = 200) -> list[dict]:
        rows = self.query("SELECT seq, at, kind, actor, payload, hash FROM log WHERE seq > ? ORDER BY seq LIMIT ?",
                          (seq, limit))
        return [{"seq": r["seq"], "at": r["at"], "kind": r["kind"], "actor": r["actor"],
                 "payload": json.loads(r["payload"]), "hash": r["hash"]} for r in rows]

    def verify_chain(self) -> int:
        prev = GENESIS
        expected_seq = 1
        for r in self.query("SELECT seq, at, kind, actor, payload, prev_hash, hash FROM log ORDER BY seq"):
            if r["seq"] != expected_seq:
                raise ChainError(f"log gap at seq {expected_seq}")
            if r["prev_hash"] != prev:
                raise ChainError(f"log seq {r['seq']}: prev_hash mismatch")
            if entry_hash(prev, r["seq"], r["at"], r["kind"], r["actor"], r["payload"]) != r["hash"]:
                raise ChainError(f"log seq {r['seq']}: content does not match its hash")
            prev = r["hash"]
            expected_seq += 1
        return expected_seq - 1

    def member(self, member_id: str):
        return self.one("SELECT * FROM members WHERE id = ?", (member_id,))

    def run(self, run_id: str):
        return self.one("SELECT * FROM runs WHERE id = ?", (run_id,))

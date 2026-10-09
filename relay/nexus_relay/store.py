"""SQLite persistence. The `log` table is append-only and hash-chained; other tables are
projections or credentials. Every write that changes room state appends to the log in
the same transaction."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import hmac
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


CHAIN_KEY_ENV = "NEXUS_RELAY_CHAIN_KEY"
MIN_CHAIN_KEY_BYTES = 32
ALG_PLAIN = "sha256"
ALG_KEYED = "hmac-sha256"


def entry_hash(prev_hash: str, seq: int, at: str, kind: str, actor: str, payload: str,
               key: bytes | None = None) -> str:
    material = canonical({"prev": prev_hash, "seq": seq, "at": at, "kind": kind, "actor": actor, "payload": payload})
    if key is None:
        return hashlib.sha256(material.encode()).hexdigest()
    return hmac.new(key, material.encode(), hashlib.sha256).hexdigest()


def key_id(key: bytes) -> str:
    return hashlib.sha256(b"nexus-relay/chain-key-id/v1\x00" + key).hexdigest()


def chain_key_from_env() -> bytes | None:
    """The chain key is supplied at start (secret manager, prompt) and never written to disk,
    so an attacker who can rewrite the database cannot recompute a keyed chain (audit R-7)."""
    raw = os.environ.get(CHAIN_KEY_ENV)
    if raw is None or raw == "":
        return None
    key = raw.encode()
    if len(key) < MIN_CHAIN_KEY_BYTES:
        raise ChainError(f"{CHAIN_KEY_ENV} must be at least {MIN_CHAIN_KEY_BYTES} bytes")
    return key


class ChainError(RuntimeError):
    pass


class Store:
    def __init__(self, path: Path, chain_key: bytes | None = None):
        self.path = path
        self._key = chain_key
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
        self._migrate()
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(path) + suffix)
            if sidecar.exists():
                os.chmod(sidecar, 0o600)

    def _migrate(self) -> None:
        """Additive, idempotent schema upgrades for databases created by earlier versions."""
        run_cols = {r["name"] for r in self._db.execute("PRAGMA table_info(runs)")}
        for col, decl in (("workspace_digest", "TEXT"), ("control_changes", "TEXT")):
            if col not in run_cols:
                self._db.execute(f"ALTER TABLE runs ADD COLUMN {col} {decl}")
        session_cols = {r["name"] for r in self._db.execute("PRAGMA table_info(sessions)")}
        if "last_seen_at" not in session_cols:
            self._db.execute("ALTER TABLE sessions ADD COLUMN last_seen_at TEXT")
        log_cols = {r["name"] for r in self._db.execute("PRAGMA table_info(log)")}
        if "alg" not in log_cols:
            self._db.execute(f"ALTER TABLE log ADD COLUMN alg TEXT NOT NULL DEFAULT '{ALG_PLAIN}'")
        self._db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self._db.execute("CREATE TRIGGER IF NOT EXISTS meta_key_fixed BEFORE UPDATE ON meta WHEN OLD.key = 'chain_key_id' "
                         "BEGIN SELECT RAISE(ABORT, 'chain key id is fixed'); END")
        self._db.execute("CREATE TRIGGER IF NOT EXISTS meta_key_kept BEFORE DELETE ON meta WHEN OLD.key = 'chain_key_id' "
                         "BEGIN SELECT RAISE(ABORT, 'chain key id is fixed'); END")

    @property
    def keyed(self) -> bool:
        return self._key is not None

    def _check_key(self, db) -> None:
        """A keyed chain stays keyed with the same key; appends never silently downgrade."""
        row = db.execute("SELECT value FROM meta WHERE key = 'chain_key_id'").fetchone()
        if self._key is None:
            if row is not None:
                raise ChainError(f"this log is keyed; set {CHAIN_KEY_ENV} to the key it was started with")
            return
        if row is None:
            db.execute("INSERT INTO meta (key, value) VALUES ('chain_key_id', ?)", (key_id(self._key),))
        elif not hmac.compare_digest(row["value"], key_id(self._key)):
            raise ChainError(f"{CHAIN_KEY_ENV} does not match the key this log was started with")

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
        self._check_key(db)
        last = db.execute("SELECT seq, hash FROM log ORDER BY seq DESC LIMIT 1").fetchone()
        seq = (last["seq"] + 1) if last else 1
        prev = last["hash"] if last else GENESIS
        at = now()
        body = canonical(payload)
        digest = entry_hash(prev, seq, at, kind, actor, body, self._key)
        db.execute("INSERT INTO log (seq, at, kind, actor, payload, prev_hash, hash, alg) VALUES (?,?,?,?,?,?,?,?)",
                   (seq, at, kind, actor, body, prev, digest, ALG_KEYED if self._key else ALG_PLAIN))
        return {"seq": seq, "at": at, "kind": kind, "actor": actor, "payload": payload, "hash": digest}

    def entries_after(self, seq: int, limit: int = 200) -> list[dict]:
        rows = self.query("SELECT seq, at, kind, actor, payload, hash FROM log WHERE seq > ? ORDER BY seq LIMIT ?",
                          (seq, limit))
        return [{"seq": r["seq"], "at": r["at"], "kind": r["kind"], "actor": r["actor"],
                 "payload": json.loads(r["payload"]), "hash": r["hash"]} for r in rows]

    def verify_chain(self, adopt_key: bool = False) -> int:
        """Recompute the chain. An unkeyed chain only detects careless edits; a keyed chain
        detects any rewrite by someone without the key."""
        stored_id = self.one("SELECT value FROM meta WHERE key = 'chain_key_id'")
        if stored_id is not None:
            if self._key is None:
                raise ChainError(f"this log is keyed; set {CHAIN_KEY_ENV} to verify it")
            if not hmac.compare_digest(stored_id["value"], key_id(self._key)):
                raise ChainError(f"{CHAIN_KEY_ENV} does not match the key this log was started with")
        prev = GENESIS
        expected_seq = 1
        seen_keyed = False
        for r in self.query("SELECT seq, at, kind, actor, payload, prev_hash, hash, alg FROM log ORDER BY seq"):
            if r["seq"] != expected_seq:
                raise ChainError(f"log gap at seq {expected_seq}")
            if r["prev_hash"] != prev:
                raise ChainError(f"log seq {r['seq']}: prev_hash mismatch")
            if r["alg"] == ALG_KEYED:
                if self._key is None:
                    raise ChainError(f"log seq {r['seq']} is keyed; set {CHAIN_KEY_ENV} to verify it")
                seen_keyed = True
                expected = entry_hash(prev, r["seq"], r["at"], r["kind"], r["actor"], r["payload"], self._key)
                if not hmac.compare_digest(expected, r["hash"]):
                    raise ChainError(f"log seq {r['seq']}: content does not match its keyed hash")
            elif r["alg"] == ALG_PLAIN:
                if seen_keyed:
                    raise ChainError(f"log seq {r['seq']}: unkeyed entry after the chain became keyed")
                if entry_hash(prev, r["seq"], r["at"], r["kind"], r["actor"], r["payload"]) != r["hash"]:
                    raise ChainError(f"log seq {r['seq']}: content does not match its hash")
            else:
                raise ChainError(f"log seq {r['seq']}: unknown hash algorithm {r['alg']!r}")
            prev = r["hash"]
            expected_seq += 1
        count = expected_seq - 1
        if self._key is not None and count and not adopt_key and (stored_id is None or not seen_keyed):
            # Verifying with a key asserts the log is keyed. A log rewritten as plain SHA-256
            # with its key record removed must fail here, not pass as a legacy log.
            raise ChainError("a chain key was supplied but the log is not keyed; it may have been rewritten")
        return count

    def head(self) -> tuple[int, str]:
        row = self.one("SELECT seq, hash FROM log ORDER BY seq DESC LIMIT 1")
        return (row["seq"], row["hash"]) if row else (0, GENESIS)

    def hash_at(self, seq: int) -> str | None:
        row = self.one("SELECT hash FROM log WHERE seq = ?", (seq,))
        return row["hash"] if row else None

    def has_hash(self, digest: str) -> bool:
        return self.one("SELECT 1 FROM log WHERE hash = ?", (digest,)) is not None

    def authentic_entry(self, r) -> None:
        """Check one entry without walking the whole chain: its own hash (an HMAC when keyed),
        its link to the entry before it, and that it is not a plain entry after keying began.
        `verify` still checks the full chain; this lets decisions trust a single entry."""
        stored_id = self.one("SELECT value FROM meta WHERE key = 'chain_key_id'")
        if stored_id is not None and (self._key is None or not hmac.compare_digest(stored_id["value"], key_id(self._key))):
            raise ChainError(f"this log is keyed; {CHAIN_KEY_ENV} is missing or does not match")
        expected_prev = self.hash_at(r["seq"] - 1) if r["seq"] > 1 else GENESIS
        if r["prev_hash"] != expected_prev:
            raise ChainError(f"log seq {r['seq']}: prev_hash mismatch")
        if r["alg"] == ALG_KEYED:
            if self._key is None:
                raise ChainError(f"log seq {r['seq']} is keyed; set {CHAIN_KEY_ENV} to check it")
            key = self._key
        elif r["alg"] == ALG_PLAIN:
            if self.one("SELECT 1 FROM log WHERE alg = ? AND seq < ? LIMIT 1", (ALG_KEYED, r["seq"])) is not None:
                raise ChainError(f"log seq {r['seq']}: unkeyed entry after the chain became keyed")
            key = None
        else:
            raise ChainError(f"log seq {r['seq']}: unknown hash algorithm {r['alg']!r}")
        expected = entry_hash(r["prev_hash"], r["seq"], r["at"], r["kind"], r["actor"], r["payload"], key)
        if not hmac.compare_digest(expected, r["hash"]):
            raise ChainError(f"log seq {r['seq']}: content does not match its hash")

    def run_completion(self, run_id: str) -> dict | None:
        """The authenticated `run.completed` payload for a run: the record evidence checks trust.
        The `runs` table is a mutable index; the chained entry is what was recorded at the time."""
        rows = self.query("SELECT seq, at, kind, actor, payload, prev_hash, hash, alg FROM log "
                          "WHERE kind = 'run.completed' AND json_extract(payload, '$.run_id') = ? ORDER BY seq",
                          (run_id,))
        if not rows:
            return None
        if len(rows) > 1:
            raise ChainError(f"run {run_id} has {len(rows)} completion entries in the log")
        self.authentic_entry(rows[0])
        payload = json.loads(rows[0]["payload"])
        if not isinstance(payload, dict):
            raise ChainError(f"log seq {rows[0]['seq']}: completion payload is not an object")
        return payload

    def member(self, member_id: str):
        return self.one("SELECT * FROM members WHERE id = ?", (member_id,))

    def run(self, run_id: str):
        return self.one("SELECT * FROM runs WHERE id = ?", (run_id,))

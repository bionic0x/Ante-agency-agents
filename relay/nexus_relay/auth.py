"""Members, invites, sessions, CSRF and login rate limiting.

Secrets are 256-bit random values. Only their SHA-256 hashes are stored, so a copy of
the database does not yield a usable invite or session."""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import hmac
import re
import secrets
import threading
import time
import uuid

from .store import ROLES, Store, now, parse_time

INVITE_TTL = dt.timedelta(hours=24)
SESSION_TTL = dt.timedelta(days=14)
SESSION_IDLE = dt.timedelta(hours=12)
TOUCH_INTERVAL = dt.timedelta(minutes=5)
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,47}$")


class AuthError(PermissionError):
    pass


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _later(delta: dt.timedelta) -> str:
    return (dt.datetime.now(dt.timezone.utc) + delta).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _expired(value: str) -> bool:
    return parse_time(value) <= dt.datetime.now(dt.timezone.utc)


def create_member(store: Store, name: str, role: str, actor: str) -> str:
    if not NAME_RE.match(name):
        raise ValueError("member name: 1-48 chars, letters, digits, . _ -")
    if role not in ROLES:
        raise ValueError("unknown role")
    member_id = "m_" + uuid.uuid4().hex
    with store.tx() as db:
        if role == "owner" and db.execute("SELECT 1 FROM members WHERE role='owner'").fetchone():
            raise ValueError("the relay already has its owner")
        if db.execute("SELECT 1 FROM members WHERE name = ?", (name,)).fetchone():
            raise ValueError("member name already exists")
        db.execute("INSERT INTO members (id, name, role, created_at) VALUES (?,?,?,?)", (member_id, name, role, now()))
        store.append(db, "member.created", actor, {"member_id": member_id, "name": name, "role": role})
    return member_id


def create_invite(store: Store, member_id: str, actor: str) -> str:
    member = store.member(member_id)
    if member is None or member["disabled_at"]:
        raise ValueError("unknown or disabled member")
    token = new_secret()
    with store.tx() as db:
        db.execute("INSERT INTO invites (token_hash, member_id, expires_at) VALUES (?,?,?)",
                   (hash_secret(token), member_id, _later(INVITE_TTL)))
        store.append(db, "invite.created", actor, {"member_id": member_id})
    return token


def redeem_invite(store: Store, token: str) -> tuple[str, str, str]:
    """Return (member_id, session_token, csrf_token). The invite cannot be used again."""
    if not isinstance(token, str) or not (20 <= len(token) <= 128):
        raise AuthError("invalid invite")
    token_hash = hash_secret(token)
    session = new_secret()
    csrf = new_secret()
    with store.tx() as db:
        row = db.execute("SELECT i.member_id, i.expires_at, i.used_at, m.disabled_at FROM invites i "
                         "JOIN members m ON m.id = i.member_id WHERE i.token_hash = ?", (token_hash,)).fetchone()
        if row is None or row["used_at"] or row["disabled_at"] or _expired(row["expires_at"]):
            raise AuthError("invalid invite")
        updated = db.execute("UPDATE invites SET used_at = ? WHERE token_hash = ? AND used_at IS NULL",
                             (now(), token_hash)).rowcount
        if updated != 1:
            raise AuthError("invalid invite")
        db.execute("INSERT INTO sessions (token_hash, member_id, csrf_hash, created_at, expires_at) VALUES (?,?,?,?,?)",
                   (hash_secret(session), row["member_id"], hash_secret(csrf), now(), _later(SESSION_TTL)))
        store.append(db, "session.created", row["member_id"], {"member_id": row["member_id"]})
    return row["member_id"], session, csrf


def session_id(token_hash: str) -> str:
    """A public handle for a session: lets the owner revoke it without exposing its hash."""
    return hashlib.sha256(("session-id/v1:" + token_hash).encode()).hexdigest()[:24]


def session_member(store: Store, session_token: str | None):
    """Absolute lifetime 14 days, idle limit 12 hours (audit R-12)."""
    if not session_token or len(session_token) > 128:
        return None, None
    token_hash = hash_secret(session_token)
    row = store.one("SELECT s.member_id, s.csrf_hash, s.expires_at, s.created_at, s.last_seen_at, m.name, m.role, "
                    "m.disabled_at FROM sessions s JOIN members m ON m.id = s.member_id WHERE s.token_hash = ?",
                    (token_hash,))
    if row is None or row["disabled_at"] or _expired(row["expires_at"]):
        return None, None
    last_seen = parse_time(row["last_seen_at"] or row["created_at"])
    current = dt.datetime.now(dt.timezone.utc)
    if current - last_seen > SESSION_IDLE:
        with store.tx() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
            store.append(db, "session.expired", row["member_id"], {"reason": "idle"})
        return None, None
    if current - last_seen > TOUCH_INTERVAL:
        with store.tx() as db:
            db.execute("UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?", (now(), token_hash))
    return {"id": row["member_id"], "name": row["name"], "role": row["role"]}, row["csrf_hash"]


def list_sessions(store: Store) -> list[dict]:
    rows = store.query("SELECT s.token_hash, s.created_at, s.last_seen_at, s.expires_at, m.name, m.role "
                       "FROM sessions s JOIN members m ON m.id = s.member_id ORDER BY s.created_at")
    return [{"id": session_id(r["token_hash"]), "member": r["name"], "role": r["role"], "created_at": r["created_at"],
             "last_seen_at": r["last_seen_at"] or r["created_at"], "expires_at": r["expires_at"]} for r in rows]


def revoke_session_by_id(store: Store, sid: str, actor: str) -> None:
    with store.tx() as db:
        for r in db.execute("SELECT token_hash FROM sessions").fetchall():
            if hmac.compare_digest(session_id(r["token_hash"]), sid):
                db.execute("DELETE FROM sessions WHERE token_hash = ?", (r["token_hash"],))
                store.append(db, "session.revoked", actor, {"session_id": sid})
                return
    raise ValueError("unknown session")


def rotate_csrf(store: Store, session_token: str) -> str:
    """Issue a fresh CSRF token for a live session (the page fetches it on load)."""
    csrf = new_secret()
    with store.tx() as db:
        db.execute("UPDATE sessions SET csrf_hash = ? WHERE token_hash = ?", (hash_secret(csrf), hash_secret(session_token)))
    return csrf


def csrf_ok(csrf_hash: str | None, presented: str | None) -> bool:
    if not csrf_hash or not presented or len(presented) > 128:
        return False
    return hmac.compare_digest(csrf_hash, hash_secret(presented))


def revoke_session(store: Store, session_token: str, actor: str) -> None:
    with store.tx() as db:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_secret(session_token),))
        store.append(db, "session.revoked", actor, {})


def disable_member(store: Store, member_id: str, actor: str) -> None:
    with store.tx() as db:
        row = db.execute("SELECT role FROM members WHERE id = ?", (member_id,)).fetchone()
        if row is None:
            raise ValueError("unknown member")
        if row["role"] == "owner":
            raise ValueError("the owner cannot be disabled")
        db.execute("UPDATE members SET disabled_at = ? WHERE id = ?", (now(), member_id))
        db.execute("DELETE FROM sessions WHERE member_id = ?", (member_id,))
        db.execute("UPDATE invites SET used_at = ? WHERE member_id = ? AND used_at IS NULL", (now(), member_id))
        store.append(db, "member.disabled", actor, {"member_id": member_id})


class RateLimiter:
    """Sliding-window limiter for unauthenticated endpoints: per client and global."""

    def __init__(self, per_client: int = 10, global_limit: int = 100, window_seconds: int = 900):
        self.per_client = per_client
        self.global_limit = global_limit
        self.window = window_seconds
        self._hits: dict[str, collections.deque] = collections.defaultdict(collections.deque)
        self._global: collections.deque = collections.deque()
        self._lock = threading.Lock()

    def allow(self, client: str) -> bool:
        cutoff = time.monotonic() - self.window
        with self._lock:
            hits = self._hits[client]
            while hits and hits[0] < cutoff:
                hits.popleft()
            while self._global and self._global[0] < cutoff:
                self._global.popleft()
            if len(hits) >= self.per_client or len(self._global) >= self.global_limit:
                return False
            stamp = time.monotonic()
            hits.append(stamp)
            self._global.append(stamp)
            if len(self._hits) > 10_000:
                for key in [k for k, v in self._hits.items() if not v]:
                    del self._hits[key]
            return True

"""Workspace evidence (audit R-6, R-8).

After a run, the relay records what the agent actually left in its workspace: a manifest
of every regular file (path, size, SHA-256) and symlink (target, never followed). Its
digest goes into the NEXUS `finish` evidence, so acceptance is bound to the delivered
state rather than to text the agent printed.

Files that steer future agent sessions (agent settings, hooks, instruction files) are
"control files". Changes to them since the task's last accepted run are surfaced to the
owner, who must acknowledge them by name before accepting: a run must not be able to
plant instructions for the next one unnoticed.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
from pathlib import Path
import stat

MAX_FILES = 50_000
MAX_HASHED_BYTES = 2 * 1024 ** 3
CONTROL_PATTERNS = (
    ".claude", ".claude/*", "CLAUDE.md", "CLAUDE.local.md", "*/CLAUDE.md", "AGENTS.md", "*/AGENTS.md",
    ".mcp.json", ".git/hooks/*", ".gitattributes", ".gitconfig", ".git/config", ".cursor/*", ".vscode/*",
    ".github/workflows/*", ".envrc", ".npmrc", ".pypirc", "Makefile", "package.json", "pyproject.toml",
)


def _hash_file(path: Path, budget: list[int]) -> str | None:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return None
    digest = hashlib.sha256()
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            budget[0] -= len(chunk)
            if budget[0] < 0:
                return None
            digest.update(chunk)
    finally:
        os.close(fd)
    return digest.hexdigest()


def manifest(workspace: Path) -> dict:
    entries: dict[str, dict] = {}
    truncated = False
    budget = [MAX_HASHED_BYTES]
    for root, dirs, files in os.walk(workspace, followlinks=False):
        dirs.sort()
        for name in sorted(files) + [d for d in dirs if os.path.islink(os.path.join(root, d))]:
            full = Path(root) / name
            rel = full.relative_to(workspace).as_posix()
            if len(entries) >= MAX_FILES:
                truncated = True
                break
            try:
                st = os.lstat(full)
            except OSError:
                continue
            if stat.S_ISLNK(st.st_mode):
                entries[rel] = {"type": "symlink", "target": os.readlink(full)}
            elif stat.S_ISREG(st.st_mode):
                sha = _hash_file(full, budget)
                if sha is None:
                    truncated = True
                    entries[rel] = {"type": "file", "size": st.st_size, "sha256": None}
                else:
                    entries[rel] = {"type": "file", "size": st.st_size, "sha256": sha}
            else:
                entries[rel] = {"type": "special"}
        if truncated:
            break
    return {"version": 1, "entries": entries, "truncated": truncated}


def digest(man: dict) -> str:
    return hashlib.sha256(json.dumps(man, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def is_control(path: str) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in CONTROL_PATTERNS)


def control_changes(previous: dict | None, current: dict) -> list[str]:
    before = (previous or {}).get("entries", {})
    after = current.get("entries", {})
    changed = []
    for path in sorted(set(before) | set(after)):
        if is_control(path) and before.get(path) != after.get(path):
            changed.append(path)
    return changed


def size_bytes(man: dict) -> int:
    return sum(e.get("size", 0) for e in man.get("entries", {}).values())


def save(man: dict, path: Path) -> None:
    fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(man, f, sort_keys=True, separators=(",", ":"))


def load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None

"""Canonical JSON serialisation and hashing.

The historical scripts serialised JSON for hashing with four different settings.
Frozen case-pack hashes and replay digests depend on those exact bytes, so each
setting survives as a named profile. New code uses ``UNICODE_STRICT``.

    profile          ensure_ascii  allow_nan   used by (historically)
    ASCII            yes           yes         marketplace-intake
    ASCII_STRICT     yes           no          nexus-instance digest
    UNICODE          no            yes         nexus-pilot / nexus-anthropic packets
    UNICODE_STRICT   no            no          nexus-casepack; every new command

All profiles sort keys and use the compact separators ``(',', ':')``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Profile:
    name: str
    ensure_ascii: bool
    allow_nan: bool


ASCII = Profile('ascii', ensure_ascii=True, allow_nan=True)
ASCII_STRICT = Profile('ascii_strict', ensure_ascii=True, allow_nan=False)
UNICODE = Profile('unicode', ensure_ascii=False, allow_nan=True)
UNICODE_STRICT = Profile('unicode_strict', ensure_ascii=False, allow_nan=False)
DEFAULT = UNICODE_STRICT


def dumps(value: Any, profile: Profile = DEFAULT) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=profile.ensure_ascii, allow_nan=profile.allow_nan)


def encode(value: Any, profile: Profile = DEFAULT) -> bytes:
    return dumps(value, profile).encode('utf-8')


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def digest(value: Any, profile: Profile = DEFAULT) -> str:
    """SHA-256 of the canonical encoding of ``value``."""
    return sha256_hex(encode(value, profile))

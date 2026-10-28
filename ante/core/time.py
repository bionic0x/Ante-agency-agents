"""Timestamps: ISO-8601 with an explicit offset, normalised to UTC.

Commands that judge expiry or freshness take ``--at`` explicitly; nothing in the
package reads the wall clock for a decision. That keeps every artefact
reproducible from its inputs.
"""
from __future__ import annotations

import datetime as dt


class TimeError(ValueError):
    pass


def parse(value: object, field: str = 'timestamp') -> dt.datetime:
    """Parse aware ISO-8601 text (``Z`` accepted) and return it in UTC."""
    if not isinstance(value, str):
        raise TimeError(f'{field}: ISO-8601 text required')
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise TimeError(f'{field}: not ISO-8601') from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TimeError(f'{field}: timezone offset required')
    return parsed.astimezone(dt.timezone.utc)


def iso(value: dt.datetime) -> str:
    """Canonical text form: UTC, seconds precision unless sub-second is present, ``Z``."""
    value = value.astimezone(dt.timezone.utc)
    text = value.isoformat()
    return text.replace('+00:00', 'Z')

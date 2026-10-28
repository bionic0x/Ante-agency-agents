"""Small declarative validation used by every new command.

The checks are strict on purpose: booleans are not integers, text must be
non-empty after trimming, objects must carry exactly the declared keys. Errors
are ``SchemaError`` with a dotted path and a defect, never the offending value.
"""
from __future__ import annotations

import math
from typing import Any, Iterable


class SchemaError(ValueError):
    pass


def fail(path: str, message: str) -> None:
    raise SchemaError(f'{path}: {message}')


def require(condition: bool, path: str, message: str) -> None:
    if not condition:
        fail(path, message)


def obj(value: Any, path: str) -> dict:
    require(isinstance(value, dict), path, 'object required')
    return value


def exact_keys(value: Any, required: Iterable[str], path: str,
               optional: Iterable[str] = ()) -> dict:
    obj(value, path)
    required, optional = set(required), set(optional)
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required - optional)
    if missing:
        fail(path, f'missing field(s) {", ".join(missing)}')
    if unknown:
        fail(path, f'unknown field(s) {", ".join(unknown)}')
    return value


def text(value: Any, path: str) -> str:
    require(isinstance(value, str) and value.strip() != '', path, 'non-empty text required')
    return value


def boolean(value: Any, path: str) -> bool:
    require(type(value) is bool, path, 'true or false required')
    return value


def integer(value: Any, path: str, minimum: int | None = None) -> int:
    require(type(value) is int, path, 'integer required')
    if minimum is not None:
        require(value >= minimum, path, f'must be at least {minimum}')
    return value


def number(value: Any, path: str, low: float | None = None, high: float | None = None) -> float:
    require(type(value) in (int, float) and math.isfinite(value), path, 'finite number required')
    if low is not None:
        require(value >= low, path, f'must be at least {low}')
    if high is not None:
        require(value <= high, path, f'must be at most {high}')
    return value


def enum(value: Any, allowed: Iterable[str], path: str) -> str:
    allowed = tuple(allowed)
    require(isinstance(value, str) and value in allowed, path, f'one of {", ".join(allowed)} required')
    return value


def array(value: Any, path: str, minimum: int = 0) -> list:
    require(isinstance(value, list), path, 'array required')
    require(len(value) >= minimum, path, f'at least {minimum} item(s) required')
    return value


def unique_ids(items: list, path: str, key: str = 'id') -> list[str]:
    ids = [text(item.get(key) if isinstance(item, dict) else None, f'{path}[{index}].{key}')
           for index, item in enumerate(items)]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    require(not duplicates, path, f'duplicate {key}(s) {", ".join(duplicates)}')
    return ids

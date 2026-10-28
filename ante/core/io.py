"""Strict JSON and YAML input for every new ``ante`` command.

Rules:
- duplicate object keys are rejected (the last-value-wins default of ``json``
  lets two writers disagree silently inside one file);
- size is bounded before parsing;
- non-finite numbers (``NaN``, ``Infinity``) are rejected;
- error messages name the file and the defect class, never echo input content,
  so a secret pasted into the wrong file does not reach a log.

The historical CLIs keep their own loaders until a reviewed behaviour change
tightens them (decision D-007).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_MAX_BYTES = 4 * 1024 * 1024


class InputError(ValueError):
    """Unreadable or invalid input. ``str(exc)`` never contains input content."""


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise InputError('duplicate object key')
        seen[key] = value
    return seen


def _no_constant(token: str) -> Any:
    raise InputError('non-finite number')


def parse_json(text: str, label: str = 'input') -> Any:
    try:
        return json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
    except InputError as exc:
        raise InputError(f'{label}: {exc}') from None
    except json.JSONDecodeError as exc:
        raise InputError(f'{label}: not valid JSON (line {exc.lineno}, column {exc.colno})') from None


def read_text(path: Path | str, label: str | None = None,
              max_bytes: int = DEFAULT_MAX_BYTES) -> str:
    target = Path(path)
    name = label or target.name
    try:
        size = target.stat().st_size
    except FileNotFoundError:
        raise InputError(f'{name}: file not found') from None
    except OSError:
        raise InputError(f'{name}: cannot be read') from None
    if size > max_bytes:
        raise InputError(f'{name}: larger than {max_bytes} bytes')
    try:
        return target.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        raise InputError(f'{name}: not UTF-8 text') from None
    except OSError:
        raise InputError(f'{name}: cannot be read') from None


def load_json(path: Path | str, label: str | None = None,
              max_bytes: int = DEFAULT_MAX_BYTES) -> Any:
    target = Path(path)
    return parse_json(read_text(target, label, max_bytes), label or target.name)


class _UniqueKeyLoader:
    """Built lazily: PyYAML is a validation dependency, not a runtime one."""
    loader = None

    @classmethod
    def get(cls):
        if cls.loader is None:
            import yaml

            class Loader(yaml.SafeLoader):
                pass

            def construct_mapping(loader, node, deep=False):
                keys = set()
                for key_node, _ in node.value:
                    key = loader.construct_object(key_node, deep=deep)
                    if key in keys:
                        raise InputError('duplicate object key')
                    keys.add(key)
                return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

            Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
            cls.loader = Loader
        return cls.loader


def load_document(path: Path | str, label: str | None = None,
                  max_bytes: int = DEFAULT_MAX_BYTES) -> Any:
    """Load ``.json`` strictly; load ``.yaml``/``.yml`` with the same duplicate-key rule."""
    target = Path(path)
    name = label or target.name
    text = read_text(target, name, max_bytes)
    if target.suffix.lower() in ('.yaml', '.yml'):
        try:
            import yaml
        except ImportError:
            raise InputError(f'{name}: YAML input needs PyYAML; supply JSON instead') from None
        try:
            value = yaml.load(text, Loader=_UniqueKeyLoader.get())
        except InputError as exc:
            raise InputError(f'{name}: {exc}') from None
        except yaml.YAMLError:
            raise InputError(f'{name}: not valid YAML') from None
        # Round-trip through strict JSON so YAML-only types cannot slip through.
        try:
            return parse_json(json.dumps(value, allow_nan=False), name)
        except (TypeError, ValueError):
            raise InputError(f'{name}: YAML value has no JSON equivalent') from None
    return parse_json(text, name)

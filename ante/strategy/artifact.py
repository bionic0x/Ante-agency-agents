"""The typed artefact every ``ante`` command emits, and its lineage.

An artefact is a JSON object:

    schema_version   1
    command          the command that produced it
    case_id          inherited from ``frame``; every artefact of a case shares it
    at               the decision time (``--at`` or the input's ``at``), UTC
    input_sha256     canonical hash of the command's own input document
    parents          [{command, artifact_sha256}] — the artefacts it was built on
    independence_level   reviews only: SELF | SEPARATED_CONTEXT | INDEPENDENT_OPERATOR
    claims           [{id, text, status, source, date, limit, ...}]
    body             command-specific content
    findings         [{severity, code, path, message}] that did not block the artefact
    verdict          a decision state, or null when the command does not decide
    next_decision    the next decision a human owner has to take
    artifact_sha256  canonical hash of everything above

The Markdown view is generated from the JSON and never read back.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ante.core import canon, io

SCHEMA_VERSION = 1
INDEPENDENCE_LEVELS = ('SELF', 'SEPARATED_CONTEXT', 'INDEPENDENT_OPERATOR')
ARTIFACT_KEYS = ('schema_version', 'command', 'case_id', 'at', 'input_sha256', 'parents',
                 'independence_level', 'claims', 'body', 'findings', 'verdict', 'next_decision',
                 'artifact_sha256')


class LineageError(ValueError):
    """A parent artefact is unreadable, altered, or from another case. Exit 3."""


class Rejected(ValueError):
    """The input violates a doctrinal validation. Exit 2. Carries findings."""

    def __init__(self, findings: list[dict]):
        self.findings = findings
        super().__init__('; '.join(f"{f['code']} {f['path']}" for f in findings))


@dataclass
class Finding:
    severity: str
    code: str
    path: str
    message: str

    def as_dict(self) -> dict:
        return {'severity': self.severity, 'code': self.code, 'path': self.path, 'message': self.message}


@dataclass
class Findings:
    items: list[Finding] = field(default_factory=list)

    def error(self, code: str, path: str, message: str) -> None:
        self.items.append(Finding('ERROR', code, path, message))

    def warn(self, code: str, path: str, message: str) -> None:
        self.items.append(Finding('WARN', code, path, message))

    def raise_errors(self) -> None:
        errors = [f.as_dict() for f in self.items if f.severity == 'ERROR']
        if errors:
            raise Rejected(errors)

    def warnings(self) -> list[dict]:
        return [f.as_dict() for f in self.items if f.severity == 'WARN']


def seal(artifact: dict) -> dict:
    body = {key: artifact[key] for key in ARTIFACT_KEYS if key != 'artifact_sha256'}
    return {**body, 'artifact_sha256': canon.digest(body)}


def verify_self(artifact: Any, label: str) -> dict:
    if not isinstance(artifact, dict) or set(artifact) != set(ARTIFACT_KEYS):
        raise LineageError(f'{label}: not an ante artefact')
    if artifact.get('schema_version') != SCHEMA_VERSION:
        raise LineageError(f'{label}: unsupported schema_version')
    expected = canon.digest({key: artifact[key] for key in ARTIFACT_KEYS if key != 'artifact_sha256'})
    if artifact['artifact_sha256'] != expected:
        raise LineageError(f'{label}: content does not match artifact_sha256 (altered after sealing)')
    return artifact


def load_parent(path: Path | str) -> dict:
    target = Path(path)
    try:
        artifact = io.load_json(target)
    except io.InputError as exc:
        raise LineageError(str(exc)) from None
    return verify_self(artifact, target.name)


@dataclass
class Lineage:
    parents: list[dict]

    @classmethod
    def from_paths(cls, paths: list[str]) -> 'Lineage':
        parents = [load_parent(p) for p in paths]
        cases = {p['case_id'] for p in parents}
        if len(cases) > 1:
            raise LineageError('parents belong to different cases')
        hashes = [p['artifact_sha256'] for p in parents]
        if len(hashes) != len(set(hashes)):
            raise LineageError('the same parent artefact was supplied twice')
        return cls(parents)

    @property
    def case_id(self) -> str | None:
        return self.parents[0]['case_id'] if self.parents else None

    def of(self, command: str) -> list[dict]:
        return [p for p in self.parents if p['command'] == command]

    def one(self, command: str) -> dict | None:
        found = self.of(command)
        if len(found) > 1:
            raise LineageError(f'more than one {command} artefact supplied; pass the one this step builds on')
        return found[0] if found else None

    def require(self, *commands: str) -> None:
        missing = [c for c in commands if not self.of(c)]
        if missing:
            raise LineageError(f'lineage needs a {", ".join(missing)} artefact (--from)')

    def refs(self) -> list[dict]:
        return sorted(({'command': p['command'], 'artifact_sha256': p['artifact_sha256']} for p in self.parents),
                      key=lambda r: (r['command'], r['artifact_sha256']))

    def prior_claims(self) -> dict[str, list[dict]]:
        """Claims already recorded upstream, by id (several parents may carry one id)."""
        found: dict[str, list[dict]] = {}
        for parent in self.parents:
            for claim in parent['claims']:
                found.setdefault(claim['id'], []).append(claim)
        return found


def to_markdown(artifact: dict) -> str:
    lines = [f"# ante {artifact['command']} — {artifact['case_id']}", '',
             '| Field | Value |', '|---|---|',
             f"| Decision time | {artifact['at']} |",
             f"| Verdict | {artifact['verdict'] or '—'} |",
             f"| Independence | {artifact['independence_level'] or '—'} |",
             f"| Input SHA-256 | `{artifact['input_sha256']}` |",
             f"| Artefact SHA-256 | `{artifact['artifact_sha256']}` |", '']
    if artifact['parents']:
        lines += ['## Lineage', ''] + [f"- {p['command']} `{p['artifact_sha256']}`" for p in artifact['parents']] + ['']
    if artifact['claims']:
        lines += ['## Claims', '', '| Id | Status | Claim | Source | Date | Limit |', '|---|---|---|---|---|---|']
        for c in artifact['claims']:
            source = c['source'].get('ref', '') if isinstance(c['source'], dict) else c['source']
            lines.append(f"| {c['id']} | {c['status']} | {_cell(c['text'])} | {_cell(source)} | {c['date']} | {_cell(c['limit'])} |")
        lines.append('')
    lines += ['## Content', '', '```json', json.dumps(artifact['body'], indent=2, ensure_ascii=False), '```', '']
    if artifact['findings']:
        lines += ['## Findings', ''] + [f"- **{f['severity']}** `{f['code']}` {f['path']}: {f['message']}"
                                        for f in artifact['findings']] + ['']
    lines += ['## Next decision', '', artifact['next_decision'], '']
    return '\n'.join(lines)


def _cell(value: Any) -> str:
    return str(value).replace('|', '\\|').replace('\n', ' ')

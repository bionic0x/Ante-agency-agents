"""What every strategy command shares: input envelope, context and the run loop.

Input envelope (JSON or YAML)::

    {
      "at": "2026-10-28T12:00:00Z",          # optional if --at is given
      "independence_level": "SELF",          # review commands only
      "claims": [ ... ],                     # see ante.strategy.claims
      ...command fields...
    }

A command validates its fields, records findings, and returns the body, the
verdict (if it decides) and the next decision. Errors block the artefact (exit 2);
warnings travel inside it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ante import doctrine as doctrine_mod
from ante.core import canon, schema
from ante.core import time as ante_time
from ante.strategy import claims as claims_mod
from ante.strategy.artifact import (INDEPENDENCE_LEVELS, SCHEMA_VERSION, Findings, Lineage, LineageError,
                                    seal)

ENVELOPE = ('at', 'claims', 'independence_level')


@dataclass
class Context:
    at: str
    lineage: Lineage
    doctrine: doctrine_mod.Doctrine
    findings: Findings
    claim_ids: set[str] = field(default_factory=set)
    claims: list[dict] = field(default_factory=list)

    def refs(self, value: Any, path: str, minimum: int = 0) -> list[str]:
        return claims_mod.refs(value, self.claim_ids, path, self.findings, minimum)

    def claim(self, claim_id: str) -> dict | None:
        for claim in self.claims:
            if claim['id'] == claim_id:
                return claim
        for found in self.lineage.prior_claims().get(claim_id, []):
            return found
        return None


@dataclass
class Result:
    body: dict
    next_decision: str
    verdict: str | None = None
    case_id: str | None = None


@dataclass(frozen=True)
class Command:
    name: str
    summary: str
    fields: tuple[str, ...]
    optional: tuple[str, ...] = ()
    parents: tuple[str, ...] = ()          # artefact kinds that must be in the lineage
    review: bool = False                   # declares independence_level
    root: bool = False                     # starts a lineage (frame, selftest)
    run: Callable[[dict, Context], Result] | None = None


def resolve_at(doc: dict, cli_at: str | None) -> str:
    value = cli_at if cli_at is not None else doc.get('at')
    if value is None:
        schema.fail('at', 'decision time required: pass --at or set "at" in the input')
    try:
        return ante_time.iso(ante_time.parse(value, 'at'))
    except ante_time.TimeError as exc:
        schema.fail('at', str(exc).split(': ', 1)[-1])


def execute(command: Command, doc: Any, cli_at: str | None, parent_paths: list[str],
            doctrine: doctrine_mod.Doctrine) -> dict:
    schema.obj(doc, 'input')
    required = ('claims',) + command.fields + (('independence_level',) if command.review else ())
    schema.exact_keys(doc, required, 'input', ('at',) + command.optional)
    at = resolve_at(doc, cli_at)
    lineage = Lineage.from_paths(parent_paths)
    if command.root and lineage.parents:
        raise LineageError(f'{command.name} starts a lineage; it takes no --from')
    if not command.root and not lineage.parents:
        raise LineageError(f'{command.name} builds on earlier artefacts; pass them with --from')
    lineage.require(*command.parents)
    moment = ante_time.parse(at, 'at')
    for parent in lineage.parents:
        if ante_time.parse(parent['at'], 'parent.at') > moment:
            raise LineageError(f'parent {parent["command"]} is dated after this decision time')

    findings = Findings()
    prior = lineage.prior_claims()
    claims = claims_mod.validate(doc['claims'], doctrine.epistemic_states, prior, findings)
    ctx = Context(at=at, lineage=lineage, doctrine=doctrine, findings=findings,
                  claim_ids={c['id'] for c in claims} | set(prior), claims=claims)
    independence = None
    if command.review:
        independence = schema.enum(doc['independence_level'], INDEPENDENCE_LEVELS, 'independence_level')

    result = command.run(doc, ctx)
    findings.raise_errors()
    if result.verdict is not None:
        schema.enum(result.verdict, doctrine.decision_states, 'verdict')
    case_id = result.case_id or lineage.case_id
    input_doc = {key: value for key, value in doc.items() if key != 'at'}
    artifact = {
        'schema_version': SCHEMA_VERSION,
        'command': command.name,
        'case_id': case_id,
        'at': at,
        'input_sha256': canon.digest(input_doc),
        'parents': lineage.refs(),
        'independence_level': independence,
        'claims': claims,
        'body': result.body,
        'findings': findings.warnings(),
        'verdict': result.verdict,
        'next_decision': result.next_decision,
    }
    return seal(artifact)


def nonplaceholder(value: Any, path: str, findings: Findings, code: str = 'PLACEHOLDER') -> str | None:
    if claims_mod.placeholder(value):
        findings.error(code, path, 'a placeholder is not content')
        return None
    return value


def distinct_texts(values: dict[str, Any], path: str, findings: Findings, code: str) -> None:
    """Flag fields that repeat one statement (the same clause pasted into several slots)."""
    seen: dict[str, str] = {}
    for key, value in values.items():
        if not isinstance(value, str):
            continue
        norm = ' '.join(value.casefold().split())
        if norm in seen:
            findings.error(code, f'{path}.{key}', f'repeats {path}.{seen[norm]} word for word')
        else:
            seen[norm] = key

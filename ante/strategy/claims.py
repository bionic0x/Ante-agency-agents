"""Claim discipline shared by every command (invariants 2 and 7).

A claim is ``{id, text, status, source, date, limit}`` plus, when needed:

    intent    {capability, will}   required for ATTRIBUTED_INTENT: keeps what the
                                   actor *can* do apart from what it is said to *want*
    upgrade   {observation, could_have_refuted, source, date}
                                   required when a claim id that an upstream
                                   artefact recorded as ATTRIBUTED_INTENT becomes
                                   EVIDENCE here
    expires   ISO date or time after which the claim must be renewed

``source`` is ``{ref, origin}`` with ``origin`` one of:

    external   an observation from outside the system
    owner      a statement by the accountable human owner
    system     anything an Ante artefact, agent or model produced

Rules enforced here:
- statuses come from ``strategy/contracts.json``;
- ``EVIDENCE`` needs a non-placeholder source and a date, and its origin cannot
  be ``system``: the system's own output never corroborates itself;
- ``ATTRIBUTED_INTENT`` separates capability from will;
- ``ATTRIBUTED_INTENT`` rises to ``EVIDENCE`` only through an observation that
  could have refuted it, from a source the claim did not already rest on —
  repetition of the same source is not observation.
"""
from __future__ import annotations

from typing import Any

from ante.core import schema
from ante.core import time as ante_time
from ante.strategy.artifact import Findings

ORIGINS = ('external', 'owner', 'system')
PLACEHOLDERS = {'', 'tbd', 'todo', 'n/a', 'na', 'none', '-', '--', 'pending', 'unknown', 'tba', '?', '...', 'xxx'}
CLAIM_REQUIRED = ('id', 'text', 'status', 'source', 'date', 'limit')
CLAIM_OPTIONAL = ('intent', 'upgrade', 'expires', 'supersedes_note')


def placeholder(value: Any) -> bool:
    return not isinstance(value, str) or value.strip().casefold() in PLACEHOLDERS


def validate(claims: Any, states: tuple[str, ...], prior: dict[str, list[dict]],
             findings: Findings) -> list[dict]:
    schema.array(claims, 'claims')
    ids = set()
    for index, claim in enumerate(claims):
        path = f'claims[{index}]'
        schema.exact_keys(claim, CLAIM_REQUIRED, path, CLAIM_OPTIONAL)
        claim_id = schema.text(claim['id'], f'{path}.id')
        if claim_id in ids:
            findings.error('DUPLICATE_CLAIM', f'{path}.id', 'claim id used twice in one input')
        ids.add(claim_id)
        schema.text(claim['text'], f'{path}.text')
        status = schema.enum(claim['status'], states, f'{path}.status')
        source = schema.exact_keys(claim['source'], ('ref', 'origin'), f'{path}.source')
        schema.enum(source['origin'], ORIGINS, f'{path}.source.origin')
        schema.text(claim['limit'], f'{path}.limit')
        if claim['date'] is not None:
            _date(claim['date'], f'{path}.date')
        if 'expires' in claim:
            _date(claim['expires'], f'{path}.expires')

        if status == 'EVIDENCE':
            if placeholder(source['ref']):
                findings.error('EVIDENCE_WITHOUT_SOURCE', f'{path}.source.ref', 'evidence needs an identifiable source')
            if claim['date'] is None:
                findings.error('EVIDENCE_WITHOUT_DATE', f'{path}.date', 'evidence needs the date it was observed')
            if source['origin'] == 'system':
                findings.error('SELF_CORROBORATION', f'{path}.source.origin',
                               'a system-produced source cannot establish evidence; record it as HYPOTHESIS')
        if status == 'ATTRIBUTED_INTENT':
            intent = claim.get('intent')
            if not isinstance(intent, dict) or placeholder(intent.get('capability')) or placeholder(intent.get('will')):
                findings.error('INTENT_NOT_SEPARATED', f'{path}.intent',
                               'attributed intent must state capability and will separately')
            elif intent['capability'].strip().casefold() == intent['will'].strip().casefold():
                findings.error('INTENT_NOT_SEPARATED', f'{path}.intent', 'capability and will are the same statement')
        _check_transition(claim, prior.get(claim_id, []), path, findings)
    return claims


def _check_transition(claim: dict, earlier: list[dict], path: str, findings: Findings) -> None:
    was_intent = any(e['status'] == 'ATTRIBUTED_INTENT' for e in earlier)
    if not (was_intent and claim['status'] == 'EVIDENCE'):
        if 'upgrade' in claim and not was_intent:
            findings.warn('UNUSED_UPGRADE', f'{path}.upgrade', 'no upstream attributed intent to upgrade')
        return
    upgrade = claim.get('upgrade')
    if not isinstance(upgrade, dict):
        findings.error('INTENT_UPGRADE_WITHOUT_OBSERVATION', path,
                       'attributed intent becomes evidence only through an observation that could have refuted it')
        return
    schema.exact_keys(upgrade, ('observation', 'could_have_refuted', 'source', 'date'), f'{path}.upgrade')
    if placeholder(upgrade['observation']):
        findings.error('INTENT_UPGRADE_WITHOUT_OBSERVATION', f'{path}.upgrade.observation', 'observation required')
    if upgrade['could_have_refuted'] is not True:
        findings.error('INTENT_UPGRADE_UNFALSIFIABLE', f'{path}.upgrade.could_have_refuted',
                       'the observation must have been able to refute the attribution')
    _date(upgrade['date'], f'{path}.upgrade.date')
    used = {_ref(e['source']) for e in earlier} | {_ref(claim['source'])}
    if placeholder(upgrade['source']) or upgrade['source'] in used:
        findings.error('INTENT_UPGRADE_BY_REPETITION', f'{path}.upgrade.source',
                       'the upgrading observation repeats a source the claim already rested on')


def _ref(source: Any) -> str:
    return source.get('ref') if isinstance(source, dict) else str(source)


def _date(value: Any, path: str) -> None:
    if not isinstance(value, str):
        schema.fail(path, 'ISO date or timestamp required')
    if len(value) == 10:
        try:
            ante_time.parse(value + 'T00:00:00Z', path)
            return
        except ante_time.TimeError:
            schema.fail(path, 'ISO date or timestamp required')
    try:
        ante_time.parse(value, path)
    except ante_time.TimeError as exc:
        schema.fail(path, str(exc).split(': ', 1)[-1])


def refs(value: Any, known: set[str], path: str, findings: Findings, minimum: int = 0) -> list[str]:
    """Validate a list of claim ids that a body field rests on."""
    schema.array(value, path, minimum)
    for index, claim_id in enumerate(value):
        if not isinstance(claim_id, str) or claim_id not in known:
            findings.error('UNKNOWN_CLAIM', f'{path}[{index}]', 'refers to a claim id not declared in this input or upstream')
    return value

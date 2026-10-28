"""ante decide — the Strategic Decision Record.

The SDR (``strategy/templates/strategic-decision-record.md`` §9) as an artefact.
It records a human owner's decision; it grants no execution authority (invariant 1).

Rules:
- the lineage must contain ``frame``, ``cohere`` and ``pathology`` for this case,
  produced under the same doctrine table as the one in use;
- the verdict must be one ``cohere`` left admissible — a fatal defect removes
  ``PROCEED`` whatever else is true;
- ``PROCEED`` and ``PROCEED_WITH_CONDITIONS`` need a valid ``close`` artefact
  (the termination is designed before the commitment, XII) and dated expectations;
- ``PROCEED`` needs no detected pathology and an ``INDEPENDENT_OPERATOR``
  coherence review; a review by the proposer or its context is a coherence
  function, not a barrier (invariant 10, decision D-010);
- conditional, held and redesigned outputs state their conditions;
- dissent is recorded, or the record names who was asked for it;
- the residual risk has a named acceptor, and the record expires.

The record carries a frozen ``snapshot`` of what was known at decision time
(parents, every visible claim with its status and origin, the expectations);
``ante learn`` reconciles and calibrates against that snapshot only
(``ante/constructs``, Marco I.10).

Input fields::

    decision_owner, verdict, rationale, conditions: [text],
    dissent: [{by, objection, evidence: [claim id], response}], dissent_solicited_from: [text],
    residual_risk: {statement, accepted_by}, expires,
    expectations: [{id, what_should_change, in_whom, horizon, refuted_by,
                    probability: {verbal, interval: [low, high]}, kind?}]
                  ``kind`` labels the type of claim for calibration (``ante learn calibrate``)
"""
from __future__ import annotations

from ante.constructs import snapshot as snapshot_mod
from ante.core import canon, schema
from ante.core import time as ante_time
from ante.strategy.artifact import LineageError
from ante.strategy.base import Command, Result, nonplaceholder

AUTHORITY_NOTE = ('This record does not itself grant production, legal, financial, security or other '
                  'real-world execution authority.')
ACTIVATING = ('PROCEED', 'PROCEED_WITH_CONDITIONS')


def _expectations(value, ctx):
    findings = ctx.findings
    items = schema.array(value, 'expectations')
    schema.unique_ids(items, 'expectations')
    for index, item in enumerate(items):
        path = f'expectations[{index}]'
        schema.exact_keys(item, ('id', 'what_should_change', 'in_whom', 'horizon', 'refuted_by', 'probability'), path,
                          ('kind',))
        if 'kind' in item:
            nonplaceholder(item['kind'], f'{path}.kind', findings)
        for key in ('what_should_change', 'in_whom', 'refuted_by'):
            nonplaceholder(item[key], f'{path}.{key}', findings, 'UNTESTABLE_EXPECTATION')
        ante_time.parse(item['horizon'], f'{path}.horizon')
        prob = schema.exact_keys(item['probability'], ('verbal', 'interval'), f'{path}.probability')
        nonplaceholder(prob['verbal'], f'{path}.probability.verbal', findings)
        interval = schema.array(prob['interval'], f'{path}.probability.interval', 2)
        if len(interval) != 2:
            schema.fail(f'{path}.probability.interval', 'exactly [low, high] required')
        low = schema.number(interval[0], f'{path}.probability.interval[0]', 0, 1)
        high = schema.number(interval[1], f'{path}.probability.interval[1]', 0, 1)
        schema.require(low <= high, f'{path}.probability.interval', 'low must not exceed high')
    return items


def run(doc, ctx):
    findings = ctx.findings
    frame = ctx.lineage.one('frame')
    cohere = ctx.lineage.one('cohere')
    pathology = ctx.lineage.one('pathology')
    close = ctx.lineage.one('close')
    doctrine_hash = canon.digest(ctx.doctrine.raw)
    for artefact in (cohere, pathology):
        if artefact['body']['doctrine_sha256'] != doctrine_hash:
            raise LineageError(f'{artefact["command"]} was produced under another doctrine table')

    owner = nonplaceholder(doc['decision_owner'], 'decision_owner', findings, 'NO_DECISION_OWNER')
    verdict = schema.enum(doc['verdict'], ctx.doctrine.decision_states, 'verdict')
    nonplaceholder(doc['rationale'], 'rationale', findings)
    admissible = cohere['body']['admissible_verdicts']
    if verdict not in admissible:
        findings.error('VERDICT_NOT_ADMISSIBLE', 'verdict',
                       f'coherence review leaves only {", ".join(admissible)}')
    conditions = schema.array(doc['conditions'], 'conditions')
    for index, condition in enumerate(conditions):
        nonplaceholder(condition, f'conditions[{index}]', findings)
    if verdict in ('PROCEED_WITH_CONDITIONS', 'HOLD', 'REDESIGN') and not conditions:
        findings.error('CONDITIONS_MISSING', 'conditions', f'{verdict} must state its conditions')

    detected = [p['id'] for p in pathology['body']['detected']]
    if verdict in ACTIVATING:
        if close is None:
            findings.error('NO_TERMINATION_CONTRACT', 'verdict',
                           f'{verdict} needs a close artefact in the lineage (termination designed before commitment)')
    if verdict == 'PROCEED':
        if detected:
            findings.error('PATHOLOGY_UNADDRESSED', 'verdict',
                           f'detected pathologies ({", ".join(detected)}) cannot coexist with an unconditional PROCEED')
        if cohere['independence_level'] != 'INDEPENDENT_OPERATOR':
            findings.error('REVIEW_NOT_INDEPENDENT', 'verdict',
                           f'coherence review is {cohere["independence_level"]}: a coherence function, not an '
                           'independent barrier; PROCEED needs INDEPENDENT_OPERATOR (or decide '
                           'PROCEED_WITH_CONDITIONS with independent review as a condition)')

    dissent = schema.array(doc['dissent'], 'dissent')
    for index, item in enumerate(dissent):
        path = f'dissent[{index}]'
        schema.exact_keys(item, ('by', 'objection', 'evidence', 'response'), path)
        for key in ('by', 'objection', 'response'):
            nonplaceholder(item[key], f'{path}.{key}', findings, 'DISSENT_NOT_RECORDED')
        ctx.refs(item['evidence'], f'{path}.evidence')
    solicited = schema.array(doc['dissent_solicited_from'], 'dissent_solicited_from')
    if not dissent and not solicited:
        findings.error('DISSENT_NOT_SOLICITED', 'dissent', 'record the dissent or who was asked for it (VIII.9)')

    risk = schema.exact_keys(doc['residual_risk'], ('statement', 'accepted_by'), 'residual_risk')
    nonplaceholder(risk['statement'], 'residual_risk.statement', findings)
    nonplaceholder(risk['accepted_by'], 'residual_risk.accepted_by', findings, 'RISK_WITHOUT_ACCEPTOR')
    expires = ante_time.parse(doc['expires'], 'expires')
    if expires <= ante_time.parse(ctx.at, 'at'):
        findings.error('ALREADY_EXPIRED', 'expires', 'the record must expire after its decision time')
    expectations = _expectations(doc['expectations'], ctx)
    if verdict in ACTIVATING and not expectations:
        findings.error('NO_DATED_EXPECTATIONS', 'expectations',
                       'an activating decision records what should change and what would refute it (I.10, VIII.13)')

    body = {
        'case': frame['body']['case'],
        'decision_owner': owner,
        'verdict': verdict,
        'rationale': doc['rationale'],
        'conditions': conditions,
        'admissible_verdicts': admissible,
        'review_independence': cohere['independence_level'],
        'detected_pathologies': detected,
        'termination_contract': close['body']['termination_contract'] if close else None,
        'dissent': dissent,
        'dissent_solicited_from': solicited,
        'residual_risk': risk,
        'expires': ante_time.iso(expires),
        'expectations': expectations,
        'authority': AUTHORITY_NOTE,
        'snapshot': snapshot_mod.build(ctx.at, ctx.lineage.parents, ctx.claims, expectations, verdict),
    }
    next_decision = {
        'PROCEED': 'Authorised work may start under the owner\'s own authority; record outcomes with ante learn reconcile.',
        'PROCEED_WITH_CONDITIONS': 'Satisfy each condition before the gated commitment; preparatory work only.',
        'HOLD': 'Resolve the stated conditions, then re-run cohere and decide.',
        'REDESIGN': 'Return to map, cause or options with the objective unchanged.',
        'REJECT': 'Close or redefine the proposal.',
    }[verdict]
    return Result(body=body, verdict=verdict, next_decision=next_decision)


COMMAND = Command(
    name='decide', summary='Strategic Decision Record bound to cohere, pathology and close',
    fields=('decision_owner', 'verdict', 'rationale', 'conditions', 'dissent', 'dissent_solicited_from',
            'residual_risk', 'expires', 'expectations'),
    parents=('frame', 'cohere', 'pathology'), run=run)

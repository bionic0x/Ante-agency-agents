"""ante frame — end state, minimum acceptable result, limits and termination criteria.

Marco XIII phase 1 and chapter I. An objective without an observable condition is
rejected: that is pathology 2 (*nominal objective*), and every later command would
inherit it.

Input fields::

    case                {id, title}
    end_state           {statement, observable_condition, horizon}
    minimum_acceptable  {statement, observable_condition}
    beneficiaries       [text]          who receives the benefit
    cost_bearers        [text]          who bears the cost
    limits              [{kind, statement}]   kind: ethical | legal | cost | time | other
    termination_criteria [text]
    basis               [claim id]      claims the framing rests on

``observable_condition`` is ``{indicator, threshold, observed_by}``: what is
measured or seen, the value or state that counts, and who can see it.
"""
from __future__ import annotations

import re

from ante.core import schema
from ante.strategy.base import Command, Result, distinct_texts, nonplaceholder

LIMIT_KINDS = ('ethical', 'legal', 'cost', 'time', 'other')
CASE_ID = re.compile(r'^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$')


def _condition(value, path, ctx):
    findings = ctx.findings
    if not isinstance(value, dict):
        findings.error('NOMINAL_OBJECTIVE', path,
                       'objective has no observable condition {indicator, threshold, observed_by} (pathology 2)')
        return
    schema.exact_keys(value, ('indicator', 'threshold', 'observed_by'), path)
    for key in ('indicator', 'threshold', 'observed_by'):
        nonplaceholder(value[key], f'{path}.{key}', findings, 'NOMINAL_OBJECTIVE')
    distinct_texts(value, path, findings, 'NOMINAL_OBJECTIVE')


def run(doc, ctx):
    findings = ctx.findings
    case = schema.exact_keys(doc['case'], ('id', 'title'), 'case')
    if not isinstance(case['id'], str) or not CASE_ID.match(case['id']):
        schema.fail('case.id', 'lower-case slug of 3-64 characters required')
    schema.text(case['title'], 'case.title')

    end = schema.exact_keys(doc['end_state'], ('statement', 'observable_condition', 'horizon'), 'end_state')
    nonplaceholder(end['statement'], 'end_state.statement', findings)
    nonplaceholder(end['horizon'], 'end_state.horizon', findings)
    _condition(end['observable_condition'], 'end_state.observable_condition', ctx)

    minimum = schema.exact_keys(doc['minimum_acceptable'], ('statement', 'observable_condition'), 'minimum_acceptable')
    nonplaceholder(minimum['statement'], 'minimum_acceptable.statement', findings)
    _condition(minimum['observable_condition'], 'minimum_acceptable.observable_condition', ctx)
    if (isinstance(end['statement'], str) and isinstance(minimum['statement'], str)
            and end['statement'].strip().casefold() == minimum['statement'].strip().casefold()):
        findings.warn('NO_SUFFICIENCY_RANGE', 'minimum_acceptable.statement',
                      'minimum equals the end state: there is no sufficient result short of full success (I.9)')

    for key in ('beneficiaries', 'cost_bearers', 'termination_criteria'):
        for index, item in enumerate(schema.array(doc[key], key, 1)):
            nonplaceholder(item, f'{key}[{index}]', findings)
    for index, limit in enumerate(schema.array(doc['limits'], 'limits', 1)):
        schema.exact_keys(limit, ('kind', 'statement'), f'limits[{index}]')
        schema.enum(limit['kind'], LIMIT_KINDS, f'limits[{index}].kind')
        nonplaceholder(limit['statement'], f'limits[{index}].statement', findings)
    if not any(isinstance(l, dict) and l.get('kind') in ('ethical', 'legal') for l in doc['limits']):
        findings.warn('NO_ADMISSIBILITY_LIMIT', 'limits',
                      'no ethical or legal limit declared; admissibility is not a score to trade (nota metodológica)')
    ctx.refs(doc['basis'], 'basis')

    body = {key: doc[key] for key in ('case', 'end_state', 'minimum_acceptable', 'beneficiaries',
                                      'cost_bearers', 'limits', 'termination_criteria', 'basis')}
    return Result(body=body, case_id=case['id'],
                  next_decision='Map actors, authority and dependencies against this end state (ante map).')


COMMAND = Command(
    name='frame', summary='end state, minimum acceptable result, limits, termination criteria',
    fields=('case', 'end_state', 'minimum_acceptable', 'beneficiaries', 'cost_bearers', 'limits',
            'termination_criteria', 'basis'),
    root=True, run=run)

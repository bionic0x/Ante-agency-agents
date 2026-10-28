"""ante watch — thresholds bound to responses, reserve with conditions of use.

Marco XIII phase 7 and VI.9. An indicator with no decision attached is a
description, not a control: it is refused. At least one threshold must stop or
pause the course, otherwise every observation becomes a reason to continue. The
reserve states the contingency it covers and how long it takes to engage (V.7).

Input fields::

    thresholds   [{id, indicator, kind, threshold, response, owner, effect_lag}]
                 kind: leading | lagging        response: continue | adjust | pause | terminate
    reserve      {what, contingency, time_to_engage, cost_of_not_using}
    culmination  {signal, review_question}       VI.9: when more effort stops converting
"""
from __future__ import annotations

from ante.core import schema
from ante.strategy.base import Command, Result, nonplaceholder
from ante.strategy.claims import placeholder

KINDS = ('leading', 'lagging')
RESPONSES = ('continue', 'adjust', 'pause', 'terminate')


def run(doc, ctx):
    findings = ctx.findings
    thresholds = schema.array(doc['thresholds'], 'thresholds', 1)
    schema.unique_ids(thresholds, 'thresholds')
    responses, kinds = [], []
    for index, item in enumerate(thresholds):
        path = f'thresholds[{index}]'
        if not isinstance(item, dict) or 'response' not in item or placeholder(item.get('response')):
            findings.error('INDICATOR_WITHOUT_DECISION', path, 'every indicator must be bound to a response')
            continue
        schema.exact_keys(item, ('id', 'indicator', 'kind', 'threshold', 'response', 'owner', 'effect_lag'), path)
        nonplaceholder(item['indicator'], f'{path}.indicator', findings)
        kinds.append(schema.enum(item['kind'], KINDS, f'{path}.kind'))
        nonplaceholder(item['threshold'], f'{path}.threshold', findings)
        responses.append(schema.enum(item['response'], RESPONSES, f'{path}.response'))
        nonplaceholder(item['owner'], f'{path}.owner', findings, 'THRESHOLD_WITHOUT_OWNER')
        nonplaceholder(item['effect_lag'], f'{path}.effect_lag', findings)
    if responses and not set(responses) & {'pause', 'terminate'}:
        findings.error('NO_STOPPING_THRESHOLD', 'thresholds',
                       'no threshold pauses or terminates: every observation becomes a reason to continue')
    if kinds and 'leading' not in kinds:
        findings.warn('ONLY_LAGGING', 'thresholds',
                      'only lagging indicators: the deterioration is confirmed after it happened (VI.4)')
    reserve = schema.exact_keys(doc['reserve'], ('what', 'contingency', 'time_to_engage', 'cost_of_not_using'),
                                'reserve')
    for key in reserve:
        nonplaceholder(reserve[key], f'reserve.{key}', findings, 'RESERVE_WITHOUT_PURPOSE')
    culmination = schema.exact_keys(doc['culmination'], ('signal', 'review_question'), 'culmination')
    for key in culmination:
        nonplaceholder(culmination[key], f'culmination.{key}', findings)
    body = {key: doc[key] for key in COMMAND.fields}
    return Result(body=body, next_decision='Write the termination contract before committing (ante close).')


COMMAND = Command(name='watch', summary='thresholds bound to responses, reserve, culmination signal',
                  fields=('thresholds', 'reserve', 'culmination'), parents=('options',), run=run)

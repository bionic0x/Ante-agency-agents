"""ante cause — the causal hypothesis, its rival and what would refute it.

Marco XIII phase 3 and I.3: "if we do X, we expect Y because Z changes, provided
that …". A causal chain without a rival explanation and without an observable
refutation is a belief, not a hypothesis (VIII.4).

Input fields::

    chain        {if, then, because, provided_that: [text], immediate_effect, final_result}
    rivals       [{id, explanation, discriminating_evidence}]       at least one
    refutations  [{observation, horizon, observed_by}]              at least one
    basis        [claim id]

``discriminating_evidence`` must say what would distinguish the rival from the
main hypothesis; an explanation that predicts the same observations everywhere
discriminates nothing.
"""
from __future__ import annotations

from ante.core import schema
from ante.strategy.base import Command, Result, distinct_texts, nonplaceholder


def run(doc, ctx):
    findings = ctx.findings
    chain = schema.exact_keys(doc['chain'], ('if', 'then', 'because', 'provided_that', 'immediate_effect',
                                             'final_result'), 'chain')
    for key in ('if', 'then', 'because', 'immediate_effect', 'final_result'):
        nonplaceholder(chain[key], f'chain.{key}', findings, 'NO_MECHANISM')
    distinct_texts({k: chain[k] for k in ('if', 'then', 'because')}, 'chain', findings, 'NO_MECHANISM')
    for index, condition in enumerate(schema.array(chain['provided_that'], 'chain.provided_that', 1)):
        nonplaceholder(condition, f'chain.provided_that[{index}]', findings)
    if (isinstance(chain['immediate_effect'], str) and isinstance(chain['final_result'], str)
            and chain['immediate_effect'].strip().casefold() == chain['final_result'].strip().casefold()):
        findings.warn('EFFECT_IS_RESULT', 'chain.final_result',
                      'immediate effect and final result are the same statement (I.4: product is not result)')

    rivals = schema.array(doc['rivals'], 'rivals', 1)
    schema.unique_ids(rivals, 'rivals')
    for index, rival in enumerate(rivals):
        path = f'rivals[{index}]'
        schema.exact_keys(rival, ('id', 'explanation', 'discriminating_evidence'), path)
        nonplaceholder(rival['explanation'], f'{path}.explanation', findings, 'NO_RIVAL')
        nonplaceholder(rival['discriminating_evidence'], f'{path}.discriminating_evidence', findings,
                       'RIVAL_NOT_DISCRIMINATED')
        if isinstance(rival['explanation'], str) and isinstance(chain['because'], str) and \
                rival['explanation'].strip().casefold() == chain['because'].strip().casefold():
            findings.error('RIVAL_IS_MAIN', f'{path}.explanation', 'the rival restates the main mechanism')

    for index, ref in enumerate(schema.array(doc['refutations'], 'refutations', 1)):
        path = f'refutations[{index}]'
        schema.exact_keys(ref, ('observation', 'horizon', 'observed_by'), path)
        for key in ('observation', 'horizon', 'observed_by'):
            nonplaceholder(ref[key], f'{path}.{key}', findings, 'UNOBSERVABLE_REFUTATION')
    ctx.refs(doc['basis'], 'basis')
    body = {key: doc[key] for key in COMMAND.fields}
    return Result(body=body, next_decision='Locate the decisive dependency and the main effort (ante focus).')


COMMAND = Command(name='cause', summary='causal chain, rival hypothesis, observable refutations',
                  fields=('chain', 'rivals', 'refutations', 'basis'), parents=('frame',), run=run)

"""ante close — the termination contract.

Marco XII and XIII phase 8. The contract uses the runbook vocabulary already
enforced by ``scripts/check-runbooks.sh`` (``achieved``, ``outstanding``,
``accountable``, ``on_breach``, ``conservation_resources``, ``revision_conditions``)
plus the type of ending (XII.1 table):

    cessation            the conduct that produced the confrontation stops
    closure_decision     conditions to resolve or bound the dispute are set
    executed_transition  transfers, guarantees and first obligations are done
    conservation         the result works under ordinary conditions

Refused: placeholders (``TBD``, ``n/a`` …) and a single clause pasted into several
fields — a contract that says one thing six times has one clause, not six.
Each transition step states the exposure it creates and how it is verified (XII.3–4).

Input fields::

    termination_contract  {type, achieved, outstanding, accountable, on_breach,
                           conservation_resources, revision_conditions}
    transition            [{step, exposure, guarantee, verification}]
"""
from __future__ import annotations

from ante.core import schema
from ante.strategy.base import Command, Result, distinct_texts, nonplaceholder

TYPES = ('cessation', 'closure_decision', 'executed_transition', 'conservation')
CLAUSES = ('achieved', 'outstanding', 'accountable', 'on_breach', 'conservation_resources', 'revision_conditions')


def run(doc, ctx):
    findings = ctx.findings
    contract = schema.exact_keys(doc['termination_contract'], ('type',) + CLAUSES, 'termination_contract')
    schema.enum(contract['type'], TYPES, 'termination_contract.type')
    for clause in CLAUSES:
        nonplaceholder(contract[clause], f'termination_contract.{clause}', findings, 'PLACEHOLDER_CLAUSE')
    distinct_texts({c: contract[c] for c in CLAUSES}, 'termination_contract', findings, 'SINGLE_CLAUSE')
    steps = schema.array(doc['transition'], 'transition', 1)
    for index, step in enumerate(steps):
        path = f'transition[{index}]'
        schema.exact_keys(step, ('step', 'exposure', 'guarantee', 'verification'), path)
        for key in ('step', 'exposure', 'guarantee', 'verification'):
            nonplaceholder(step[key], f'{path}.{key}', findings, 'UNGUARDED_TRANSITION')
    body = {'termination_contract': contract, 'transition': steps}
    return Result(body=body, next_decision='Run the seven coherence tests on the whole plan (ante cohere).')


COMMAND = Command(name='close', summary='termination contract: type, clauses, guarded transition',
                  fields=('termination_contract', 'transition'), parents=('frame',), run=run)

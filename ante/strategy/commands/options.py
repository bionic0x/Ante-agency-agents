"""ante options — courses of action that differ in mechanism, continuity included.

Marco XIII phase 5 and Appendix B. Options must differ in *how* they produce the
effect, not only in intensity, and the continuity baseline (keep doing what we do)
is always one of them, with its costs. A set made of one viable option and
decoys offers no choice: it is refused. Nothing is scored; the comparison is a
table of conditions and trade-offs.

Input fields::

    options    [{id, kind, mechanism, viable, why_not_viable?, resources, reversibility,
                 distribution_of_effects, sustainability, assumptions: [claim id]}]
               kind: continuity | alternative     reversibility: high | medium | low
    criteria   [text]   comparison rows (Appendix B), e.g. "legitimacy", "reserve preserved"
    comparison {option id: {criterion: text}}   every option × every criterion
    preferred  {option, reason, conditional_on: [text]}
"""
from __future__ import annotations

from ante.core import schema
from ante.strategy.base import Command, Result, nonplaceholder

KINDS = ('continuity', 'alternative')
REVERSIBILITY = ('high', 'medium', 'low')
OPTION_KEYS = ('id', 'kind', 'mechanism', 'viable', 'resources', 'reversibility', 'distribution_of_effects',
               'sustainability', 'assumptions')


def run(doc, ctx):
    findings = ctx.findings
    options = schema.array(doc['options'], 'options', 2)
    ids = schema.unique_ids(options, 'options')
    mechanisms: dict[str, str] = {}
    viable = []
    for index, option in enumerate(options):
        path = f'options[{index}]'
        schema.exact_keys(option, OPTION_KEYS, path, ('why_not_viable',))
        kind = schema.enum(option['kind'], KINDS, f'{path}.kind')
        mechanism = nonplaceholder(option['mechanism'], f'{path}.mechanism', findings, 'NO_MECHANISM')
        if mechanism:
            norm = ' '.join(mechanism.casefold().split())
            if norm in mechanisms:
                findings.error('SAME_MECHANISM', f'{path}.mechanism',
                               f'same mechanism as {mechanisms[norm]}: options must differ in how, not how much')
            mechanisms[norm] = option['id']
        if schema.boolean(option['viable'], f'{path}.viable'):
            if kind == 'alternative':
                viable.append(option['id'])
            if 'why_not_viable' in option:
                schema.fail(f'{path}.why_not_viable', 'only for options declared not viable')
        else:
            nonplaceholder(option.get('why_not_viable'), f'{path}.why_not_viable', findings, 'UNEXPLAINED_DECOY')
        for key in ('resources', 'distribution_of_effects', 'sustainability'):
            nonplaceholder(option[key], f'{path}.{key}', findings)
        schema.enum(option['reversibility'], REVERSIBILITY, f'{path}.reversibility')
        ctx.refs(option['assumptions'], f'{path}.assumptions')

    continuity = [o for o in options if isinstance(o, dict) and o.get('kind') == 'continuity']
    if len(continuity) != 1:
        findings.error('NO_CONTINUITY_BASELINE', 'options', 'exactly one continuity baseline is required')
    if len(viable) < 2:
        findings.error('DECOY_SET', 'options',
                       f'{len(viable)} viable alternative(s) besides continuity; a choice needs at least two')

    criteria = schema.array(doc['criteria'], 'criteria', 3)
    for index, criterion in enumerate(criteria):
        nonplaceholder(criterion, f'criteria[{index}]', findings)
    comparison = schema.obj(doc['comparison'], 'comparison')
    if set(comparison) != set(ids):
        findings.error('INCOMPLETE_COMPARISON', 'comparison', 'every option needs a comparison column')
    for option_id, row in comparison.items():
        schema.obj(row, f'comparison.{option_id}')
        if set(row) != set(criteria):
            findings.error('INCOMPLETE_COMPARISON', f'comparison.{option_id}', 'every criterion needs an entry')
        for criterion, text in row.items():
            nonplaceholder(text, f'comparison.{option_id}.{criterion}', findings, 'INCOMPLETE_COMPARISON')
        if any(isinstance(v, (int, float)) and not isinstance(v, bool) for v in row.values()):
            findings.error('WEIGHTED_SCORE', f'comparison.{option_id}', 'the matrix compares conditions; no scores')

    preferred = schema.exact_keys(doc['preferred'], ('option', 'reason', 'conditional_on'), 'preferred')
    if preferred['option'] not in ids:
        findings.error('UNKNOWN_OPTION', 'preferred.option', 'not one of the options')
    elif preferred['option'] not in viable and preferred['option'] not in [o['id'] for o in continuity]:
        findings.error('PREFERRED_NOT_VIABLE', 'preferred.option', 'the preferred option is declared not viable')
    nonplaceholder(preferred['reason'], 'preferred.reason', findings)
    schema.array(preferred['conditional_on'], 'preferred.conditional_on', 1)

    body = {key: doc[key] for key in COMMAND.fields}
    return Result(body=body, next_decision='Test the options against competent reactions (ante react).')


COMMAND = Command(name='options', summary='options that differ in mechanism, continuity baseline included',
                  fields=('options', 'criteria', 'comparison', 'preferred'), parents=('cause',), run=run)

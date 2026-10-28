"""ante react — competent reactions, third-party shifts and their activation signals.

Marco XIII phase 6, chapters VI and IX. The plan is tested against a competent
adversary, against a third party that changes its stance, and against the
reaction planners forget: unexpected *cooperation*, which can make the rest of
the plan unnecessary (continuing by inertia after it is also a failure). Each
reaction carries the signal that would show it is happening and the decision it
would trigger.

Input fields::

    reactions [{id, actor, kind, against_option, description, incentive,
                information_revealed, capacity_required, activation_signal,
                contingent_decision, changes_choice}]
              kind: opposition | cooperation | third_party_shift | adaptation
              contingent_decision: continue | adjust | pause | terminate
"""
from __future__ import annotations

from ante.core import schema
from ante.strategy.base import Command, Result, nonplaceholder

KINDS = ('opposition', 'cooperation', 'third_party_shift', 'adaptation')
DECISIONS = ('continue', 'adjust', 'pause', 'terminate')
FIELDS = ('id', 'actor', 'kind', 'against_option', 'description', 'incentive', 'information_revealed',
          'capacity_required', 'activation_signal', 'contingent_decision', 'changes_choice')


def run(doc, ctx):
    findings = ctx.findings
    options_artifact = ctx.lineage.one('options')
    option_ids = {o['id'] for o in options_artifact['body']['options']}
    reactions = schema.array(doc['reactions'], 'reactions', 3)
    schema.unique_ids(reactions, 'reactions')
    kinds = []
    for index, reaction in enumerate(reactions):
        path = f'reactions[{index}]'
        schema.exact_keys(reaction, FIELDS, path)
        kinds.append(schema.enum(reaction['kind'], KINDS, f'{path}.kind'))
        if reaction['against_option'] not in option_ids:
            findings.error('UNKNOWN_OPTION', f'{path}.against_option', 'not an option of the parent artefact')
        for key in ('actor', 'description', 'incentive', 'information_revealed', 'capacity_required'):
            nonplaceholder(reaction[key], f'{path}.{key}', findings)
        nonplaceholder(reaction['activation_signal'], f'{path}.activation_signal', findings, 'NO_ACTIVATION_SIGNAL')
        schema.enum(reaction['contingent_decision'], DECISIONS, f'{path}.contingent_decision')
        schema.boolean(reaction['changes_choice'], f'{path}.changes_choice')
    for required, code in (('opposition', 'NO_COMPETENT_OPPOSITION'), ('cooperation', 'NO_UNEXPECTED_COOPERATION'),
                           ('third_party_shift', 'NO_THIRD_PARTY_SHIFT')):
        if required not in kinds:
            findings.error(code, 'reactions', f'at least one {required} reaction is required (XIII F6)')
    if not any(isinstance(r, dict) and r.get('changes_choice') is True for r in reactions):
        findings.warn('PASSIVE_ENVIRONMENT', 'reactions',
                      'no reaction would change the choice: does the plan only work if others stay passive?')
    body = {'reactions': doc['reactions']}
    return Result(body=body, next_decision='Tie each indicator to a response before acting (ante watch).')


COMMAND = Command(name='react', summary='competent opposition, unexpected cooperation, third-party shifts',
                  fields=('reactions',), parents=('options',), run=run)

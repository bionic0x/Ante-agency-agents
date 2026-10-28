"""ante map — actors, authority, commitment capacity, dependencies and third parties.

Marco XIII phase 2 and chapter II. Each actor must keep three things apart that a
summary tends to fuse (II.2): what it *prefers*, on whose behalf it *represents*,
and what it can *commit to and enforce*. A map in which the three are one
sentence cannot tell resistance from a missing mandate.

Input fields::

    actors        [{id, kind, preference, representation, commitment_capacity,
                    affected_by, basis: [claim id]}]
                  kind: decider | executor | resource_holder | veto | affected | third_party
    dependencies  [{id, actor, resource, criticality, substitutes, substitution_time}]
                  criticality: critical | material | minor
    third_parties [{actor, role}]   role: mediator | arbiter | verifier | guarantor | audience
    formal_vs_effective  text       where the formal map and the observed one differ
"""
from __future__ import annotations

from ante.core import schema
from ante.strategy.base import Command, Result, distinct_texts, nonplaceholder

KINDS = ('decider', 'executor', 'resource_holder', 'veto', 'affected', 'third_party')
CRITICALITY = ('critical', 'material', 'minor')
ROLES = ('mediator', 'arbiter', 'verifier', 'guarantor', 'audience')


def run(doc, ctx):
    findings = ctx.findings
    actors = schema.array(doc['actors'], 'actors', 2)
    ids = schema.unique_ids(actors, 'actors')
    kinds = set()
    for index, actor in enumerate(actors):
        path = f'actors[{index}]'
        schema.exact_keys(actor, ('id', 'kind', 'preference', 'representation', 'commitment_capacity',
                                  'affected_by', 'basis'), path)
        kinds.add(schema.enum(actor['kind'], KINDS, f'{path}.kind'))
        for key in ('preference', 'representation', 'commitment_capacity', 'affected_by'):
            nonplaceholder(actor[key], f'{path}.{key}', findings, 'ACTOR_UNDIFFERENTIATED')
        distinct_texts({k: actor[k] for k in ('preference', 'representation', 'commitment_capacity')},
                       path, findings, 'ACTOR_UNDIFFERENTIATED')
        ctx.refs(actor['basis'], f'{path}.basis')
    if 'decider' not in kinds:
        findings.error('NO_DECIDER', 'actors', 'the map names nobody who can decide')
    if 'affected' not in kinds:
        findings.warn('NO_AFFECTED_PARTY', 'actors',
                      'nobody is mapped as affected; influence and legitimacy need separate criteria (II.3)')

    deps = schema.array(doc['dependencies'], 'dependencies', 1)
    schema.unique_ids(deps, 'dependencies')
    for index, dep in enumerate(deps):
        path = f'dependencies[{index}]'
        schema.exact_keys(dep, ('id', 'actor', 'resource', 'criticality', 'substitutes', 'substitution_time'), path)
        if dep['actor'] not in ids:
            findings.error('UNKNOWN_ACTOR', f'{path}.actor', 'dependency on an actor not in the map')
        nonplaceholder(dep['resource'], f'{path}.resource', findings)
        schema.enum(dep['criticality'], CRITICALITY, f'{path}.criticality')
        schema.array(dep['substitutes'], f'{path}.substitutes')
        nonplaceholder(dep['substitution_time'], f'{path}.substitution_time', findings, 'SUBSTITUTION_UNSTATED')
        if dep['criticality'] == 'critical' and not dep['substitutes']:
            findings.warn('SINGLE_POINT', path, 'critical dependency with no substitute: candidate for ante focus')

    for index, third in enumerate(schema.array(doc['third_parties'], 'third_parties')):
        path = f'third_parties[{index}]'
        schema.exact_keys(third, ('actor', 'role'), path)
        if third['actor'] not in ids:
            findings.error('UNKNOWN_ACTOR', f'{path}.actor', 'third party not in the map')
        schema.enum(third['role'], ROLES, f'{path}.role')
    nonplaceholder(doc['formal_vs_effective'], 'formal_vs_effective', findings, 'FORMAL_MAP_ONLY')

    body = {key: doc[key] for key in COMMAND.fields}
    return Result(body=body, next_decision='State the causal hypothesis and its rival (ante cause).')


COMMAND = Command(
    name='map', summary='actors, authority, commitment capacity, dependencies, third parties',
    fields=('actors', 'dependencies', 'third_parties', 'formal_vs_effective'),
    parents=('frame',), run=run)

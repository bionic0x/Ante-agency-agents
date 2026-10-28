"""ante focus — centre of gravity as a dependency hypothesis, main effort and renunciations.

Marco XIII phase 4 and chapter III. The candidate centre is traced through the
Strange chain (capability → requirement → vulnerability) and must pass the six
rows of matrix III.10. A centre without a substitution analysis and a horizon is
refused; so is a sheet where centre, decisive point, vulnerability and
Schwerpunkt are the same sentence (pathology 4, *concept confusion*). When no
dominant dependency exists the candidate is ``null`` and the reason is stated
(III.8): that is a result, not a gap.

Input fields::

    system           {name, scope, horizon}
    candidate        {id, description, kind} | null      kind: capacity | cohesion | both
    no_dominant_reason   text (only when candidate is null)
    capabilities     [{id, verb, description}]
    requirements     [{id, capability, description}]
    vulnerabilities  [{id, requirement, feasible_path, compensable_within_horizon}]
    matrix           {scope, dependency, transmission,
                      substitution: {alternatives: [text], time}, conversion, revision}
    decisive_point   {statement, enables}
    schwerpunkt      {focus, renunciations: [text], minimums: [text]}
    own_dependencies [text]          what our own action depends on (III.9)
    basis            [claim id]
"""
from __future__ import annotations

from ante.core import schema
from ante.strategy.base import Command, Result, nonplaceholder

KINDS = ('capacity', 'cohesion', 'both')
MATRIX = ('scope', 'dependency', 'transmission', 'substitution', 'conversion', 'revision')


def _norm(value):
    return ' '.join(value.casefold().split()) if isinstance(value, str) else None


def run(doc, ctx):
    findings = ctx.findings
    system = schema.exact_keys(doc['system'], ('name', 'scope', 'horizon'), 'system')
    for key in ('name', 'scope'):
        nonplaceholder(system[key], f'system.{key}', findings)
    nonplaceholder(system['horizon'], 'system.horizon', findings, 'CENTRE_WITHOUT_HORIZON')

    candidate = doc['candidate']
    if candidate is None:
        if 'no_dominant_reason' not in doc:
            schema.fail('no_dominant_reason', 'required when candidate is null')
        nonplaceholder(doc['no_dominant_reason'], 'no_dominant_reason', findings)
    else:
        schema.exact_keys(candidate, ('id', 'description', 'kind'), 'candidate')
        schema.text(candidate['id'], 'candidate.id')
        nonplaceholder(candidate['description'], 'candidate.description', findings)
        schema.enum(candidate['kind'], KINDS, 'candidate.kind')
        if 'no_dominant_reason' in doc:
            schema.fail('no_dominant_reason', 'only allowed when candidate is null')

    capabilities = schema.array(doc['capabilities'], 'capabilities', 1 if candidate else 0)
    cap_ids = set(schema.unique_ids(capabilities, 'capabilities'))
    for index, cap in enumerate(capabilities):
        schema.exact_keys(cap, ('id', 'verb', 'description'), f'capabilities[{index}]')
        nonplaceholder(cap['verb'], f'capabilities[{index}].verb', findings, 'CAPABILITY_WITHOUT_FUNCTION')
        nonplaceholder(cap['description'], f'capabilities[{index}].description', findings)
    requirements = schema.array(doc['requirements'], 'requirements', 1 if candidate else 0)
    req_ids = set(schema.unique_ids(requirements, 'requirements'))
    for index, req in enumerate(requirements):
        schema.exact_keys(req, ('id', 'capability', 'description'), f'requirements[{index}]')
        if req['capability'] not in cap_ids:
            findings.error('BROKEN_CHAIN', f'requirements[{index}].capability', 'requirement for an unknown capability')
        nonplaceholder(req['description'], f'requirements[{index}].description', findings)
    vulnerabilities = schema.array(doc['vulnerabilities'], 'vulnerabilities')
    schema.unique_ids(vulnerabilities, 'vulnerabilities')
    for index, vul in enumerate(vulnerabilities):
        path = f'vulnerabilities[{index}]'
        schema.exact_keys(vul, ('id', 'requirement', 'feasible_path', 'compensable_within_horizon'), path)
        if vul['requirement'] not in req_ids:
            findings.error('BROKEN_CHAIN', f'{path}.requirement', 'vulnerability of an unknown requirement')
        nonplaceholder(vul['feasible_path'], f'{path}.feasible_path', findings, 'VULNERABILITY_WITHOUT_PATH')
        if schema.boolean(vul['compensable_within_horizon'], f'{path}.compensable_within_horizon'):
            findings.error('NOT_A_CRITICAL_VULNERABILITY', path,
                           'the system compensates it within the horizon; by definition it is not critical')

    matrix = schema.exact_keys(doc['matrix'], MATRIX, 'matrix')
    for key in ('scope', 'dependency', 'transmission', 'conversion', 'revision'):
        nonplaceholder(matrix[key], f'matrix.{key}', findings, 'MATRIX_INCOMPLETE')
    substitution = schema.exact_keys(matrix['substitution'], ('alternatives', 'time'), 'matrix.substitution')
    schema.array(substitution['alternatives'], 'matrix.substitution.alternatives')
    nonplaceholder(substitution['time'], 'matrix.substitution.time', findings, 'CENTRE_WITHOUT_SUBSTITUTION')

    point = schema.exact_keys(doc['decisive_point'], ('statement', 'enables'), 'decisive_point')
    nonplaceholder(point['statement'], 'decisive_point.statement', findings)
    nonplaceholder(point['enables'], 'decisive_point.enables', findings)
    effort = schema.exact_keys(doc['schwerpunkt'], ('focus', 'renunciations', 'minimums'), 'schwerpunkt')
    nonplaceholder(effort['focus'], 'schwerpunkt.focus', findings)
    for index, item in enumerate(schema.array(effort['renunciations'], 'schwerpunkt.renunciations', 1)):
        nonplaceholder(item, f'schwerpunkt.renunciations[{index}]', findings, 'PRIORITY_WITHOUT_RENUNCIATION')
    for index, item in enumerate(schema.array(effort['minimums'], 'schwerpunkt.minimums', 1)):
        nonplaceholder(item, f'schwerpunkt.minimums[{index}]', findings)
    for index, item in enumerate(schema.array(doc['own_dependencies'], 'own_dependencies', 1)):
        nonplaceholder(item, f'own_dependencies[{index}]', findings)

    concepts = {'decisive_point.statement': point['statement'], 'schwerpunkt.focus': effort['focus']}
    if candidate is not None:
        concepts['candidate.description'] = candidate['description']
    for index, vul in enumerate(vulnerabilities):
        concepts[f'vulnerabilities[{index}].feasible_path'] = vul['feasible_path']
    seen = {}
    for path, text in concepts.items():
        norm = _norm(text)
        if norm and norm in seen:
            findings.error('CONCEPT_CONFUSION', path, f'same statement as {seen[norm]} (pathology 4)')
        elif norm:
            seen[norm] = path
    ctx.refs(doc['basis'], 'basis', 1 if candidate else 0)

    body = {key: doc[key] for key in COMMAND.fields + ('no_dominant_reason',) if key in doc}
    return Result(body=body, next_decision='Design options that differ in mechanism (ante options).')


COMMAND = Command(
    name='focus', summary='centre of gravity chain, matrix III.10, Schwerpunkt and renunciations',
    fields=('system', 'candidate', 'capabilities', 'requirements', 'vulnerabilities', 'matrix',
            'decisive_point', 'schwerpunkt', 'own_dependencies', 'basis'),
    optional=('no_dominant_reason',), parents=('map',), run=run)

"""ante street — misuse analysis of the plan's own instruments.

Marco VIII.12 (Goodhart, Campbell: an indicator under decision pressure
distorts the process it measures) and VI (paradoxical logic: an effective
measure invites the counter-measure). For every metric, rule or instrument the
plan introduces, ask how the actors will reuse it **against its purpose**, and
how the misuse would be seen.

Input fields::

    instruments  [{id, kind, statement, purpose,
                   misuse: [{actor, reuse, effect_on_purpose, indicator, countermeasure}]}]
                 kind: metric | rule | instrument

Refused:
- an instrument with no misuse scenario (``INSTRUMENT_WITHOUT_MISUSE``);
- a scenario whose manipulation indicator is the instrument itself
  (``CIRCULAR_INDICATOR``): a gamed metric cannot reveal its own gaming;
- an actor that is not in the ``map`` artefact when one is in the lineage.

``cohere`` reads the ``street`` artefact: a plan metric with no misuse analysis
keeps the interactive test from passing (it is marked ``CONDITIONAL`` with
pending evidence). In decision records this analysis is ``misuse_analysis``.
"""
from __future__ import annotations

from ante.core import schema
from ante.strategy.base import Command, Result, nonplaceholder

KINDS = ('metric', 'rule', 'instrument')
SCENARIO_KEYS = ('actor', 'reuse', 'effect_on_purpose', 'indicator', 'countermeasure')


def _norm(text: str) -> str:
    return ' '.join(str(text).lower().split())


def run(doc, ctx):
    findings = ctx.findings
    map_artefact = ctx.lineage.one('map')
    actors = {a['id'] for a in map_artefact['body']['actors']} if map_artefact else None
    items = schema.array(doc['instruments'], 'instruments', 1)
    schema.unique_ids(items, 'instruments')
    analysed = []
    for index, item in enumerate(items):
        path = f'instruments[{index}]'
        schema.exact_keys(item, ('id', 'kind', 'statement', 'purpose', 'misuse'), path)
        schema.enum(item['kind'], KINDS, f'{path}.kind')
        statement = nonplaceholder(item['statement'], f'{path}.statement', findings)
        nonplaceholder(item['purpose'], f'{path}.purpose', findings)
        scenarios = schema.array(item['misuse'], f'{path}.misuse')
        if not scenarios:
            findings.error('INSTRUMENT_WITHOUT_MISUSE', f'{path}.misuse',
                           'how will the actors reuse this against its purpose?')
        for number, scenario in enumerate(scenarios):
            spath = f'{path}.misuse[{number}]'
            schema.exact_keys(scenario, SCENARIO_KEYS, spath)
            for key in SCENARIO_KEYS:
                nonplaceholder(scenario[key], f'{spath}.{key}', findings)
            if actors is not None and scenario['actor'] not in actors:
                findings.error('UNKNOWN_ACTOR', f'{spath}.actor', 'not an actor of the map artefact')
            if statement and _norm(scenario['indicator']) == _norm(statement):
                findings.error('CIRCULAR_INDICATOR', f'{spath}.indicator',
                               'the instrument cannot reveal its own gaming; observe something it does not control')
        analysed.append(item)
    body = {'misuse_analysis': analysed,
            'covered_metrics': sorted(_norm(i['statement']) for i in analysed if i['kind'] == 'metric')}
    return Result(body=body, next_decision='Carry each manipulation indicator into watch; cohere checks coverage.')


def covers(street_artefact: dict | None, metric: str) -> bool:
    return street_artefact is not None and _norm(metric) in street_artefact['body']['covered_metrics']


COMMAND = Command(name='street', summary='misuse analysis of the plan\'s metrics, rules and instruments',
                  fields=('instruments',), parents=('frame',), run=run)

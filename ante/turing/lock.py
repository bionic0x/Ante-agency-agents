"""The Turing lock.

A self-developing system can gain autonomy without any single change looking
like it: a slightly larger budget here, one fewer review there, a broader scope
next week. The lock therefore counts **autonomy**, not changes, and counts it
**cumulatively**.

Every proposal declares an ``autonomy_delta`` on six dimensions (permissions,
budget, scope, gate_thresholds, frequency, human_review_reduction); a positive
integer is one step more autonomy. The lock:

1. refuses to net dimensions against each other: only positive components count,
   so reducing one dimension does not pay for increasing another;
2. sends any single proposal with a component above ``PER_PROPOSAL_LIMIT`` to
   review;
3. adds the positive components of every proposal the gate let through since the
   last independent review; when this proposal would take the running total above
   ``CUMULATIVE_LIMIT`` it goes to review (with the defaults, the fifth of five
   proposals of one step each);
4. flags a proposal that declares no autonomy change while its patch adds lines
   that look like one (``UNDECLARED_AUTONOMY``) — a heuristic tripwire, not proof.

"Review" means a record by an ``INDEPENDENT_OPERATOR`` (invariant 10) naming the
proposal and the cumulative total it accepts. A review written by the loop itself
is refused. The record is self-declared, like every independence label in Ante:
the lock checks its form and coverage, not the reviewer's identity. Without a
valid review the gate answers HOLD; nothing here can answer PROPOSE on its own
authority.
"""
from __future__ import annotations

import re

from ante.core import canon, io, schema
from ante.core import time as ante_time

DIMENSIONS = ('permissions', 'budget', 'scope', 'gate_thresholds', 'frequency', 'human_review_reduction')
PER_PROPOSAL_LIMIT = 1
CUMULATIVE_LIMIT = 4
LOOP_NAMES = ('ante develop', 'ante-develop', 'nexus-optimize', 'improver')
REVIEW_KEYS = ('reviewer', 'independence_level', 'proposal', 'accepts_cumulative', 'at', 'statement',
               'record_sha256')
TRIPWIRE = re.compile(r'^\+(?!\+\+).*\b(budget|max_[a-z_]+|autonomy|approval|approver|permission|'
                      r'allowed_tools|tools\s*:|threshold|auto_?merge|review_required|spend)\b', re.I | re.M)


class LockError(ValueError):
    pass


def positive(delta: dict) -> int:
    return sum(max(0, int(delta[name])) for name in DIMENSIONS)


def _review(path: str, proposal_id: str, total: int, at: str) -> dict:
    record = io.load_document(path)
    schema.exact_keys(record, REVIEW_KEYS, 'review')
    for key in ('reviewer', 'statement'):
        schema.text(record[key], f'review.{key}')
    if record['independence_level'] != 'INDEPENDENT_OPERATOR':
        raise LockError('the review is not by an INDEPENDENT_OPERATOR')
    if record['reviewer'].strip().lower() in LOOP_NAMES:
        raise LockError('the develop loop cannot review its own autonomy')
    if record['proposal'] != proposal_id:
        raise LockError(f'the review covers {record["proposal"]}, not {proposal_id}')
    if schema.integer(record['accepts_cumulative'], 'review.accepts_cumulative') < total:
        raise LockError(f'the review accepts a cumulative autonomy of {record["accepts_cumulative"]}, '
                        f'this proposal brings it to {total}')
    if ante_time.parse(record['at'], 'review.at') > ante_time.parse(at, 'at'):
        raise LockError('the review is dated after the gate')
    body = {k: v for k, v in record.items() if k != 'record_sha256'}
    if canon.digest(body) != record['record_sha256']:
        raise LockError('the review record does not match its record_sha256')
    return record


def cumulative(entries: list[dict]) -> int:
    """Positive autonomy let through by the gate since the last accepted review."""
    proposals = {e['payload']['id']: e['payload']['spec'] for e in entries if e['kind'] == 'proposal'}
    total = 0
    for entry in entries:
        if entry['kind'] != 'gate':
            continue
        payload = entry['payload']
        autonomy = payload['checks'].get('autonomy', {})
        if autonomy.get('review'):
            total = 0
        elif payload['decision'] == 'PROPOSE':
            total += positive(proposals[payload['id']]['autonomy_delta'])
    return total


def assess(entries: list[dict], proposal: dict, review_path: str | None, at: str, patch_text: str = '') -> dict:
    delta = proposal['spec']['autonomy_delta']
    own = positive(delta)
    prior = cumulative([e for e in entries if not (e['kind'] == 'gate' and e['payload']['id'] == proposal['id'])])
    total = prior + own
    reasons = []
    if any(int(delta[name]) > PER_PROPOSAL_LIMIT for name in DIMENSIONS):
        reasons.append(f'a single dimension rises by more than {PER_PROPOSAL_LIMIT}')
    if own and total > CUMULATIVE_LIMIT:
        reasons.append(f'cumulative autonomy {total} exceeds {CUMULATIVE_LIMIT} since the last independent review')
    tripped = sorted({m.group(1).lower() for m in TRIPWIRE.finditer(patch_text)})
    if not own and tripped:
        reasons.append('UNDECLARED_AUTONOMY: the patch adds lines mentioning ' + ', '.join(tripped)
                       + ' but declares no autonomy change')
    result = {'delta': delta, 'positive': own, 'cumulative_before': prior, 'cumulative_after': total,
              'limits': {'per_proposal': PER_PROPOSAL_LIMIT, 'cumulative': CUMULATIVE_LIMIT}, 'review': None}
    if not reasons:
        return {**result, 'decision': 'PASS', 'reason': 'no autonomy beyond the limits'}
    if review_path is None:
        return {**result, 'decision': 'HOLD', 'reason': '; '.join(reasons) + '; needs an INDEPENDENT_OPERATOR review'}
    try:
        record = _review(review_path, proposal['id'], total, at)
    except (LockError, io.InputError, schema.SchemaError, ante_time.TimeError) as exc:
        return {**result, 'decision': 'REJECT', 'reason': f'review refused: {exc}'}
    return {**result, 'decision': 'PASS', 'reason': '; '.join(reasons) + '; accepted by independent review',
            'review': {'reviewer': record['reviewer'], 'record_sha256': record['record_sha256']}}

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
2. holds every proposal with a positive delta until a review record by an
   ``INDEPENDENT_OPERATOR`` (invariant 10) names it;
3. adds the positive components of every proposal the gate let through in the
   last ``WINDOW_DAYS`` since the last review of the accumulation; when this
   proposal takes the running total above ``CUMULATIVE_LIMIT``, a review of this
   step alone is not enough — the record must accept the accumulated total. With
   the defaults, five one-step proposals, each reviewed on its own, pass four
   times and are held on the fifth: the erosion is in the sum, which no
   single-step reviewer saw;
4. holds a proposal that declares no autonomy change while its patch adds lines
   that look like one (``UNDECLARED_AUTONOMY``) — a heuristic tripwire, not proof.

A review written by the loop itself, by a lower independence level, for another
proposal, dated after the gate or not matching its own hash is refused (REJECT).
The record is self-declared, like every independence label in Ante: the lock
checks its form and coverage, not the reviewer's identity. Nothing here can
answer PROPOSE on its own authority; it can only hold or refuse.
"""
from __future__ import annotations

import re

from ante.core import canon, io, schema
from ante.core import time as ante_time

DIMENSIONS = ('permissions', 'budget', 'scope', 'gate_thresholds', 'frequency', 'human_review_reduction')
CUMULATIVE_LIMIT = 4
WINDOW_DAYS = 90
LOOP_NAMES = ('ante develop', 'ante-develop', 'nexus-optimize', 'improver')
REVIEW_KEYS = ('reviewer', 'independence_level', 'proposal', 'accepts_cumulative', 'at', 'statement',
               'record_sha256')
TRIPWIRE = re.compile(r'^\+(?!\+\+).*\b(budget|max_[a-z_]+|autonomy|approval|approver|permission|'
                      r'allowed_tools|tools\s*:|threshold|auto_?merge|review_required|spend)\b', re.I | re.M)


class LockError(ValueError):
    pass


def positive(delta: dict) -> int:
    return sum(max(0, int(delta[name])) for name in DIMENSIONS)


def _review(path: str, proposal_id: str, at: str) -> dict:
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
    schema.integer(record['accepts_cumulative'], 'review.accepts_cumulative', 0)
    if ante_time.parse(record['at'], 'review.at') > ante_time.parse(at, 'at'):
        raise LockError('the review is dated after the gate')
    body = {k: v for k, v in record.items() if k != 'record_sha256'}
    if canon.digest(body) != record['record_sha256']:
        raise LockError('the review record does not match its record_sha256')
    return record


def cumulative(entries: list[dict], at: str) -> int:
    """Positive autonomy the gate let through in the window, since the last review of the accumulation."""
    now = ante_time.parse(at, 'at')
    proposals = {e['payload']['id']: e['payload']['spec'] for e in entries if e['kind'] == 'proposal'}
    total = 0
    for entry in entries:
        if entry['kind'] != 'gate':
            continue
        payload = entry['payload']
        autonomy = payload['checks'].get('autonomy', {})
        if autonomy.get('accumulation_reviewed'):
            total = 0
            continue
        recent = (now - ante_time.parse(entry['at'], 'at')).days < WINDOW_DAYS
        if payload['decision'] == 'PROPOSE' and recent:
            total += positive(proposals[payload['id']]['autonomy_delta'])
    return total


def assess(entries: list[dict], proposal: dict, review_path: str | None, at: str, patch_text: str = '') -> dict:
    delta = proposal['spec']['autonomy_delta']
    own = positive(delta)
    prior = cumulative([e for e in entries if not (e['kind'] == 'gate' and e['payload']['id'] == proposal['id'])], at)
    total = prior + own
    result = {'delta': delta, 'positive': own, 'cumulative_before': prior, 'cumulative_after': total,
              'limits': {'cumulative': CUMULATIVE_LIMIT, 'window_days': WINDOW_DAYS},
              'review': None, 'accumulation_reviewed': False}
    tripped = sorted({m.group(1).lower() for m in TRIPWIRE.finditer(patch_text)})
    if not own:
        if tripped:
            return {**result, 'decision': 'HOLD',
                    'reason': 'UNDECLARED_AUTONOMY: the patch adds lines mentioning ' + ', '.join(tripped)
                              + ' but declares no autonomy change; declare it or show it is not one'}
        return {**result, 'decision': 'PASS', 'reason': 'no autonomy change declared or detected'}
    if review_path is None:
        return {**result, 'decision': 'HOLD',
                'reason': f'positive autonomy delta ({own}) needs an INDEPENDENT_OPERATOR review'}
    try:
        record = _review(review_path, proposal['id'], at)
    except (LockError, io.InputError, schema.SchemaError, ante_time.TimeError) as exc:
        return {**result, 'decision': 'REJECT', 'reason': f'review refused: {exc}'}
    review = {'reviewer': record['reviewer'], 'record_sha256': record['record_sha256'],
              'accepts_cumulative': record['accepts_cumulative']}
    if total > CUMULATIVE_LIMIT:
        if record['accepts_cumulative'] < total:
            return {**result, 'review': review, 'decision': 'HOLD',
                    'reason': f'cumulative autonomy {total} in {WINDOW_DAYS} days exceeds {CUMULATIVE_LIMIT}; '
                              f'the review accepts {record["accepts_cumulative"]}: the accumulated steps need '
                              'their own review'}
        return {**result, 'review': review, 'accumulation_reviewed': True, 'decision': 'PASS',
                'reason': f'cumulative autonomy {total} accepted by an independent review of the accumulation'}
    return {**result, 'review': review, 'decision': 'PASS', 'reason': 'step accepted by independent review'}

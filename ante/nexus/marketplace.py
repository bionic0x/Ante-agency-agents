"""Turn normalized external marketplace observations into offline HOLD packets.

No API client, signer, model invocation or NEXUS replay event is emitted here.
The format is Ante's review envelope, not an assertion about ACT's API schema.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys

MAX_BYTES = 1024 * 1024
PAYMENT_STATES = {'NOT_OBSERVED', 'PENDING_REPORTED', 'SETTLED_REPORTED', 'DISPUTED_REPORTED'}
STATES = {
    'PENDING': 'unassigned', 'INVITED': 'invitation_reported',
    'ASSIGNED': 'assignment_reported', 'SUBMITTED': 'delivery_reported',
    'COMPLETED': 'client_acceptance_reported', 'VALIDATED': 'validator_acceptance_reported',
    'DELETED': 'deletion_reported', 'DECLINED_BY_OWNER': 'rejection_reported',
    'DECLINED_BY_VALIDATOR': 'rejection_reported',
    'DISPUTED_BY_OWNER': 'dispute_reported', 'DISPUTED_BY_AGENT': 'dispute_reported',
    'RESOLVED': 'resolution_reported',
}
FIELDS = {'chain', 'contract', 'task_id', 'event', 'observed_at', 'source_ref',
          'external_state', 'topic', 'payload', 'deadline', 'payment_state'}
EVENT_FIELDS = {'transaction_hash', 'log_index', 'block_number', 'block_hash',
                'removed', 'confirmations'}


def exact_keys(value, keys, field):
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f'{field}: expected exactly the documented fields')


def integer(value, field, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{field}: invalid integer')
    return value


def text(value, field, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'{field}: invalid text length')
    return value


def timestamp(value, field):
    text(value, field, 64)
    try:
        date = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError(f'{field}: invalid ISO timestamp') from exc
    if date.tzinfo is None:
        raise ValueError(f'{field}: timezone required')
    return date.astimezone(dt.timezone.utc)


def hex_value(value, digits, field):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]{' + str(digits) + '}', value):
        raise ValueError(f'{field}: invalid hexadecimal value')
    if int(value[2:], 16) == 0:
        raise ValueError(f'{field}: zero value is not an identity')
    return value.lower()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def normalize(row):
    exact_keys(row, FIELDS, 'observation')
    row = dict(row)
    if not isinstance(row['chain'], str) or not re.fullmatch(r'eip155:[1-9][0-9]{0,19}', row['chain']):
        raise ValueError('chain: expected canonical eip155 chain identity')
    row['contract'] = hex_value(row['contract'], 40, 'contract')
    task_id = row['task_id']
    if not isinstance(task_id, str) or not re.fullmatch(r'0|[1-9][0-9]{0,28}', task_id) or int(task_id) >= 2**96:
        raise ValueError('task_id: expected canonical uint96 decimal string')
    event = row['event']
    exact_keys(event, EVENT_FIELDS, 'event')
    event = dict(event)
    for field in ('transaction_hash', 'block_hash'):
        event[field] = hex_value(event[field], 64, field)
    for field in ('log_index', 'block_number', 'confirmations'):
        integer(event[field], field)
    if type(event['removed']) is not bool:
        raise ValueError('removed: expected boolean')
    row['event'] = event
    for field in ('observed_at', 'deadline'):
        row[field] = timestamp(row[field], field).isoformat()
    text(row['source_ref'], 'source_ref', 1024)
    text(row['topic'], 'topic', 128)
    text(row['payload'], 'payload', 65536)
    if not isinstance(row['external_state'], str) or row['external_state'] not in STATES:
        raise ValueError('external_state: unknown ACT state')
    if not isinstance(row['payment_state'], str) or row['payment_state'] not in PAYMENT_STATES:
        raise ValueError('payment_state: unknown observation state')
    return row


def review(document, *, at, max_age_seconds=86400, min_confirmations=12):
    """Deterministic batch review. Deduplication is local to this batch only."""
    exact_keys(document, {'schema_version', 'observations'}, 'document')
    if type(document['schema_version']) is not int or document['schema_version'] != 1:
        raise ValueError('schema_version: expected 1')
    integer(max_age_seconds, 'max_age_seconds', 1)
    integer(min_confirmations, 'min_confirmations', 1)
    if not isinstance(at, dt.datetime) or at.tzinfo is None:
        raise ValueError('at: explicit timezone required')
    rows = document['observations']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
        raise ValueError('observations: expected 1 to 1000 records')
    seen, packets, duplicate_count = {}, [], 0
    for original in rows:
        row = normalize(original)
        event = row['event']
        task_key = f"{row['chain']}:{row['contract']}:{row['task_id']}"
        event_key = f"{row['chain']}:{row['contract']}:{event['transaction_hash']}:{event['log_index']}"
        fingerprint = digest(canonical(row))
        if event_key in seen:
            if seen[event_key] != fingerprint:
                # Includes conflicting block hashes, states, payloads or timestamps.
                # Never choose one of two incompatible records silently.
                raise ValueError('conflicting observation for one event; reconcile source history')
            duplicate_count += 1
            continue
        seen[event_key] = fingerprint
        observed = timestamp(row['observed_at'], 'observed_at')
        reasons = ['OWNER_MANDATE_REQUIRED', 'INDEPENDENT_SOURCE_VERIFICATION_REQUIRED']
        if observed > at:
            reasons.append('FUTURE_OBSERVATION')
        elif (at - observed).total_seconds() >= max_age_seconds:
            reasons.append('STALE_OBSERVATION')
        if timestamp(row['deadline'], 'deadline') <= at:
            reasons.append('DEADLINE_REACHED')
        if event['removed']:
            reasons.append('REMOVED_LOG_RECONCILIATION_REQUIRED')
        if event['confirmations'] < min_confirmations:
            reasons.append('CONFIRMATION_POLICY_NOT_MET')
        if row['external_state'] != 'ASSIGNED':
            reasons.append('NOT_AN_ASSIGNED_TASK')
        packets.append({
            'task_key': task_key, 'event_key': event_key,
            'observation_sha256': fingerprint,
            'payload_sha256': digest(row['payload']),
            'external_state': row['external_state'],
            'external_meaning': STATES[row['external_state']],
            'decision_state': 'HOLD', 'claim_status': 'ASSUMPTION',
            'execution_authorized': False, 'hold_reasons': reasons,
            'payment_state': row['payment_state'], 'payment_authorized': False,
            'review_runbook': 'strategic-decision',
        })
    return {
        'schema_version': 1, 'mode': 'offline-review-only',
        'at': at.astimezone(dt.timezone.utc).isoformat(),
        'policy': {'max_age_seconds': max_age_seconds, 'min_confirmations': min_confirmations},
        'input_sha256': digest(canonical(document)),
        'duplicate_count': duplicate_count,
        'packets': sorted(packets, key=lambda packet: packet['event_key']),
    }


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON object key')
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--at', required=True, help='explicit ISO timestamp with timezone')
    parser.add_argument('--max-age-seconds', type=int, default=86400)
    parser.add_argument('--min-confirmations', type=int, default=12)
    args = parser.parse_args(argv)
    try:
        with args.snapshot.open('rb') as handle:
            raw = handle.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('snapshot exceeds 1 MiB')
        document = json.loads(raw, object_pairs_hook=unique_object)
        result = review(document, at=timestamp(args.at, 'at'),
                        max_age_seconds=args.max_age_seconds,
                        min_confirmations=args.min_confirmations)
    except (OSError, ValueError, RecursionError):
        # Raw parser/OS exceptions can include attacker-controlled payloads/paths.
        print('marketplace intake rejected: invalid, unreadable or conflicting snapshot; see contract', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())

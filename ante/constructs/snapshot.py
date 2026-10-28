"""Decision snapshot: what was known when ``decide`` ran, frozen inside the record."""
from __future__ import annotations

from ante.core import canon

KEYS = ('frozen_at', 'parents', 'claims_known', 'expectations', 'verdict', 'snapshot_sha256')


class SnapshotError(ValueError):
    pass


def build(at: str, parents: list[dict], own_claims: list[dict], expectations: list[dict], verdict: str) -> dict:
    known = [{'id': c['id'], 'status': c['status'], 'origin': (c.get('source') or {}).get('origin'),
              'from': 'decide'} for c in own_claims]
    for parent in sorted(parents, key=lambda p: (p['command'], p['artifact_sha256'])):
        known += [{'id': c['id'], 'status': c['status'], 'origin': (c.get('source') or {}).get('origin'),
                   'from': parent['command']} for c in parent['claims']]
    body = {'frozen_at': at,
            'parents': [{'command': p['command'], 'artifact_sha256': p['artifact_sha256']}
                        for p in sorted(parents, key=lambda p: (p['command'], p['artifact_sha256']))],
            'claims_known': known, 'expectations': expectations, 'verdict': verdict}
    return {**body, 'snapshot_sha256': canon.digest(body)}


def verify(snapshot: dict) -> dict:
    if not isinstance(snapshot, dict) or set(snapshot) != set(KEYS):
        raise SnapshotError('the decision carries no frozen snapshot')
    body = {k: v for k, v in snapshot.items() if k != 'snapshot_sha256'}
    if canon.digest(body) != snapshot['snapshot_sha256']:
        raise SnapshotError('the decision snapshot does not match its hash')
    return snapshot

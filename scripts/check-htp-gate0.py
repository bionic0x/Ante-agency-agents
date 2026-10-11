#!/usr/bin/env python3
"""Structural guard for HTP Gate 0 machine-readable artifacts.

Checks recording boundaries only, not on-chain facts or authority authenticity.
A textual authority reference does not grant permission or close Gate 0.
"""
from __future__ import annotations

import json
from pathlib import Path
import runpy
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
NETWORKS = {'solana', 'arbitrum_one'}
LIVE_ACTIONS = {'production_write', 'transaction_signing', 'transaction_submission', 'custody', 'liquidation'}


def load(path: Path):
    with path.open() as handle:
        return yaml.safe_load(handle)


def check(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    gate0 = root / 'strategy/htp-gate0'
    register = load(gate0 / 'gate0/05-claim-registers.yaml')
    ladder = set(register['schema']['allowed_evidence_status'])
    if register.get('cross_network_transfer_policy', {}).get('default') != 'forbidden':
        errors.append('05-claim-registers: cross-network transfer default must remain forbidden')
    runbooks = json.loads((root / 'strategy/runbooks.json').read_text())['runbooks']
    book = next((b for b in runbooks if b['slug'] == 'htp-gate0-solana-arbitrum'), None)
    roster = {a for group in book['roster'] for a in group['agents']} if book else set()
    if not book:
        errors.append('runbooks.json: htp-gate0-solana-arbitrum runbook missing')
    collect = runpy.run_path(str(root / 'scripts/build-catalog.py'))['collect']
    collect.__globals__['ROOT'] = root
    catalog = {a['slug'] for a in collect()[1]}

    handoff_count = 0
    for instance in sorted(p for p in (gate0 / 'instances').iterdir() if p.is_dir()):
        manifests: dict[str, dict] = {}
        for path in sorted(instance.glob('*.yaml')):
            rel = path.relative_to(root)
            try:
                doc = load(path)
            except yaml.YAMLError as exc:
                errors.append(f'{rel}: invalid YAML ({exc})')
                continue
            if isinstance(doc, dict) and 'manifest' in doc:
                manifest = doc['manifest']
                if not isinstance(manifest, dict):
                    errors.append(f'{rel}: manifest mapping required')
                    continue
                scope = manifest.get('network_scope')
                if not isinstance(scope, str) or scope not in NETWORKS:
                    errors.append(f'{rel}: manifest network_scope must be one of {sorted(NETWORKS)}')
                manifests[str(rel)] = manifest
        for path in sorted(instance.glob('handoff-*.yaml')):
            handoff_count += 1
            rel = path.relative_to(root)
            try:
                handoff = load(path)['handoff']
            except (yaml.YAMLError, KeyError, TypeError):
                errors.append(f'{rel}: missing handoff mapping')
                continue
            if not isinstance(handoff, dict):
                errors.append(f'{rel}: missing handoff mapping')
                continue
            scope = handoff.get('network_scope')
            if not isinstance(scope, str) or scope not in NETWORKS:
                errors.append(f'{rel}: handoff must name exactly one network ({sorted(NETWORKS)})')
            ref = str(handoff.get('artifact_ref', '')).strip()
            manifest = manifests.get(ref)
            if manifest is None:
                errors.append(f'{rel}: artifact_ref does not resolve to a manifest in this instance')
            else:
                if manifest.get('network_scope') != scope:
                    errors.append(f'{rel}: cross-network handoff ({scope} -> manifest {manifest.get("network_scope")})')
                freeze, frozen = handoff.get('artifact_freeze_date'), manifest.get('frozen_at')
                if not freeze or not frozen or str(freeze) != str(frozen):
                    errors.append(f'{rel}: artifact_freeze_date missing or differs from manifest frozen_at')
            status = handoff.get('evidence_status')
            if not isinstance(status, str) or status not in ladder:
                errors.append(f'{rel}: evidence_status not in Gate 0 evidence ladder')
            for field in ('from_agent', 'to_agent'):
                agent = handoff.get(field)
                if not isinstance(agent, str) or agent not in catalog or agent not in roster:
                    errors.append(f'{rel}: {field} {agent!r} is not a catalog agent in the HTP roster')
            tool_sets = {}
            for field in ('allowed_tools', 'prohibited_actions'):
                values = handoff.get(field)
                if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
                    errors.append(f'{rel}: {field} must be a string array')
                    values = []
                tool_sets[field] = set(values)
            allowed, prohibited = tool_sets['allowed_tools'], tool_sets['prohibited_actions']
            if allowed & prohibited:
                errors.append(f'{rel}: tools both allowed and prohibited: {sorted(allowed & prohibited)}')
            authority = handoff.get('authority_ref')
            if not isinstance(authority, str) or not authority.strip():
                if not LIVE_ACTIONS <= prohibited:
                    errors.append(f'{rel}: without authority_ref, prohibited_actions must include {sorted(LIVE_ACTIONS - prohibited)}')
            for field in ('governing_object', 'non_object'):
                value = handoff.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f'{rel}: {field} required')
    if not handoff_count:
        errors.append('Gate 0: at least one instance handoff required')
    return errors


def main() -> int:
    try:
        errors = check()
    except (OSError, ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError) as exc:
        errors = [f'invalid Gate 0 structure: {exc}']
    if errors:
        print('\n'.join('ERROR ' + e for e in errors))
        return 1
    print('PASSED: HTP Gate 0 handoffs stay single-network, bounded and roster-bound')
    return 0


if __name__ == '__main__':
    sys.exit(main())

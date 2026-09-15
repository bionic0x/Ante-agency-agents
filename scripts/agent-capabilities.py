#!/usr/bin/env python3
"""Inspect declared/observed capability boundaries; render a scoped Claude profile.

This tool does not observe a live host or grant authority. Observations and scope
policies are explicit, externally supplied records, never inferred from prompts.
"""
from __future__ import annotations
import argparse
import hashlib
import datetime as dt
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('privileges', ROOT / 'scripts/check-agent-privileges.py')
privileges = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privileges)


def load(path):
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict):
        raise ValueError('record must be an object')
    return value


def nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be non-empty text')
    return value


def tokens(value, name):
    if not isinstance(value, list) or not all(isinstance(t, str) and t.strip() for t in value):
        raise ValueError(f'{name} must be an array of tool names')
    if len(value) != len(set(value)):
        raise ValueError(f'{name} contains duplicate tools')
    return value


def timestamp(value, name):
    try:
        date = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        raise ValueError(f'{name} must be an ISO timestamp')
    if date.tzinfo is None:
        raise ValueError(f'{name} must include timezone')
    return date


def resolve_agent(agent_id):
    matches = [p for p in privileges.agent_files(ROOT) if p.stem == agent_id]
    if len(matches) != 1:
        raise ValueError('agent must resolve to one canonical filename ID')
    return matches[0]


def policy_tools(policy, agent_id, at):
    if policy.get('host') != 'claude-code' or policy.get('agent_id') != agent_id:
        raise ValueError('policy host/agent does not match this profile')
    for field in ('scope', 'owner', 'authority_ref'):
        nonempty(policy.get(field), field)
    if timestamp(policy.get('expires'), 'expires') <= at:
        raise ValueError('scope policy expired')
    result = tokens(policy.get('allowed_tools'), 'allowed_tools')
    _, registry = privileges.load_tool_policy(ROOT)
    privileges.validate_registered_tools(result, registry)
    return result


def inspect(agent_id, observation=None, policy=None, at=None):
    at = at or dt.datetime.now(dt.timezone.utc)
    path = resolve_agent(agent_id)
    metadata = privileges.frontmatter(path)
    declared = privileges.parse_tools(metadata['tools']) if 'tools' in metadata else None
    classes, registry = privileges.load_tool_policy(ROOT)
    if declared is not None:
        privileges.validate_registered_tools(declared, registry)
    report = {
        'agent_id': agent_id, 'host': 'claude-code',
        'declared_capabilities': declared,
        'declaration_state': 'EXPLICIT' if declared is not None else 'HOST_INHERITED',
        'declared_class': privileges.declared_class(declared, classes, registry) if declared is not None else 'unspecified',
        'host_resolved_capabilities': None, 'scope_allowed_capabilities': None,
        'candidate_authorized_capabilities': None, 'verified_authority': False,
        'status': 'HOST_NOT_OBSERVED',
        'limitations': ['This diagnostic neither authenticates an authority record nor tests host enforcement.'],
    }
    allowed = policy_tools(policy, agent_id, at) if policy is not None else None
    report['scope_allowed_capabilities'] = allowed
    if observation is not None:
        if observation.get('host') != 'claude-code' or observation.get('agent_id') != agent_id:
            raise ValueError('observation host/agent does not match')
        for field in ('host_version', 'evidence_ref', 'configuration_ref'):
            nonempty(observation.get(field), field)
        if observation.get('source_sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('observation refers to another source revision')
        observed_at = timestamp(observation.get('observed_at'), 'observed_at')
        if observed_at > at or timestamp(observation.get('valid_until'), 'valid_until') <= at:
            raise ValueError('observation is future-dated or expired')
        observed = tokens(observation.get('resolved_tools'), 'resolved_tools')
        report['host_resolved_capabilities'] = observed
        report['observation_ref'] = observation['evidence_ref']
        report['status'] = 'SUPPLIED_OBSERVATION'
        outside = sorted(set(observed) - set(declared)) if declared is not None else []
        report['outside_declaration'] = outside
        if outside:
            report['status'] = 'DECLARATION_MISMATCH'
        if allowed is not None:
            report['outside_scope_policy'] = sorted(set(observed) - set(allowed))
            candidates = set(observed) & set(allowed)
            if declared is not None:
                candidates &= set(declared)
            report['candidate_authorized_capabilities'] = sorted(candidates)
    return report


def render(agent_id, policy, output, at=None):
    """Prepare only a Claude profile; user/host policy still governs its use."""
    at = at or dt.datetime.now(dt.timezone.utc)
    allowed = policy_tools(policy, agent_id, at)
    if not allowed:
        raise ValueError('empty allowlist is not portable; use host-enforced tool denial instead')
    path = resolve_agent(agent_id)
    metadata = privileges.frontmatter(path)
    if 'tools' in metadata:
        existing = privileges.parse_tools(metadata['tools'])
        if set(allowed) - set(existing):
            raise ValueError('scope policy cannot expand an explicit source declaration')
    text = path.read_text()
    end = text.index('\n---\n', 4)
    header = re.sub(r'^tools:.*\n?', '', text[4:end], flags=re.M).rstrip()
    result = '---\n' + header + '\ntools: ' + ', '.join(allowed) + '\n---\n' + text[end + 5:]
    dest = Path(output)
    if dest.exists():
        raise ValueError('output already exists; review before replacing a scoped profile')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(result)
    return {'path': str(dest.resolve()), 'status': 'PROFILE_PREPARED', 'authority_granted': False,
            'enforcement': 'HOST_SMOKE_TEST_REQUIRED', 'allowed_tools': allowed,
            'policy_expires': policy['expires'], 'policy_ref': policy['authority_ref'],
            'limitation': 'The generated profile does not enforce expiry; the host/operator must remove or revoke it.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['inspect', 'render'])
    ap.add_argument('--agent', required=True)
    ap.add_argument('--observation')
    ap.add_argument('--policy')
    ap.add_argument('--output')
    args = ap.parse_args()
    try:
        policy = load(args.policy) if args.policy else None
        if args.command == 'render':
            if policy is None or not args.output:
                ap.error('render requires --policy and --output')
            result = render(args.agent, policy, args.output)
        else:
            result = inspect(args.agent, load(args.observation) if args.observation else None, policy)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())

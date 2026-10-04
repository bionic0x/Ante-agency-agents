#!/usr/bin/env python3
"""Anthropic/Claude Code execution adapter for NEXUS.

This module is deliberately narrow. It does not decide whether a NEXUS task is
ready, which provider/model is admissible, or whether the operator has authority.
Those decisions belong to nexus-instance.py, nexus-routing.py and the caller.

The adapter does two things only:
  1. observe a real Claude Code model call and emit a model-observation record;
  2. execute one already-authorized task packet against one already-selected model.

No checked-in model catalog is implied. Observations expire. An execution record
proves only that a host call completed and reports the host/session counters it
could observe; it does not establish the correctness of the model output.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CAPABILITIES = _module('agent_capabilities_for_nexus', ROOT / 'scripts' / 'agent-capabilities.py')


class AdapterError(ValueError):
    pass


def _utcnow():
    return dt.datetime.now(dt.timezone.utc)


def _iso(value):
    return value.isoformat()


def _run(cmd, cwd, timeout=600):
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, 'CLAUDE_CODE_NONINTERACTIVE': '1'},
    )


def _events(text):
    rows = []
    for line in text.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _single(rows, predicate, label):
    found = [row for row in rows if predicate(row)]
    if len(found) != 1:
        raise AdapterError(f'expected exactly one {label}, got {len(found)}')
    return found[0]


def _observed_model(rows):
    values = []
    for row in rows:
        for value in (row.get('model'), row.get('model_id')):
            if isinstance(value, str) and value.strip():
                values.append(value.strip())
        message = row.get('message')
        if isinstance(message, dict):
            for value in (message.get('model'), message.get('model_id')):
                if isinstance(value, str) and value.strip():
                    values.append(value.strip())
    unique = sorted(set(values))
    if len(unique) > 1:
        raise AdapterError(f'host stream names multiple model ids: {unique}')
    return unique[0] if unique else None


def _context_window(rows):
    keys = ('context_window', 'model_context_window', 'context_window_tokens')
    values = []
    for row in rows:
        for key in keys:
            value = row.get(key)
            if type(value) is int and value > 0:
                values.append(value)
        message = row.get('message')
        if isinstance(message, dict):
            for key in keys:
                value = message.get(key)
                if type(value) is int and value > 0:
                    values.append(value)
    unique = sorted(set(values))
    if len(unique) > 1:
        raise AdapterError(f'host stream reports conflicting context windows: {unique}')
    return unique[0] if unique else None


def _usage_total(result):
    direct = result.get('tokens_total')
    if type(direct) in (int, float) and direct >= 0:
        return int(direct)
    usage = result.get('usage')
    if not isinstance(usage, dict):
        return None
    values = [v for k, v in usage.items()
              if k.endswith('_tokens') and type(v) in (int, float) and v >= 0]
    return int(sum(values)) if values else None


def _cost(result):
    for key in ('total_cost_usd', 'cost_usd'):
        value = result.get(key)
        if type(value) in (int, float) and value >= 0:
            return float(value)
    return None


def _host_duration(result):
    for key in ('duration_ms', 'duration_api_ms'):
        value = result.get(key)
        if type(value) in (int, float) and value >= 0:
            return float(value) / 1000.0
    return None


def _text_output(rows, result):
    chunks = []
    for row in rows:
        if row.get('type') != 'assistant':
            continue
        message = row.get('message')
        content = message.get('content') if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        text = ''.join(item.get('text', '') for item in content
                       if isinstance(item, dict) and item.get('type') == 'text')
        if text.strip():
            chunks.append(text)
    if chunks:
        return chunks[-1]
    value = result.get('result')
    return value if isinstance(value, str) else ''


def parse_stream(stdout, returncode=0, measured_wall_time=None):
    rows = _events(stdout)
    init = _single(rows, lambda e: e.get('type') == 'system' and e.get('subtype') == 'init', 'system/init event')
    result = _single(rows, lambda e: e.get('type') == 'result', 'result event')
    sid = init.get('session_id')
    if not isinstance(sid, str) or not sid:
        raise AdapterError('host init has no session_id')
    if any(row.get('session_id') not in (None, sid) for row in rows):
        raise AdapterError('stream mixes multiple session ids')
    success = (returncode == 0 and result.get('subtype') == 'success' and result.get('is_error') is False)
    if not success:
        raise AdapterError(f"host call did not complete successfully (returncode={returncode}, subtype={result.get('subtype')!r}, is_error={result.get('is_error')!r})")
    tools = init.get('tools')
    if tools is not None and (not isinstance(tools, list) or not all(isinstance(t, str) and t for t in tools)):
        raise AdapterError('host init has malformed tools list')
    host_version = init.get('claude_code_version')
    if not isinstance(host_version, str) or not host_version:
        raise AdapterError('host init has no claude_code_version')
    permission_denials = result.get('permission_denials', [])
    if not isinstance(permission_denials, list):
        permission_denials = []
    return {
        'session_id': sid,
        'host_version': host_version,
        'tools': sorted(tools) if isinstance(tools, list) else None,
        'observed_model_id': _observed_model(rows),
        'context_window': _context_window(rows),
        'cost_usd': _cost(result),
        'tokens_total': _usage_total(result),
        'host_duration_seconds': _host_duration(result),
        'wall_time_seconds': measured_wall_time,
        'permission_denials': permission_denials,
        'output': _text_output(rows, result),
    }


def _invoke(model_id, prompt, cwd, agent=None, timeout=600):
    if not shutil.which('claude'):
        raise AdapterError('claude CLI is not on PATH; live Anthropic execution is unavailable')
    cmd = ['claude', '-p', prompt, '--model', model_id,
           '--output-format', 'stream-json', '--verbose']
    if agent:
        cmd += ['--agent', agent]
    started = time.monotonic()
    proc = _run(cmd, cwd, timeout=timeout)
    wall = time.monotonic() - started
    parsed = parse_stream(proc.stdout, proc.returncode, wall)
    parsed['stderr'] = proc.stderr
    return parsed


def observe(model_id, capabilities, valid_hours=24, context_window=None,
            declared_cost_per_1k_input=None, declared_cost_per_1k_output=None,
            timeout=600):
    """Perform one real host call and return a model observation.

    Model/host/session fields come from the host stream when available. Capability
    classes and optional pricing/context overrides are operator declarations and
    are labelled as such; the adapter never derives a price from one cached turn.
    """
    observed_at = _utcnow()
    with tempfile.TemporaryDirectory(prefix='ante-nexus-anthropic-observe-') as td:
        parsed = _invoke(model_id, 'Return exactly ANTE_NEXUS_OBSERVATION.', Path(td), timeout=timeout)
    observed_model = parsed['observed_model_id'] or model_id
    window = parsed['context_window'] if parsed['context_window'] is not None else context_window
    valid_until = observed_at + dt.timedelta(hours=valid_hours)
    return {
        'model_id': observed_model,
        'provider': 'anthropic',
        'observed_at': _iso(observed_at),
        'valid_until': _iso(valid_until),
        'evidence_ref': parsed['session_id'],
        'host': 'claude-code',
        'host_version': parsed['host_version'],
        'capabilities': capabilities,
        'context_window': window,
        'declared_cost_per_1k_input': declared_cost_per_1k_input,
        'declared_cost_per_1k_output': declared_cost_per_1k_output,
        'provenance': {
            'model_id': 'host-stream' if parsed['observed_model_id'] else 'operator-selected target; host did not echo model id',
            'host_version': 'host-stream',
            'context_window': 'host-stream' if parsed['context_window'] is not None else ('operator-declared' if context_window is not None else 'UNKNOWN'),
            'capabilities': 'operator-declared requirement classes; not a measured quality claim',
            'declared_cost_per_1k_input': 'operator-declared' if declared_cost_per_1k_input is not None else 'UNKNOWN',
            'declared_cost_per_1k_output': 'operator-declared' if declared_cost_per_1k_output is not None else 'UNKNOWN',
            'call_cost_usd': 'host-result',
            'tokens_total': 'host-result',
        },
        'observation_call': {
            'cost_usd': parsed['cost_usd'],
            'tokens_total': parsed['tokens_total'],
            'wall_time_seconds': parsed['wall_time_seconds'],
            'host_duration_seconds': parsed['host_duration_seconds'],
        },
        'limitations': [
            'This record observes one host call; it does not establish model quality or superiority.',
            'Per-1k prices remain UNKNOWN unless an operator supplies them in the same unit used by routing.',
            'Capability classes are operator declarations unless separately supported by host/evaluation evidence.',
        ],
    }


def _frontmatter_name(profile_text):
    if not profile_text.startswith('---\n'):
        raise AdapterError('rendered agent profile has no YAML frontmatter')
    head, sep, _ = profile_text[4:].partition('\n---\n')
    if not sep:
        raise AdapterError('rendered agent profile frontmatter is not closed')
    data = yaml.safe_load(head)
    name = data.get('name') if isinstance(data, dict) else None
    if not isinstance(name, str) or not name.strip():
        raise AdapterError('rendered agent profile has no host-visible name')
    return name


def execute(packet, agent_id, model_id, authority_ref, operator, policy_expires,
            timeout=900):
    """Execute one already-authorized task packet. No planning or routing here."""
    if not isinstance(packet, dict):
        raise AdapterError('packet must be an object')
    for field, value in [('agent_id', agent_id), ('model_id', model_id),
                         ('authority_ref', authority_ref), ('operator', operator)]:
        if not isinstance(value, str) or not value.strip():
            raise AdapterError(f'{field} must be non-empty text')
    packet_bytes = json.dumps(packet, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    packet_sha = hashlib.sha256(packet_bytes).hexdigest()
    started_at = _utcnow()
    with tempfile.TemporaryDirectory(prefix='ante-nexus-anthropic-execute-') as td:
        workspace = Path(td)
        policy = {
            'host': 'claude-code', 'agent_id': agent_id, 'scope': 'project',
            'owner': operator, 'authority_ref': authority_ref,
            'expires': policy_expires, 'allowed_tools': ['Read'],
        }
        profile = workspace / '.claude' / 'agents' / f'{agent_id}.md'
        profile.parent.mkdir(parents=True, exist_ok=True)
        CAPABILITIES.render(agent_id, policy, profile)
        host_agent = _frontmatter_name(profile.read_text(encoding='utf-8'))
        packet_path = workspace / 'nexus-task.json'
        packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        prompt = (
            'Read ./nexus-task.json exactly once. Perform only the bounded analytical task described there. '
            'Do not modify files, call external services, or claim authority beyond the packet. '
            'Return the decision-relevant analysis and a concise summary, including unresolved uncertainty.'
        )
        parsed = _invoke(model_id, prompt, workspace, agent=host_agent, timeout=timeout)
    finished_at = _utcnow()
    if parsed['tools'] != ['Read']:
        raise AdapterError(f"host resolved tools {parsed['tools']!r}; expected the scoped ['Read'] boundary")
    if parsed['observed_model_id'] and parsed['observed_model_id'] != model_id:
        raise AdapterError(f"selected model {model_id!r} but host stream reported {parsed['observed_model_id']!r}")
    task = packet.get('task', {})
    return {
        'record_id': uuid.uuid4().hex[:16],
        'instance_id': packet.get('instance_id'),
        'task_id': task.get('id'),
        'agent_id': agent_id,
        'provider': 'anthropic',
        'model_id': model_id,
        'observed_model_id': parsed['observed_model_id'],
        'host_version': parsed['host_version'],
        'authority_ref': authority_ref,
        'operator': operator,
        'started_at': _iso(started_at),
        'finished_at': _iso(finished_at),
        'outcome': 'COMPLETED',
        'cost_usd': parsed['cost_usd'],
        'tokens_total': parsed['tokens_total'],
        'wall_time_seconds': parsed['wall_time_seconds'],
        'host_duration_seconds': parsed['host_duration_seconds'],
        'evidence_ref': parsed['session_id'],
        'level': task.get('level'),
        'vector': task.get('vector'),
        'permission_denials': parsed['permission_denials'],
        'packet_sha256': packet_sha,
        'output': parsed['output'],
        'limitations': [
            'The engine may authorize task readiness, the router target admissibility and the operator the model call; none establishes that this output is correct.',
            'Execution is scoped to a temporary project profile whose host-resolved tool set was exactly [Read].',
            'Cost/token counters are recorded only when the host result exposes them; wall time is measured by this adapter.',
        ],
    }


def _write(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    obs = sub.add_parser('observe', help='make one live host call and emit a model observation')
    obs.add_argument('--model', required=True)
    obs.add_argument('--output', required=True)
    obs.add_argument('--reasoning-depth', choices=['shallow', 'standard', 'extended'], required=True)
    obs.add_argument('--context-class', choices=['small', 'large'], required=True)
    obs.add_argument('--modality', action='append', choices=['text', 'vision', 'audio'], required=True)
    obs.add_argument('--tool-use', choices=['none', 'declared', 'enforced'], required=True)
    obs.add_argument('--determinism-need', choices=['exploratory', 'repeatable'], required=True)
    obs.add_argument('--context-window', type=int)
    obs.add_argument('--declared-cost-per-1k-input', type=float)
    obs.add_argument('--declared-cost-per-1k-output', type=float)
    obs.add_argument('--valid-hours', type=int, default=24)
    obs.add_argument('--timeout', type=int, default=600)
    args = ap.parse_args()
    try:
        caps = {
            'reasoning_depth': args.reasoning_depth,
            'context_class': args.context_class,
            'modality': args.modality,
            'tool_use': args.tool_use,
            'determinism_need': args.determinism_need,
        }
        record = observe(
            args.model, caps, valid_hours=args.valid_hours,
            context_window=args.context_window,
            declared_cost_per_1k_input=args.declared_cost_per_1k_input,
            declared_cost_per_1k_output=args.declared_cost_per_1k_output,
            timeout=args.timeout,
        )
        _write(args.output, [record])
        print(json.dumps(record, indent=2, ensure_ascii=False))
        return 0
    except (AdapterError, OSError, subprocess.SubprocessError, ValueError, TypeError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

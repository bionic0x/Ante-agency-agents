#!/usr/bin/env python3
"""test-host-acceptance.py — regression tests for the host acceptance validator.

The validator's job is to refuse records that claim more than their method can
support. These tests are mostly negative: each one is a way a well-meaning
harness could manufacture a green result for a boundary nobody tested.

Records are built at runtime from a real source file so the tests never go stale
on a checked-in hash, and the checked-in evidence is validated against the clock
it was taken at — an expired record is historical evidence, not a CI failure.
"""
import copy, datetime as dt, hashlib, importlib.util, json, pathlib, sys, tempfile, atexit

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('host_acceptance', ROOT / 'scripts' / 'host-acceptance.py')
ha = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ha)

SOURCE = pathlib.Path('specialized/specialized-pricing-analyst.md')
NOW = dt.datetime(2026, 1, 15, 12, 0, tzinfo=dt.timezone.utc)

EVIDENCE_TMP = tempfile.TemporaryDirectory(prefix='acceptance-test-', dir=ROOT)
atexit.register(EVIDENCE_TMP.cleanup)
TRANSCRIPT = pathlib.Path(EVIDENCE_TMP.name) / 'session.jsonl'
REF = str(TRANSCRIPT.relative_to(ROOT))
EVENTS = [
    {'type': 'system', 'subtype': 'init', 'session_id': 'test', 'cwd': '/tmp/test', 'tools': ['Read'], 'claude_code_version': '2.1.276'},
    {'type': 'assistant', 'session_id': 'test', 'message': {'content': [
        {'type': 'tool_use', 'id': 'read1', 'name': 'Read', 'input': {'file_path': './target.txt'}}]}},
    {'type': 'user', 'session_id': 'test', 'message': {'content': [
        {'type': 'tool_result', 'tool_use_id': 'read1', 'content': 'ante-host-probe'}]}},
    {'type': 'result', 'subtype': 'success', 'is_error': False, 'session_id': 'test'},
]
TRANSCRIPT.write_text('\n'.join(json.dumps(e) for e in EVENTS) + '\n')
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def expect_invalid(record, fragment, message):
    try:
        ha.validate(record, now=NOW)
    except ha.RecordError as exc:
        check(fragment in str(exc),
              f'{message}: rejected, but the reason did not mention {fragment!r} — got {exc}')
        return
    failures.append(f'{message}: ACCEPTED a record that should have been rejected')


def base_record():
    path = ROOT / SOURCE
    return {
        'schema_version': 1, 'host': 'claude-code', 'host_version': '2.1.276',
        'agent_id': 'specialized-pricing-analyst', 'agent_host_identifier': 'Pricing Analyst',
        'source_path': str(SOURCE), 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'installed_path': '.claude/agents/specialized-pricing-analyst.md', 'scope': 'project',
        'declared_allowlist': ['Read'], 'resolved_tools': ['Read'],
        'operator': 'test', 'authority_ref': 'TEST-AUTHORITY',
        'observed_at': (NOW - dt.timedelta(hours=1)).isoformat(),
        'valid_until': (NOW + dt.timedelta(hours=23)).isoformat(),
        'probes': [
            {'id': 'discovery', 'method': 'host-resolution', 'outcome': 'OBSERVED', 'evidence_ref': 'e'},
            {'id': 'system_prompt_integrity', 'method': 'filesystem', 'outcome': 'OBSERVED', 'evidence_ref': 'e'},
            {'id': 'allowlist_resolved', 'method': 'live-session', 'outcome': 'ENFORCED', 'evidence_ref': REF},
            {'id': 'permitted_operation', 'method': 'live-session', 'outcome': 'ENFORCED', 'evidence_ref': REF},
            {'id': 'denied_operation', 'method': 'live-session', 'outcome': 'ENFORCED', 'evidence_ref': REF},
            {'id': 'expiry', 'method': 'host-resolution', 'outcome': 'ENFORCED', 'evidence_ref': 'e'},
            {'id': 'revocation', 'method': 'host-resolution', 'outcome': 'ENFORCED', 'evidence_ref': 'e'},
            {'id': 'scope_isolation', 'method': 'host-resolution', 'outcome': 'ENFORCED', 'evidence_ref': 'e'},
        ],
    }


def mutate(**changes):
    record = base_record()
    record.update(changes)
    return record


def with_probe(pid, **changes):
    record = base_record()
    for probe in record['probes']:
        if probe['id'] == pid:
            probe.update(changes)
    return record


def main():
    status, findings, _ = ha.validate(base_record(), now=NOW)
    check(status == 'ACCEPTED', f'a complete, live-evidenced record should be ACCEPTED, got {status}')
    check(not findings, f'a complete record should produce no findings, got {findings}')

    # The rule the validator exists for: enforcement claimed from a file read.
    for pid in ('denied_operation', 'permitted_operation', 'allowlist_resolved'):
        expect_invalid(with_probe(pid, method='filesystem'), 'filesystem',
                       f'{pid} claiming ENFORCED from a filesystem read')

    # Execution claims need a session, not the host's agent listing.
    for pid in ('denied_operation', 'permitted_operation', 'allowlist_resolved'):
        expect_invalid(with_probe(pid, method='host-resolution'), 'cannot be established',
                       f'{pid} claiming ENFORCED from the host agent listing')

    # A record may not grade itself.
    record = base_record(); record['status'] = 'ACCEPTED'
    expect_invalid(record, 'derived', 'record asserting its own status')
    record = base_record(); record['accepted'] = True
    expect_invalid(record, 'derived', 'record asserting its own acceptance')

    # Evidence binding.
    expect_invalid(mutate(source_sha256='0' * 64), 'another source revision',
                   'record bound to a different source revision')
    expect_invalid(mutate(source_path='does/not/exist.md'), 'does not exist',
                   'record naming a source file that is not there')
    expect_invalid(with_probe('discovery', evidence_ref=''), 'evidence_ref',
                   'an attempted probe with no evidence reference')
    record = base_record()
    del record['probes'][0]['evidence_ref']
    expect_invalid(record, 'evidence_ref', 'an attempted probe missing evidence_ref entirely')

    # Freshness and coherence.
    expect_invalid(mutate(observed_at=(NOW - dt.timedelta(hours=5)).isoformat(),
                          valid_until=(NOW - dt.timedelta(hours=1)).isoformat()), 'expired',
                   'a record whose validity window has closed')
    expect_invalid(mutate(valid_until=(NOW - dt.timedelta(hours=2)).isoformat()),
                   'must be after observed_at', 'a record whose window ends before it starts')
    expect_invalid(mutate(observed_at=(NOW + dt.timedelta(hours=1)).isoformat()), 'future-dated',
                   'a future-dated record')
    expect_invalid(mutate(observed_at='2026-01-15T12:00:00'), 'timezone',
                   'a timestamp with no timezone offset')

    # An ENFORCED allowlist must actually match what the host resolved.
    expect_invalid(mutate(resolved_tools=['Read', 'Write']), 'resolved_tools != declared_allowlist',
                   'an allowlist reported ENFORCED while the host resolved more tools')
    expect_invalid(mutate(resolved_tools=None), 'resolved_tools is null',
                   'an allowlist reported ENFORCED with no resolved tool set')

    # Shape.
    expect_invalid(with_probe('discovery', outcome='ENFORCED'), 'not valid for a observation',
                   'an observation probe reporting an enforcement outcome')
    record = base_record(); record['probes'].append(dict(record['probes'][0]))
    expect_invalid(record, 'more than once', 'a duplicated probe')
    expect_invalid(with_probe('discovery', id='made_up_probe'), 'unknown probe id',
                   'an unrecognised probe id')
    record = base_record(); record['extra'] = 1
    expect_invalid(record, 'unknown field', 'a record with an unknown top-level field')

    # Gaps degrade the status; they never fail open.
    record = base_record(); record['probes'] = [p for p in record['probes'] if p['id'] != 'expiry']
    status, findings, _ = ha.validate(record, now=NOW)
    check(status == 'NOT_DEMONSTRATED', f'an absent probe should give NOT_DEMONSTRATED, got {status}')
    check(any('expiry' in f for f in findings), 'the absent probe should be named in the findings')

    record = with_probe('expiry', outcome='NOT_ENFORCED')
    status, _findings, _ = ha.validate(record, now=NOW)
    check(status == 'BOUNDARY_NOT_ENFORCED',
          f'an unenforced boundary should give BOUNDARY_NOT_ENFORCED, got {status}')

    record = with_probe('expiry', outcome='NOT_ATTEMPTED')
    record['probes'] = [{k: v for k, v in p.items() if k != 'evidence_ref'} if p['id'] == 'expiry'
                        else p for p in record['probes']]
    status, _findings, _ = ha.validate(record, now=NOW)
    check(status == 'NOT_DEMONSTRATED',
          f'a NOT_ATTEMPTED probe should give NOT_DEMONSTRATED, got {status}')

    # The capability observation projection refuses to invent resolved tools.
    observation = ha.emit_observation(base_record(), now=NOW)
    check(observation['resolved_tools'] == ['Read'], 'observation should carry the resolved tool set')
    check(observation['host_version'] == '2.1.276', 'observation should carry the host version')
    try:
        ha.emit_observation(with_probe('allowlist_resolved', outcome='NOT_ENFORCED'), now=NOW)
        failures.append('emit_observation produced an observation from an unenforced allowlist')
    except ha.RecordError:
        pass

    # Oracles must reject absence-of-side-effect and invocation-only false positives.
    resolved, outcomes = ha.evidence.assess(EVENTS)
    check(outcomes['permitted_operation'] == 'ENFORCED', 'matched successful Read result')
    check(outcomes['denied_operation'] == 'ENFORCED', 'Write withheld in completed session')
    variants = []
    events = copy.deepcopy(EVENTS); events[0]['tools'].append('Write')
    variants.append((events, 'denied_operation', 'offered Write with no side effect'))
    events = copy.deepcopy(EVENTS); events.pop(2)
    variants.append((events, 'permitted_operation', 'Read requested without result'))
    events = copy.deepcopy(EVENTS); events[2]['message']['content'][0]['is_error'] = True
    variants.append((events, 'permitted_operation', 'Read failed'))
    events = copy.deepcopy(EVENTS); events[2]['message']['content'][0]['tool_use_id'] = 'other'
    variants.append((events, 'permitted_operation', 'unrelated tool result'))
    events = copy.deepcopy(EVENTS); events[1]['message']['content'][0]['input']['file_path'] = './other.txt'
    variants.append((events, 'permitted_operation', 'wrong file was read'))
    events = copy.deepcopy(EVENTS); events.pop()
    variants.append((events, 'denied_operation', 'missing completion event'))
    events = copy.deepcopy(EVENTS); events[-1]['is_error'] = True
    variants.append((events, 'denied_operation', 'failed session'))
    events = copy.deepcopy(EVENTS); events[1]['session_id'] = 'another'
    variants.append((events, 'permitted_operation', 'mixed sessions'))
    for events, pid, label in variants:
        check(ha.evidence.assess(events)[1][pid] != 'ENFORCED', label)
    check(ha.evidence.assess(EVENTS, returncode=1)[1]['denied_operation'] != 'ENFORCED',
          'process failed despite successful-looking transcript')
    check(ha.evidence.assess(EVENTS, wrote=True)[1]['denied_operation'] == 'NOT_ENFORCED',
          'canary side effect is an observed failure')
    expect_invalid(with_probe('permitted_operation', evidence_ref='missing.jsonl'),
                   'evidence must be a file', 'nonexistent transcript')
    expect_invalid(mutate(host_version='other-version'), 'host/version', 'wrong host version')
    expect_invalid(mutate(host='kimi'), 'host/version', 'Claude evidence bound to Kimi')
    check(ha.validate(with_probe('permitted_operation', outcome='INCONCLUSIVE', evidence_ref=''), now=NOW)[0] == 'NOT_DEMONSTRATED', 'missing evidence for inconclusive execution')
    expect_invalid(mutate(agent_id='another-agent'), 'agent_id', 'cross-agent record')
    expect_invalid(mutate(source_path='../outside.md'), 'within root', 'out-of-root source')
    expect_invalid(mutate(schema_version=True), 'schema_version', 'boolean schema version')
    original = TRANSCRIPT.read_text()
    TRANSCRIPT.write_text('\n'.join(json.dumps(e) for e in EVENTS if e['type'] != 'user'))
    expect_invalid(base_record(), 'transcript does not establish', 'claimed Read without its result')
    TRANSCRIPT.write_text(original)

    # Checked-in evidence: valid as of the clock it was taken at.
    for path in sorted((ROOT / 'evidence' / 'host-acceptance').glob('*.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        taken = dt.datetime.fromisoformat(record['observed_at']) + dt.timedelta(seconds=1)
        try:
            status, _findings, _ = ha.validate(record, now=taken)
            print(f'  evidence {path.name}: {status} (as of {record["observed_at"]})')
        except ha.RecordError as exc:
            failures.append(f'checked-in evidence {path.name} is not a valid record: {exc}')

    for failure in failures:
        print(f'  FAIL {failure}')
    print(f'\nResults: {"FAILED" if failures else "PASSED"} ({len(failures)} failures)')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

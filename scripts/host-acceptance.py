#!/usr/bin/env python3
"""host-acceptance.py — validate live host acceptance records.

Installation and offline conversion tests establish what a FILE contains. They
establish nothing about what a HOST does with it: whether the agent is
discovered, which tools the host actually resolves for it, whether an operation
outside the allowlist is refused, and whether removing the profile withdraws it.
This validator consumes records produced by a live probe against a real host and
refuses any record that claims more than its own method can support.

Execution claims require `live-session`; availability claims may use host resolution.
A record that reports enforcement from a filesystem read is rejected, not
downgraded — a harness that silently accepts weaker evidence is worse than no
harness, because it manufactures a green result for an untested boundary.

The record never declares its own status. Status is derived here from the probe
outcomes, so a record cannot assert `ACCEPTED` about itself.

Usage:
  host-acceptance.py validate RECORD...            # derive and print status
  host-acceptance.py validate RECORD --require accepted
  host-acceptance.py emit-observation RECORD       # agent-capabilities.py input
"""
import argparse, datetime as dt, hashlib, importlib.util, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("host_session_evidence", ROOT / "scripts/host-session-evidence.py")
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)
SCHEMA_VERSION = 1
HOSTS = {'claude-code', 'kimi'}
SCOPES = {'project', 'user'}
# filesystem      we read the installed file ourselves. Establishes content, never behavior.
# host-resolution the host binary resolved something and told us, without a model turn
#                 (e.g. it printed its own agent listing). Host behavior, cheap and exact.
# live-session    a real session ran: tool sets, tool calls and side effects are observable.
METHODS = {'filesystem', 'host-resolution', 'live-session'}

OBSERVATION_OUTCOMES = {'OBSERVED', 'NOT_OBSERVED'}
ENFORCEMENT_OUTCOMES = {'ENFORCED', 'NOT_ENFORCED'}
INCONCLUSIVE_OUTCOMES = {'NOT_ATTEMPTED', 'INCONCLUSIVE'}

# kind: what class of claim the probe makes. methods: the only methods whose
# evidence can support that claim. An enforcement claim needs a live session.
PROBES = {
    'discovery':               ('observation', {'host-resolution', 'live-session'}),
    'system_prompt_integrity': ('observation', {'filesystem', 'live-session'}),
    'allowlist_resolved':      ('enforcement', {'live-session'}),
    'permitted_operation':     ('enforcement', {'live-session'}),
    'denied_operation':        ('enforcement', {'live-session'}),
    # These three are claims about what the host OFFERS, which its own resolution
    # settles. The three above are claims about what the host EXECUTED, which only a
    # real session can settle.
    'expiry':                  ('enforcement', {'host-resolution', 'live-session'}),
    'revocation':              ('enforcement', {'host-resolution', 'live-session'}),
    'scope_isolation':         ('enforcement', {'host-resolution', 'live-session'}),
}

RECORD_FIELDS = {
    'schema_version', 'host', 'host_version', 'agent_id', 'agent_host_identifier',
    'source_path', 'source_sha256', 'installed_path', 'scope', 'declared_allowlist',
    'resolved_tools', 'operator', 'authority_ref', 'observed_at', 'valid_until', 'probes',
}
DERIVED_FIELDS = {'status', 'accepted', 'result', 'verdict'}


class RecordError(ValueError):
    pass


def _ts(value, name):
    if not isinstance(value, str):
        raise RecordError(f'{name} must be an ISO-8601 string')
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise RecordError(f'{name} is not ISO-8601: {exc}') from exc
    if parsed.tzinfo is None:
        raise RecordError(f'{name} must carry an explicit timezone offset')
    return parsed


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise RecordError(f'{name} must be a non-empty string')
    return value


def _tools(value, name):
    if not isinstance(value, list) or not all(isinstance(t, str) and t.strip() for t in value):
        raise RecordError(f'{name} must be a list of non-empty tool names')
    if len(set(value)) != len(value):
        raise RecordError(f'{name} contains duplicates')
    return value


def validate(record, now=None, root=ROOT):
    """Return (status, findings, probes). Evidence is supplied, not authenticated."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if not isinstance(record, dict):
        raise RecordError('record must be a JSON object')

    declared = DERIVED_FIELDS & set(record)
    if declared:
        raise RecordError(
            f'record declares derived field(s) {sorted(declared)}; status is derived '
            'from probe outcomes, never asserted by the record')
    unknown = set(record) - RECORD_FIELDS
    if unknown:
        raise RecordError(f'unknown field(s): {sorted(unknown)}')
    missing = RECORD_FIELDS - set(record)
    if missing:
        raise RecordError(f'missing field(s): {sorted(missing)}')

    if type(record['schema_version']) is not int or record['schema_version'] != SCHEMA_VERSION:
        raise RecordError(f'schema_version must be {SCHEMA_VERSION}')
    if not isinstance(record['host'], str) or record['host'] not in HOSTS:
        raise RecordError(f"host must be one of {sorted(HOSTS)}")
    if not isinstance(record['scope'], str) or record['scope'] not in SCOPES:
        raise RecordError(f"scope must be one of {sorted(SCOPES)}")
    for field in ('host_version', 'agent_id', 'agent_host_identifier',
                  'source_path', 'installed_path', 'operator', 'authority_ref'):
        _text(record[field], field)

    # Bind the record to one source revision, the way a capability observation does.
    root = pathlib.Path(root).resolve()
    source = (root / record['source_path']).resolve()
    if pathlib.Path(record['source_path']).is_absolute() or not source.is_relative_to(root):
        raise RecordError('source_path must stay within root')
    if not source.is_file():
        raise RecordError(f"source_path does not exist: {record['source_path']}")
    if source.stem != record['agent_id']:
        raise RecordError('agent_id does not match source_path')
    if not isinstance(record['source_sha256'], str):
        raise RecordError('source_sha256 must be a string')
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if record['source_sha256'] != actual:
        raise RecordError('source_sha256 refers to another source revision '
                          f"(record {record['source_sha256'][:12]}…, file {actual[:12]}…)")

    observed_at, valid_until = _ts(record['observed_at'], 'observed_at'), _ts(record['valid_until'], 'valid_until')
    if observed_at > now:
        raise RecordError('observed_at is future-dated')
    if valid_until <= observed_at:
        raise RecordError('valid_until must be after observed_at')
    if valid_until <= now:
        raise RecordError('record has expired; re-run the probe against the current host')

    allowlist = _tools(record['declared_allowlist'], 'declared_allowlist')
    resolved = record['resolved_tools']
    if resolved is not None:
        _tools(resolved, 'resolved_tools')

    probes = record['probes']
    if not isinstance(probes, list) or not probes:
        raise RecordError('probes must be a non-empty list')
    seen, findings = {}, []
    for index, probe in enumerate(probes):
        where = f'probes[{index}]'
        if not isinstance(probe, dict):
            raise RecordError(f'{where} must be an object')
        unknown = set(probe) - {'id', 'method', 'outcome', 'evidence_ref', 'detail'}
        if unknown:
            raise RecordError(f'{where} has unknown field(s): {sorted(unknown)}')
        pid = probe.get('id')
        if not isinstance(pid, str) or pid not in PROBES:
            raise RecordError(f'{where}: unknown probe id {pid!r}; expected one of {sorted(PROBES)}')
        if pid in seen:
            raise RecordError(f'{where}: probe {pid!r} appears more than once')
        kind, permitted_methods = PROBES[pid]
        method, outcome = probe.get('method'), probe.get('outcome')
        if not isinstance(method, str) or method not in METHODS:
            raise RecordError(f'{where}: method must be one of {sorted(METHODS)}')

        allowed_outcomes = (ENFORCEMENT_OUTCOMES if kind == 'enforcement'
                            else OBSERVATION_OUTCOMES) | INCONCLUSIVE_OUTCOMES
        if not isinstance(outcome, str) or outcome not in allowed_outcomes:
            raise RecordError(f'{where}: outcome {outcome!r} is not valid for a {kind} probe '
                              f'(expected one of {sorted(allowed_outcomes)})')
        if outcome in INCONCLUSIVE_OUTCOMES:
            seen[pid] = outcome
            continue

        # The rule this validator exists for.
        if outcome in ENFORCEMENT_OUTCOMES and method == 'filesystem':
            raise RecordError(
                f"{where}: probe {pid!r} reports {outcome} from method 'filesystem'. "
                'Reading the installed file establishes what it contains, never what the '
                'host did with it. An enforcement outcome needs host behavior.')
        if method not in permitted_methods:
            raise RecordError(f'{where}: probe {pid!r} cannot be established by method '
                              f'{method!r}; permitted: {sorted(permitted_methods)}')
        ref = _text(probe.get('evidence_ref'), f'{where}.evidence_ref')
        seen[pid] = outcome

    absent = sorted(set(PROBES) - set(seen))
    for pid in absent:
        findings.append(f'probe {pid!r} is absent (treated as NOT_ATTEMPTED)')
        seen[pid] = 'NOT_ATTEMPTED'

    # The allowlist probe carries a checkable claim: enforcement means the host
    # resolved exactly the declared allowlist, no more and no less.
    if seen['allowlist_resolved'] == 'ENFORCED':
        if resolved is None:
            raise RecordError('allowlist_resolved is ENFORCED but resolved_tools is null')
        if sorted(resolved) != sorted(allowlist):
            raise RecordError(
                'allowlist_resolved is ENFORCED but resolved_tools != declared_allowlist '
                f'(resolved {sorted(resolved)}, declared {sorted(allowlist)}); '
                'report NOT_ENFORCED instead')

    for probe in probes:
        pid, method, outcome = probe['id'], probe['method'], probe['outcome']
        ref, where = probe.get('evidence_ref', ''), f'probe {pid}'
        if outcome in INCONCLUSIVE_OUTCOMES:
            continue
        if method == 'live-session' and pid in {'allowlist_resolved', 'permitted_operation', 'denied_operation'}:
            path = (root / ref).resolve()
            if pathlib.Path(ref).is_absolute() or not path.is_relative_to(root) or not path.is_file():
                raise RecordError(f'{where}: live-session evidence must be a file within root')
            events = evidence.parse_events(path.read_text(encoding='utf-8'))
            inits = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
            if record['host'] != 'claude-code' or len(inits) != 1 or inits[0].get('claude_code_version') != record['host_version']:
                raise RecordError(f'{where}: transcript host/version does not match record')
            session_tools, supported = evidence.assess(events)
            if session_tools != resolved:
                raise RecordError(f'{where}: transcript tools do not match resolved_tools')
            if pid == 'allowlist_resolved' and session_tools is not None:
                supported[pid] = 'ENFORCED' if sorted(allowlist) == session_tools else 'NOT_ENFORCED'
            if outcome == 'ENFORCED' and supported[pid] != 'ENFORCED':
                raise RecordError(f'{where}: transcript does not establish {pid} ENFORCED')
    failed = sorted(p for p, o in seen.items() if o in {'NOT_OBSERVED', 'NOT_ENFORCED'})
    pending = sorted(p for p, o in seen.items() if o in INCONCLUSIVE_OUTCOMES)
    findings += [f'probe {p!r}: {seen[p]}' for p in failed + pending]

    if failed:
        status = 'BOUNDARY_NOT_ENFORCED'
    elif pending:
        status = 'NOT_DEMONSTRATED'
    else:
        status = 'ACCEPTED'
    return status, findings, seen


def emit_observation(record, root=ROOT, now=None):
    """Project the record onto the agent-capabilities.py observation contract."""
    _status, _findings, seen = validate(record, now=now, root=root)
    if seen['allowlist_resolved'] != 'ENFORCED':
        raise RecordError('cannot emit a capability observation: allowlist_resolved is '
                          f"{seen['allowlist_resolved']}, so resolved_tools is not established")
    return {
        'host': record['host'], 'agent_id': record['agent_id'],
        'host_version': record['host_version'],
        'evidence_ref': next(p['evidence_ref'] for p in record['probes']
                             if p['id'] == 'allowlist_resolved'),
        'configuration_ref': record['installed_path'],
        'source_sha256': record['source_sha256'],
        'observed_at': record['observed_at'], 'valid_until': record['valid_until'],
        'resolved_tools': record['resolved_tools'],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['validate', 'emit-observation'])
    ap.add_argument('record', nargs='+')
    ap.add_argument('--require', choices=['accepted', 'no-unenforced-boundary'],
                    help='exit non-zero unless every record reaches this bar')
    ap.add_argument('--root', default=str(ROOT))
    args = ap.parse_args()
    if args.command == 'emit-observation' and args.require:
        ap.error('--require is only supported by validate')
    root, worst = pathlib.Path(args.root), 0

    for path in args.record:
        try:
            record = json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
            if args.command == 'emit-observation':
                print(json.dumps(emit_observation(record, root=root), indent=2))
                continue
            status, findings, _seen = validate(record, root=root)
        except (OSError, json.JSONDecodeError, RecordError) as exc:
            print(f'INVALID {path}: {exc}', file=sys.stderr)
            worst = 2
            continue
        print(f'{status:17} {path}')
        for finding in findings:
            print(f'    - {finding}')
        if args.require == 'accepted' and status != 'ACCEPTED':
            worst = max(worst, 1)
        if args.require == 'no-unenforced-boundary' and status == 'BOUNDARY_NOT_ENFORCED':
            worst = max(worst, 1)
    return worst


if __name__ == '__main__':
    sys.exit(main())

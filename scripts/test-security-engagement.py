#!/usr/bin/env python3
"""Regression tests for the security engagement contract.

The contract's value is that it fails when it should. These tests build agent
frontmatter/bodies at runtime and assert the checker's verdicts, so they never
depend on the current wording of a real agent.
"""
import copy, importlib.util, json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('cse', ROOT / 'scripts' / 'check-security-engagement.py')
cse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cse)
REG = cse.load_registry()

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def agent(engagement, body):
    fm = '---\nname: Fixture\ndescription: fixture\ncolor: "#000000"\n'
    if engagement is not None:
        fm += f'engagement: {engagement}\n'
    return fm + '---\n\n' + body


def verdict(text):
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, dir=ROOT / 'security') as fh:
        fh.write(text)
        path = Path(fh.name)
    try:
        findings, declared, advisories = cse.check_file(path, REG)
    finally:
        path.unlink(missing_ok=True)
    return findings, declared, advisories


OFFENSIVE_BODY = ('Verify prior written authorization. Test only what the rules of engagement mark '
                  'in-scope; anything out of scope is untouchable. Halt and escalate on any boundary. '
                  'Never cause denial of service or data destruction. This declaration is not authorization.')
DEFENSIVE_BODY = ('Acts only on assets the operator owns. All changes run under change control with a '
                  'rollback. This declaration is not authorization.')


def main():
    # Passive agent with nothing extra passes.
    f, d, _ = verdict(agent('passive-analysis', 'Reads code and writes a report.'))
    check(not f and d == 'passive-analysis', f'clean passive agent should pass, got {f}')

    # Missing engagement field fails.
    f, d, _ = verdict(agent(None, 'Reads code.'))
    check(any('missing `engagement:`' in x for x in f), 'missing engagement must fail')

    # Unknown class fails.
    f, d, _ = verdict(agent('freelance-hacking', 'whatever'))
    check(any('unknown engagement class' in x for x in f), 'unknown class must fail')

    # Offensive agent lacking every obligation fails on each one.
    f, _, _ = verdict(agent('authorized-offensive', 'I attack things.'))
    for token in ('written_authorization', 'scope_boundary', 'stop_condition',
                  'no_destruction', 'not_authorization'):
        check(any(token in x for x in f), f'offensive agent missing {token} must be flagged')

    # Offensive agent with the full RoE passes.
    f, _, _ = verdict(agent('authorized-offensive', OFFENSIVE_BODY))
    check(not f, f'complete offensive agent should pass, got {f}')

    # Drop one obligation and only that one fails.
    partial = OFFENSIVE_BODY.replace('This declaration is not authorization.', '')
    f, _, _ = verdict(agent('authorized-offensive', partial))
    check(len(f) == 1 and 'not_authorization' in f[0],
          f'removing exactly the not-authorization line should fail exactly once, got {f}')

    # Defensive agent needs own-assets + change-control + not-authorization.
    f, _, _ = verdict(agent('active-defensive', 'Monitors things in real time.'))
    for token in ('own_assets', 'change_control', 'not_authorization'):
        check(any(token in x for x in f), f'defensive agent missing {token} must be flagged')
    f, _, _ = verdict(agent('active-defensive', DEFENSIVE_BODY))
    check(not f, f'complete defensive agent should pass, got {f}')

    # Misdeclaration is ADVISORY, never a failure: first-person offensive phrasing
    # under a passive class is reported but does not fail the build.
    f, _, adv = verdict(agent('passive-analysis', 'I will exploit the target host to prove it.'))
    check(not f, 'first-person offensive phrasing must not fail a passive agent (advisory only)')
    check(any('offensive phrasing' in a for a in adv), 'that phrasing should raise an advisory')

    # And naming attacker techniques as subject matter raises NOTHING — the false
    # positive the design exists to avoid.
    f, _, adv = verdict(agent('passive-analysis',
        'Analysts track how adversaries use C2, lateral movement, privilege escalation and '
        'exfiltration. This agent detects and documents those techniques.'))
    check(not f and not adv, f'describing attacker TTPs must be clean, got findings={f} advisories={adv}')

    # Malformed frontmatter must fail cleanly, including duplicate/non-scalar fields.
    malformed = [
        '---\nengagement: passive-analysis\nReads code.',
        '-- trailing\nengagement: passive-analysis\n---\nReads code.',
        agent('[passive-analysis]', 'Reads code.'),
        agent('{class: passive-analysis}', 'Reads code.'),
        agent('"unterminated', 'Reads code.'),
        agent('passive-analysis\nengagement: passive-analysis', 'Reads code.'),
    ]
    for text in malformed:
        f, _, _ = verdict(text)
        check(bool(f), f'malformed frontmatter must fail: {text!r}')

    for wrapper in ('<!-- {} -->', '```text\n{}\n```',
                    '   ~~~text\n{}\n   ~~~~', '```text\n{}'):
        f, _, _ = verdict(agent('authorized-offensive', wrapper.format(OFFENSIVE_BODY)))
        check(len(f) == 5, 'comments and fenced examples must not satisfy obligations')
    for before, after, token in (
        ('Halt and escalate', 'Configure the desktop', 'stop_condition'),
        ('prior written authorization', 'prior authorization', 'written_authorization'),
        ('Never cause denial of service or data destruction.',
         'Study denial of service and data destruction.', 'no_destruction'),
    ):
        f, _, _ = verdict(agent('authorized-offensive', OFFENSIVE_BODY.replace(before, after)))
        check(len(f) == 1 and token in f[0], f'weak phrase must not satisfy {token}: {f}')
    f, _, adv = verdict(agent('passive-analysis',
        'Adversaries establish persistence and run the exploit. We document their behavior.'))
    check(not f and not adv, 'third-person descriptions must not trigger an advisory')

    # Discovery includes nested profiles, excludes division documentation, and fails empty.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'divisions.json').write_text(json.dumps({'divisions': {'security': {}}}))
        (root / 'security' / 'nested').mkdir(parents=True)
        (root / 'security' / 'README.md').write_text('Division documentation')
        try:
            cse.security_agents(root)
            failures.append('an empty security division must fail discovery')
        except ValueError:
            pass
        nested = root / 'security' / 'nested' / 'fixture.md'
        nested.write_text(agent('passive-analysis', 'Reads code.'))
        check(cse.security_agents(root) == [nested], 'nested security agents must be discovered')
        check(not cse.check_file(nested, REG, root)[0], 'alternate repository root must work')

    # Exercise the public CLI with a relative path and multiple findings on one agent.
    with tempfile.NamedTemporaryFile('w', suffix='.md', dir=ROOT / 'security') as fh:
        fh.write(agent('authorized-offensive', 'No policy language.'))
        fh.flush()
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/check-security-engagement.py'),
                                 str(Path(fh.name).relative_to(ROOT))], cwd=ROOT,
                                capture_output=True, text=True)
        check(result.returncode == 1 and 'Results: 0/1' in result.stdout
              and 'Traceback' not in result.stderr, 'CLI must count failed agents, not findings')
        fh.seek(0)
        fh.truncate()
        fh.write(agent('passive-analysis', 'Reads code.'))
        fh.flush()
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/check-security-engagement.py'),
                                 str(Path(fh.name).relative_to(ROOT))], cwd=ROOT,
                                capture_output=True, text=True)
        check(result.returncode == 0 and 'Results: 1/1' in result.stdout,
              'CLI must accept valid relative paths')

    # Mutate a valid registry so every validation targets the intended defect.
    bad_registries = []
    def mutate(change):
        bad = copy.deepcopy(REG)
        change(bad)
        bad_registries.append(json.dumps(bad))
    mutate(lambda r: r.update(schema_version=True))
    mutate(lambda r: r['classes'].append('passive-analysis'))
    mutate(lambda r: r['definitions']['active-defensive'].update(acts_only_on_own_assets='yes'))
    mutate(lambda r: r['definitions']['authorized-offensive'].update(required_language=[]))
    mutate(lambda r: r['definitions']['active-defensive']['required_language'].append('ghost'))
    mutate(lambda r: r['required_language']['stop_condition'].update(any_of=['']))
    mutate(lambda r: r['required_language']['stop_condition'].update(any_of=['stop', 'stop']))
    bad_registries.append(json.dumps(REG).replace('"schema_version": 1',
                                                   '"schema_version": 1, "schema_version": 1'))
    for text in bad_registries:
        with tempfile.NamedTemporaryFile('w', suffix='.json') as fh:
            fh.write(text)
            fh.flush()
            try:
                cse.load_registry(fh.name)
                failures.append('invalid registry mutation must be rejected')
            except ValueError:
                pass

    # Every real security agent satisfies its class.
    findings_total = 0
    for path in cse.security_agents():
        f, _, _ = cse.check_file(path, REG)
        findings_total += len(f)
    check(findings_total == 0, f'the live security division must be clean, got {findings_total} findings')

    for f in failures:
        print(f'  FAIL {f}')
    print(f'\nResults: {"FAILED" if failures else "PASSED"} ({len(failures)} failures)')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""nexus-optimize.py — propose a bounded edit to one agent profile (NEXUS Overdrive, Phase 3).

The profile optimizer is the agency improving itself. A self-improving loop fails
by fitting the test (XV.12), so every limit here is mechanical:

  evidence     development-split packs only. Feedback that cites a held-out pack
               is refused: the optimizer must never see the evidence that will
               judge it.
  scope        one existing profile, body only. The frontmatter (name, tools,
               permissions, colour) is copied byte for byte, so a proposal cannot
               grant itself capability.
  size         the body may change by at most --max-change of its length.
  overfitting  a proposal that names an evidence pack or copies eight
               consecutive words of a pack's materials is refused: the lesson must
               be general, not the case's answer.
  checks       the proposed file passes scripts/lint-agents.sh, keeps the
               Identity, Core Mission and Critical Rules sections, and lies
               outside strategy/overdrive-protected.json.

    nexus-optimize.py propose --agent SLUG --evidence FILE --out DIR
                              [--executor claude|fake] [--model M] [--operator NAME] [--max-change 0.3]

Output: the proposed profile, a unified diff and proposal.json. Nothing is
committed or merged. Admission is decided elsewhere: an independent evaluator runs
`nexus-improve.py gate --improver profile-optimizer` on held-out packs the
optimizer never read, and a human merges.

Evidence file:
  {"schema_version": 1, "observations": [
     {"pack": "<development pack dir>", "failures": [{"rubric": "fatal_defects",
      "item": "<rubric text>", "note": "<what the artifact did>"}]}]}
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import fnmatch
import importlib.util
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OPTIMIZER_AGENT = 'agents-orchestrator'
IMPROVER_LABEL = 'profile-optimizer'
MAX_ATTEMPTS = 2
SECTIONS = ('Identity', 'Core Mission', 'Critical Rules')
SHINGLE = 8
_spec = importlib.util.spec_from_file_location('casepack_for_optimize', ROOT / 'scripts/nexus-casepack.py')
CASEPACK = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(CASEPACK)


class OptimizeError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise OptimizeError(message)


def split_profile(text):
    require(text.startswith('---\n'), 'profile has no frontmatter')
    end = text.index('\n---\n', 4) + len('\n---\n')
    return text[:end], text[end:]


def profile_path(slug):
    _, agents, _ = runpy.run_path(str(ROOT / 'scripts/build-catalog.py'))['collect']()
    found = {a['slug']: a for a in agents}
    require(slug in found, f'unknown agent {slug!r}')
    path = Path(found[slug]['path'])
    return path if path.is_absolute() else ROOT / path


def load_evidence(path):
    evidence = json.loads(Path(path).read_text(encoding='utf-8'))
    require(isinstance(evidence, dict) and evidence.get('schema_version') == 1, 'evidence schema_version must be 1')
    observations = evidence.get('observations')
    require(isinstance(observations, list) and observations, 'evidence needs observations')
    cases = []
    for i, obs in enumerate(observations):
        pack_dir = Path(obs.get('pack', ''))
        if not pack_dir.is_absolute():
            pack_dir = (Path(path).parent / pack_dir).resolve()
        pack = CASEPACK.verify(pack_dir)
        require(pack['split'] == 'development', f"observations[{i}]: pack {pack['id']} is {pack['split']}; "
                'the optimizer reads development packs only and must never see held-out evidence')
        failures = obs.get('failures')
        require(isinstance(failures, list) and failures and all(
            isinstance(f, dict) and {'rubric', 'item', 'note'} <= set(f) for f in failures),
            f'observations[{i}]: failures need rubric, item and note')
        materials = {name: (pack_dir / name).read_text(encoding='utf-8') for name in pack['materials']}
        cases.append({'pack_id': pack['id'], 'brief': pack['brief'], 'rubric': pack['rubric'],
                      'failures': failures, 'materials': materials})
    return cases


def words(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def shingles(text, n=SHINGLE):
    w = words(text)
    return {' '.join(w[i:i + n]) for i in range(len(w) - n + 1)}


def check_body(old_body, new_body, cases, max_change, path, frontmatter):
    require(not new_body.lstrip().startswith('---'), 'return the body only; the frontmatter is fixed')
    change = abs(len(new_body) - len(old_body)) / max(1, len(old_body))
    require(change <= max_change, f'body length changed by {change:.0%}, above the {max_change:.0%} bound')
    require(new_body.strip() != old_body.strip(), 'the proposal changes nothing')
    for section in SECTIONS:
        require(re.search(rf'^#+ .*{re.escape(section)}', new_body, re.MULTILINE),
                f'the proposal drops the {section} section')
    old_shingles = shingles(old_body)
    for case in cases:
        require(case['pack_id'] not in new_body or case['pack_id'] in old_body,
                f"the proposal names evidence pack {case['pack_id']}; lessons must be general")
        for name, text in case['materials'].items():
            copied = sorted((shingles(new_body) & shingles(text)) - old_shingles)
            if copied:
                raise OptimizeError(f"the proposal copies case material from {case['pack_id']}/{name}: "
                                    f"'{copied[0]}'")
    policy = json.loads((ROOT / 'strategy/overdrive-protected.json').read_text())
    rel = str(path.relative_to(ROOT))
    require(not any(fnmatch.fnmatchcase(rel, p) for p in policy['protected']), f'{rel} is protected')
    return round(change, 3)


def lint(path_text, slug, out):
    """lint-agents.sh on the proposed file, placed where an agent file lives."""
    probe = out / 'lint' / slug / f'{slug}.md'
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(path_text, encoding='utf-8')
    proc = subprocess.run(['bash', str(ROOT / 'scripts/lint-agents.sh'), str(probe)], capture_output=True,
                          text=True, cwd=ROOT)
    require(proc.returncode == 0, 'lint-agents.sh refused the proposal: ' + (proc.stdout + proc.stderr)[-400:])


def packet(slug, frontmatter, body, cases, max_change, refusal=None, previous=None):
    p = {'role': 'Profile optimizer. Improve this agent\'s instructions so the failures below become less '
                 'likely in general, without fitting these cases.',
         'agent': slug, 'frontmatter_fixed': frontmatter, 'current_body': body,
         'development_feedback': [{'brief': c['brief'], 'rubric': c['rubric'], 'failures': c['failures']}
                                  for c in cases],
         'rules': ['Return the full revised body in one fenced markdown block, no frontmatter. The body '
                   'contains ``` fences, so open yours with ````markdown and close it with ````.',
                   f'Keep the sections {", ".join(SECTIONS)}. Change the body length by at most {max_change:.0%}.',
                   'State general practices (what to check, when to stop, what to report), never facts, '
                   'figures, names or wording from the cases.',
                   'Do not grant tools, permissions or authority; the frontmatter cannot change.']}
    if refusal:
        p['previous_proposal'] = previous
        p['refusal'] = refusal
    return p


def parse(output):
    """The body inside the outermost markdown fence. Profiles contain ``` blocks, so the reply
    may use a longer fence (````markdown ... ````); the closing fence must match its length."""
    match = re.search(r'^(`{3,})(?:markdown|md)[ \t]*\n(.*)\n\1[ \t]*$', output, re.DOTALL | re.MULTILINE)
    require(match is not None, 'the optimizer returned no fenced markdown block')
    return '\n' + match.group(2).strip('\n') + '\n'


def claude_optimizer(operator):
    anthropic = runpy.run_path(str(ROOT / 'scripts/nexus-anthropic.py'), run_name='anthropic_for_optimize')

    def run(p, model):
        expires = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).replace(microsecond=0)
        record = anthropic['execute'](p, OPTIMIZER_AGENT, model, authority_ref='profile proposal for gated review',
                                      operator=operator, policy_expires=expires.isoformat().replace('+00:00', 'Z'))
        return {'output': record['output'], 'cost_usd': record['cost_usd'], 'evidence_ref': record['evidence_ref']}
    return run


def fake_optimizer(p, model):
    """Deterministic for tests: add one general rule under Critical Rules."""
    body = p['current_body']
    rule = ('- Before recommending, check that the measure being improved still tracks the outcome it '
            'stands for, and report it when the two diverge.\n')
    revised = re.sub(r'(^#+ .*Critical Rules.*\n)', lambda m: m.group(1) + rule, body, count=1, flags=re.MULTILINE)
    return {'output': f'```markdown\n{revised.strip()}\n```', 'cost_usd': 0.0, 'evidence_ref': 'fake-optimizer'}


def propose(slug, evidence_path, out, executor, model='claude-opus-5-5', max_change=0.3):
    out = Path(out)
    require(not out.exists(), f'{out} already exists; a proposal is written once')
    path = profile_path(slug)
    original = path.read_text(encoding='utf-8')
    frontmatter, body = split_profile(original)
    cases = load_evidence(evidence_path)
    out.mkdir(parents=True)
    (out / 'attempts').mkdir()
    attempts, refusal, previous, accepted = [], None, None, None
    for n in range(1, MAX_ATTEMPTS + 1):
        sent = packet(slug, frontmatter, body, cases, max_change, refusal, previous)
        result = executor(sent, model)
        try:
            core = parse(result['output']).strip('\n')
            # Keep the original's surrounding whitespace so the diff shows only the edit.
            new_body = body[:len(body) - len(body.lstrip('\n'))] + core + body[len(body.rstrip('\n')):]
            change = check_body(body, new_body, cases, max_change, path, frontmatter)
            lint(frontmatter + new_body, slug, out)
            accepted, refusal = (new_body, change), None
        except OptimizeError as exc:
            refusal, previous = str(exc), result['output']
        attempts.append({'attempt': n, 'refusal': refusal, 'cost_usd': result.get('cost_usd'),
                         'evidence_ref': result.get('evidence_ref')})
        (out / 'attempts' / f'{n:03d}.json').write_text(json.dumps(
            {**attempts[-1], 'packet': sent, 'output': result['output']}, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8')
        if accepted:
            break
    summary = {'status': 'PROPOSED' if accepted else 'REFUSED', 'agent': slug,
               'path': str(path.relative_to(ROOT)), 'improver': IMPROVER_LABEL, 'attempts': attempts,
               'evidence_packs': [c['pack_id'] for c in cases]}
    if accepted:
        new_text = frontmatter + accepted[0]
        (out / f'{slug}.md').write_text(new_text, encoding='utf-8')
        rel = str(path.relative_to(ROOT))
        diff = difflib.unified_diff(original.splitlines(True), new_text.splitlines(True), f'a/{rel}', f'b/{rel}')
        (out / 'proposal.patch').write_text(''.join(diff), encoding='utf-8')
        summary.update(body_change=accepted[1], next_steps=[
            'apply proposal.patch on a branch; run development trials',
            f'independent evaluator: nexus-improve.py gate --improver {IMPROVER_LABEL} on private held-out packs',
            'a human reviews and merges only on PROPOSE'])
    (out / 'proposal.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('propose')
    p.add_argument('--agent', required=True); p.add_argument('--evidence', required=True)
    p.add_argument('--out', required=True); p.add_argument('--executor', choices=('claude', 'fake'), default='claude')
    p.add_argument('--model', default='claude-opus-5-5'); p.add_argument('--operator', default='optimizer-operator')
    p.add_argument('--max-change', type=float, default=0.3)
    args = ap.parse_args(argv)
    try:
        executor = fake_optimizer if args.executor == 'fake' else claude_optimizer(args.operator)
        result = propose(args.agent, args.evidence, args.out, executor, args.model, args.max_change)
        print(json.dumps(result, indent=2))
        return 0 if result['status'] == 'PROPOSED' else 1
    except (OptimizeError, CASEPACK.PackError, ValueError, OSError, KeyError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

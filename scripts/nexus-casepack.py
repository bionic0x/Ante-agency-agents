#!/usr/bin/env python3
"""nexus-casepack.py — freeze and verify evaluation case packs (NEXUS Overdrive, Phase 1).

A case in `examples/nexus/evaluation-cases.json` is a scenario outline. A case
PACK is the frozen material a trial actually answers: brief, materials,
constraints, permitted evidence, defect rubric, output contract, and the roster
each variant uses. Its `inputs_hash` binds every trial row to exactly that
material, so a variant cannot be credited for answering a different question.

    nexus-casepack.py new      PACK_DIR --author NAME --case-ref ID [--split held_out] [--from PACK_DIR]
    nexus-casepack.py validate PACK_DIR
    nexus-casepack.py freeze   PACK_DIR --by NAME --at ISO_TIME
    nexus-casepack.py verify   PACK_DIR
    nexus-casepack.py list     ROOT_DIR

Freezing records who froze the pack and when; it does not judge the pack's
quality. Held-out packs must be authored by someone other than the improver
(strategy/NEXUS-OVERDRIVE.md); the `author` label is recorded, not authenticated.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path, PurePosixPath
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / 'examples/nexus/evaluation-cases.json'
SPLITS = ('development', 'held_out')
FIELDS = {'schema_version', 'id', 'case_ref', 'split', 'author', 'brief', 'materials', 'constraints',
          'permitted_evidence', 'rubric', 'output_contract', 'roster', 'nexus_instance', 'frozen'}
RUBRIC_KEYS = ('fatal_defects', 'factual_errors', 'constraint_violations', 'evidence_required')


class PackError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PackError(message)


PLACEHOLDER = 'TODO'


def text(value, field):
    require(isinstance(value, str) and value.strip(), f'{field}: non-empty text required')
    require(not value.strip().startswith(PLACEHOLDER), f'{field}: unfilled {PLACEHOLDER} placeholder')
    return value


def texts(value, field, nonempty=True):
    require(isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value),
            f'{field}: list of non-empty strings required')
    require(not any(v.strip().startswith(PLACEHOLDER) for v in value), f'{field}: unfilled {PLACEHOLDER} placeholder')
    require(len(value) == len(set(value)), f'{field}: duplicate entries')
    require(not nonempty or value, f'{field}: must not be empty')
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _local(pack_dir: Path, name: str, field: str) -> Path:
    """Materials live inside the pack; no absolute paths, no escaping it."""
    pure = PurePosixPath(name)
    require(not pure.is_absolute() and '..' not in pure.parts and name.strip(), f'{field}: {name!r} must be a relative path inside the pack')
    path = pack_dir / pure
    require(path.is_file(), f'{field}: {name!r} not found in pack')
    return path


def catalog():
    _, agents, runbooks = runpy.run_path(str(ROOT / 'scripts/build-catalog.py'))['collect']()
    return {a['slug'] for a in agents}


def load(pack_dir) -> tuple[Path, dict]:
    pack_dir = Path(pack_dir)
    path = pack_dir / 'pack.json'
    require(path.is_file(), f'{path}: missing pack.json')
    try:
        pack = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise PackError(f'{path}: invalid JSON: {exc}') from None
    return pack_dir, pack


def validate(pack_dir, pack, agents=None):
    require(isinstance(pack, dict), 'pack must be an object')
    unknown = set(pack) - FIELDS
    require(not unknown, f'unknown field(s) {sorted(unknown)}')
    require(pack.get('schema_version') == 1, 'schema_version must be 1')
    text(pack.get('id'), 'id')
    require(pack['id'] == Path(pack_dir).name, 'id must equal the pack directory name')
    cases = {c['id'] for c in json.loads(CASES.read_text())['cases']}
    require(pack.get('case_ref') in cases, 'case_ref must name a case in evaluation-cases.json')
    require(pack.get('split') in SPLITS, f'split must be one of {SPLITS}')
    text(pack.get('author'), 'author')
    text(pack.get('brief'), 'brief')
    for name in texts(pack.get('materials'), 'materials', nonempty=False):
        _local(pack_dir, name, 'materials')
    texts(pack.get('constraints'), 'constraints')
    texts(pack.get('permitted_evidence'), 'permitted_evidence')
    rubric = pack.get('rubric')
    require(isinstance(rubric, dict) and set(rubric) == set(RUBRIC_KEYS), f'rubric needs exactly {RUBRIC_KEYS}')
    for key in RUBRIC_KEYS:
        texts(rubric[key], f'rubric.{key}')
    contract = pack.get('output_contract')
    require(isinstance(contract, dict) and set(contract) == {'required_sections'}, 'output_contract needs required_sections')
    sections = texts(contract['required_sections'], 'output_contract.required_sections')
    require(all(s.startswith('## ') for s in sections), 'required_sections must be level-2 markdown headings')
    roster = pack.get('roster')
    require(isinstance(roster, dict) and set(roster) == {'single_agent', 'fixed_team'}, 'roster needs single_agent and fixed_team')
    agents = catalog() if agents is None else agents
    require(roster['single_agent'] in agents, 'roster.single_agent must be a catalog agent')
    for slug in texts(roster['fixed_team'], 'roster.fixed_team'):
        require(slug in agents, f'roster.fixed_team: unknown agent {slug}')
    instance_path = _local(pack_dir, text(pack.get('nexus_instance'), 'nexus_instance'), 'nexus_instance')
    engine = runpy.run_path(str(ROOT / 'scripts/nexus-instance.py'), run_name='nexus_engine_for_casepack')
    try:
        engine['validate'](json.loads(instance_path.read_text(encoding='utf-8')))
    except (ValueError, KeyError, TypeError) as exc:
        raise PackError(f'nexus_instance: {exc}') from None
    if 'frozen' in pack:
        frozen = pack['frozen']
        require(isinstance(frozen, dict) and set(frozen) == {'inputs_hash', 'frozen_by', 'frozen_at'}, 'frozen needs inputs_hash, frozen_by, frozen_at')
        text(frozen['frozen_by'], 'frozen.frozen_by')
        try:
            when = dt.datetime.fromisoformat(frozen['frozen_at'].replace('Z', '+00:00'))
        except (AttributeError, ValueError):
            raise PackError('frozen.frozen_at must be ISO-8601') from None
        require(when.tzinfo is not None, 'frozen.frozen_at needs a timezone')
    return pack


def inputs_hash(pack_dir, pack) -> str:
    """Hash of everything a variant may read: the pack minus its freeze record, plus file bytes."""
    body = {k: v for k, v in pack.items() if k != 'frozen'}
    files = {name: sha256(_local(pack_dir, name, 'materials').read_bytes()) for name in pack['materials']}
    files[pack['nexus_instance']] = sha256(_local(pack_dir, pack['nexus_instance'], 'nexus_instance').read_bytes())
    return 'sha256:' + sha256(canonical({'pack': body, 'files': files}))


def verify(pack_dir) -> dict:
    """Return the validated, frozen pack; refuse unfrozen or altered material."""
    pack_dir, pack = load(pack_dir)
    validate(pack_dir, pack)
    require('frozen' in pack, f"{pack['id']}: pack is not frozen")
    actual = inputs_hash(pack_dir, pack)
    require(actual == pack['frozen']['inputs_hash'], f"{pack['id']}: material changed after freezing ({actual})")
    return pack


def freeze(pack_dir, by, at) -> dict:
    pack_dir, pack = load(pack_dir)
    require('frozen' not in pack, f"{pack['id']}: already frozen; a changed case is a new pack id")
    validate(pack_dir, pack)
    text(by, 'frozen_by')
    pack['frozen'] = {'inputs_hash': inputs_hash(pack_dir, pack), 'frozen_by': by, 'frozen_at': at}
    validate(pack_dir, pack)
    (pack_dir / 'pack.json').write_text(json.dumps(pack, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return pack


def scaffold(pack_dir, author, case_ref, split='held_out', template=None) -> dict:
    """Start a new pack. Every field the author must write is a TODO that validation refuses.

    The NEXUS instance is copied from a template pack as a structural starting point;
    its tasks, asserts and claims still have to be rewritten for the new case.
    """
    pack_dir = Path(pack_dir)
    require(not pack_dir.exists(), f'{pack_dir}: already exists; a new case needs a new directory')
    require(split in SPLITS, f'split must be one of {SPLITS}')
    text(author, 'author')
    template = Path(template) if template else ROOT / 'examples/nexus/casepacks/level-inversion-northwind'
    _, source = load(template)
    pack_dir.mkdir(parents=True)
    (pack_dir / 'instance.json').write_bytes((template / source['nexus_instance']).read_bytes())
    todo = lambda what: f'{PLACEHOLDER}: {what}'
    pack = {
        'schema_version': 1, 'id': pack_dir.name, 'case_ref': case_ref, 'split': split, 'author': author,
        'brief': todo('the decision the deliverable must support, for whom, and by when'),
        'materials': [],
        'constraints': [todo('a limit the answer must respect')],
        'permitted_evidence': [todo('what the answer may rely on')],
        'rubric': {
            'fatal_defects': [todo('an observable error that would make the deliverable unusable')],
            'factual_errors': [todo('a claim that contradicts the materials')],
            'constraint_violations': [todo('how a broken constraint shows in the output')],
            'evidence_required': [todo('a point the answer must ground in named evidence')],
        },
        'output_contract': {'required_sections': ['## Decision', '## Evidence', '## Limits and what would change this']},
        'roster': source['roster'],
        'nexus_instance': 'instance.json',
    }
    (pack_dir / 'pack.json').write_text(json.dumps(pack, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return pack


PUBLIC_PACKS = ROOT / 'examples/nexus/casepacks'


def published_materials() -> dict[str, str]:
    """sha256 of every material file in the public example packs -> 'pack/file'."""
    seen = {}
    for pack_json in sorted(PUBLIC_PACKS.glob('*/pack.json')):
        try:
            pack_dir, pack = load(pack_json.parent)
        except PackError:
            continue
        for name in pack.get('materials', []):
            path = pack_dir / name
            if path.is_file():
                seen.setdefault(sha256(path.read_bytes()), f"{pack_dir.name}/{name}")
    return seen


def exposure(root, pack_dir=None, pack=None, published=None) -> list[str]:
    """Reasons evidence under `root` (or one pack in it) cannot count as unseen.

    Two mechanical checks, neither a proof of secrecy: the root must lie outside
    this public checkout (symlinks resolved), and a pack must not reuse a material
    file published in it byte for byte. A reworded copy passes both; access
    control and prior exposure still need an evaluator's attestation.
    """
    reasons = []
    resolved, checkout = Path(root).resolve(), ROOT.resolve()
    if resolved == checkout or checkout in resolved.parents:
        reasons.append('held-out packs under the public repository checkout are exposed; use a separate '
                       'evaluator-controlled, access-restricted corpus (published sample packs cannot '
                       'establish a blind result)')
    if pack_dir is not None and pack is not None:
        published = published_materials() if published is None else published
        for name in pack.get('materials', []):
            path = Path(pack_dir) / name
            if path.is_file() and sha256(path.read_bytes()) in published:
                reasons.append(f"{pack['id']}: material {name!r} is published in this repository "
                               f"({published[sha256(path.read_bytes())]}); a copy of a public case is not unseen")
    return reasons


def listing(root) -> list[dict]:
    rows = []
    for pack_json in sorted(Path(root).glob('*/pack.json')):
        _, pack = load(pack_json.parent)
        rows.append({'id': pack.get('id'), 'case_ref': pack.get('case_ref'), 'split': pack.get('split'),
                     'author': pack.get('author'), 'frozen': 'frozen' in pack})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    for name in ('validate', 'verify'):
        sub.add_parser(name).add_argument('pack')
    f = sub.add_parser('freeze'); f.add_argument('pack'); f.add_argument('--by', required=True); f.add_argument('--at', required=True)
    sub.add_parser('list').add_argument('root')
    n = sub.add_parser('new'); n.add_argument('pack'); n.add_argument('--author', required=True)
    n.add_argument('--case-ref', required=True); n.add_argument('--split', default='held_out', choices=SPLITS)
    n.add_argument('--from', dest='template')
    args = ap.parse_args(argv)
    try:
        if args.command == 'validate':
            pack_dir, pack = load(args.pack); validate(pack_dir, pack); result = {'status': 'VALID', 'id': pack['id']}
        elif args.command == 'verify':
            pack = verify(args.pack); result = {'status': 'FROZEN_OK', 'id': pack['id'], 'inputs_hash': pack['frozen']['inputs_hash']}
        elif args.command == 'freeze':
            pack = freeze(args.pack, args.by, args.at); result = {'status': 'FROZEN', 'id': pack['id'], 'inputs_hash': pack['frozen']['inputs_hash']}
        elif args.command == 'new':
            pack = scaffold(args.pack, args.author, args.case_ref, args.split, args.template)
            result = {'status': 'SCAFFOLDED', 'id': pack['id'],
                      'next': 'replace every TODO, add materials, rewrite instance.json, then validate and freeze'}
        else:
            result = listing(args.root)
        print(json.dumps(result, indent=2))
        return 0
    except (PackError, OSError) as exc:
        print(f'ERROR {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

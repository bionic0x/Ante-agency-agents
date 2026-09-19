#!/usr/bin/env python3
"""check-security-engagement.py — enforce the engagement contract for security agents.

The repository already treats a `tools:` declaration as a security-relevant claim
that CI validates against a closed registry (scripts/agent-tools.json). It applied
that discipline to *capabilities* and stopped there. An agent that simulates an
adversary is at least as sensitive as one that declares a write tool, yet the
rules of engagement lived only as uneven prose: one offensive agent spelled them
out fourteen times, another not at all.

This check closes that gap. Every agent under the security division must declare
an `engagement:` class from scripts/security-engagement.json, and each class
carries required policy language that must appear in the prose body:

  passive-analysis     reads and reports; no obligation beyond honest classification
  active-defensive     acts on the operator's own assets under change control, and
                       states that the declaration is not authorization
  authorized-offensive requires prior written authorization, a defined scope, a
                       stop/abort condition, a no-destruction limit, and the same
                       not-authorization statement

The class is a claim; this check validates vocabulary and required phrases, not
semantic consistency, authorization signatures or host behavior. A declaration
is never itself authorization — the operator's mandate, scope and law decide that.

The check is intentionally conservative about MISDECLARATION: an agent whose body
reads as offensive (exploitation, intrusion) while declaring a passive class is
flagged for human review. The advisory is not a complete classifier and does not
prevent a misleading passive declaration from passing CI.

Usage:
  check-security-engagement.py                 # scan the whole security division
  check-security-engagement.py FILE...         # check specific files
  check-security-engagement.py --inventory     # print the per-agent classification
"""
import argparse, json, re, sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / 'scripts' / 'security-engagement.json'

# Body phrases that describe carrying out an intrusion against a target. Matched
# case-insensitively. Their presence in an agent that declared a non-offensive
# class warrants review; it does not establish a misdeclaration or capability.
# First-PERSON offensive constructions: performing an intrusion, not naming a
# technique a defender studies. "adversaries exfiltrate data" is subject matter;
# "I will exploit" / "we gain a foothold" / "you run the exploit" describes action.
# The distinction matters — a threat-intel analyst that could not say "C2" or
# "lateral movement" could not do its job, so nouns are never markers here.
OFFENSIVE_RE = re.compile(
    r'\b(?:I|we|you)\s+(?:will\s+)?(?:'
    r'(?:exploit|compromise|breach|intrude|pop|own)\b|'
    r'gain\s+(?:a\s+)?foothold\b|'
    r'(?:run|launch|execute|deploy|fire)\s+(?:the\s+)?(?:exploit|payload|attack)\b|'
    r'establish\s+(?:persistence|c2|command[\s-]and[\s-]control)\b)', re.IGNORECASE)


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in mapping:
            raise ValueError('frontmatter keys must be unique strings')
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def split_profile(text):
    lines = text.splitlines()
    if not lines or lines[0] != '---':
        raise ValueError('missing opening frontmatter fence')
    try:
        end = lines.index('---', 1)
    except ValueError:
        raise ValueError('missing closing frontmatter fence') from None
    try:
        meta = yaml.load('\n'.join(lines[1:end]), Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise ValueError(f'invalid YAML frontmatter: {exc}') from exc
    if not isinstance(meta, dict):
        raise ValueError('frontmatter is not a mapping')
    return meta, '\n'.join(lines[end + 1:])


def frontmatter(text):
    return split_profile(text)[0]


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate registry key: {key}')
        result[key] = value
    return result


def load_registry(path=REGISTRY):
    reg = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique_json)
    if not isinstance(reg, dict) or type(reg.get('schema_version')) is not int or reg['schema_version'] != 1:
        raise ValueError('security-engagement.json schema_version must be 1')
    classes = reg.get('classes')
    if classes != ['passive-analysis', 'active-defensive', 'authorized-offensive']:
        raise ValueError('classes must list exactly the three registered classes in order')
    definitions, phrases = reg.get('definitions'), reg.get('required_language')
    if not isinstance(definitions, dict) or set(definitions) != set(classes):
        raise ValueError('every class needs exactly one definition and vice versa')
    if not isinstance(phrases, dict) or not phrases:
        raise ValueError('required_language must be a non-empty mapping')
    minimum = {'passive-analysis': set(),
               'active-defensive': {'own_assets', 'change_control', 'not_authorization'},
               'authorized-offensive': {'written_authorization', 'scope_boundary', 'stop_condition',
                                        'no_destruction', 'not_authorization'}}
    for name, spec in definitions.items():
        if not isinstance(spec, dict):
            raise ValueError(f'class {name!r} definition must be an object')
        for key in ('interacts_with_live_targets', 'acts_only_on_own_assets',
                    'requires_rules_of_engagement', 'requires_authority_reference'):
            if type(spec.get(key)) is not bool:
                raise ValueError(f'class {name!r} field {key!r} must be a boolean')
        if not isinstance(spec.get('summary'), str) or not spec['summary'].strip():
            raise ValueError(f'class {name!r} summary must be non-empty text')
        required = spec.get('required_language')
        if not isinstance(required, list) or any(not isinstance(t, str) for t in required):
            raise ValueError(f'class {name!r} required_language must be a list of tokens')
        if len(required) != len(set(required)) or not minimum[name] <= set(required):
            raise ValueError(f'class {name!r} has duplicate or missing mandatory language tokens')
        for token in required:
            if token not in phrases:
                raise ValueError(f'class {name!r} requires undefined language token {token!r}')
    for token, spec in phrases.items():
        if not isinstance(token, str) or not token.strip() or not isinstance(spec, dict):
            raise ValueError('language definitions require non-empty token names and objects')
        options = spec.get('any_of')
        if not isinstance(options, list) or not options or any(not isinstance(p, str) or not p.strip() for p in options):
            raise ValueError(f'language token {token!r} needs non-empty phrase strings')
        if len(options) != len(set(options)) or not isinstance(spec.get('why'), str) or not spec['why'].strip():
            raise ValueError(f'language token {token!r} needs distinct phrases and a non-empty why')
    return reg


def security_agents(root=ROOT):
    root = Path(root).resolve()
    divisions = json.loads((root / 'divisions.json').read_text(encoding='utf-8'))
    divisions = divisions.get('divisions', divisions)
    if 'security' not in divisions:
        raise ValueError("divisions.json has no 'security' division")
    paths = sorted(p for p in (root / 'security').rglob('*.md') if p.name != 'README.md')
    if not paths:
        raise ValueError('security division contains no agent files')
    return paths


def phrase_present(body_lower, token, registry):
    return any(re.search(r'(?<!\w)' + re.escape(p.lower()) + r'(?!\w)', body_lower)
               for p in registry['required_language'][token]['any_of'])


def policy_prose(body):
    body = re.sub(r'<!--.*?(?:-->|\Z)', '', body, flags=re.S)
    lines, fence = [], None
    for line in body.splitlines():
        if fence:
            if re.fullmatch(r' {0,3}' + re.escape(fence[0]) +
                            '{' + str(len(fence)) + r',}\s*', line):
                fence = None
            continue
        opening = re.match(r' {0,3}(`{3,}|~{3,})', line)
        if opening:
            fence = opening.group(1)
        else:
            lines.append(line)
    return '\n'.join(lines)


def check_file(path, registry, root=ROOT):
    findings = []
    root, path = Path(root).resolve(), Path(path).resolve()
    try:
        rel = path.relative_to(root)
        text = path.read_text(encoding='utf-8')
        meta, body = split_profile(text)
    except (OSError, ValueError) as exc:
        return [f'{path}: {exc}'], None, []

    declared = meta.get('engagement')
    if declared is None:
        return [f'{rel}: missing `engagement:` field; security agents must declare a class '
                f"from {registry['classes']}"], None, []
    if not isinstance(declared, str) or declared not in registry['classes']:
        return [f'{rel}: unknown engagement class {declared!r}; registered classes are '
                f"{registry['classes']}"], None, []

    spec = registry['definitions'][declared]
    # Examples and HTML comments cannot satisfy required policy prose.
    body_lower = policy_prose(body).lower()

    for token in spec['required_language']:
        if not phrase_present(body_lower, token, registry):
            findings.append(f'{rel}: declares {declared!r} but the body does not '
                            f"{registry['required_language'][token]['why']} "
                            f'(none of the registered phrases for {token!r} are present)')

    # Misdeclaration is an ADVISORY, never a build failure: separating "performs an
    # intrusion" from "analyzes one" cannot be done reliably by lexical scan, and a
    # heuristic that misfires on the division's analytical agents must not gate CI.
    advisories = []
    if declared != 'authorized-offensive':
        hits = sorted({m.group(0).lower() for m in OFFENSIVE_RE.finditer(body)})
        if hits:
            advisories.append(f'{rel}: declares {declared!r} but the body uses first-person '
                              f'offensive phrasing ({", ".join(hits[:4])}); confirm the class is right')
    return findings, declared, advisories


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='*')
    ap.add_argument('--inventory', action='store_true')
    args = ap.parse_args()
    try:
        registry = load_registry()
        paths = [Path(f).resolve() for f in args.files] if args.files else security_agents()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'ERROR registry: {exc}', file=sys.stderr)
        return 2

    all_findings, all_advisories, inventory = [], [], {}
    failed_agents = 0
    for path in paths:
        findings, declared, advisories = check_file(path, registry)
        failed_agents += bool(findings)
        all_findings += findings
        all_advisories += advisories
        inventory[str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)] = declared

    if args.inventory:
        by_class = {}
        for rel, cls in sorted(inventory.items()):
            by_class.setdefault(cls or 'UNDECLARED', []).append(rel)
        for cls in list(registry['classes']) + ['UNDECLARED']:
            if cls in by_class:
                print(f'\n{cls} ({len(by_class[cls])}):')
                for rel in by_class[cls]:
                    print(f'  {rel}')

    for advisory in all_advisories:
        print(f'  ADVISORY {advisory}')
    for finding in all_findings:
        print(f'  FAIL {finding}')
    total = len(inventory)
    print(f'\nResults: {total - failed_agents}/{total} security agents pass the language checks for their '
          f'declared engagement class ({len(all_findings)} findings)')
    return 1 if all_findings else 0


if __name__ == '__main__':
    sys.exit(main())

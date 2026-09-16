#!/usr/bin/env python3
"""Keep machine vocabulary and critical human handoff templates aligned."""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    vocabulary = json.loads((ROOT / 'strategy/contracts.json').read_text())
    expected = vocabulary['epistemic_states']
    register = (ROOT / 'strategy/templates/claim-register.yaml').read_text()
    match = re.search(r'allowed_status:\n((?:  - [A-Z_]+\n)+)', register)
    actual = re.findall(r'  - ([A-Z_]+)', match[1]) if match else []
    handoff = (ROOT / 'strategy/coordination/handoff-templates.md').read_text()
    rows = [line for line in handoff.splitlines() if line.startswith('| [claim] |')]
    errors = []
    if actual != expected:
        errors.append('claim-register allowed_status differs from strategy/contracts.json')
    if len(rows) != 1 or rows[0].split('|')[2].strip() != ' / '.join(expected):
        errors.append('standard handoff loses canonical epistemic states')
    if errors:
        print('\n'.join('ERROR ' + e for e in errors))
        return 1
    print('PASSED: claim register and standard handoff preserve all epistemic states')
    return 0

if __name__ == '__main__':
    sys.exit(main())

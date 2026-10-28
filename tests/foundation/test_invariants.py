"""Invariants without a natural home in another test file.

Invariant 6 (no new network by default) and invariant 9 (Marco XVII stays in
quarantine). foundation/INVARIANTS.md maps all ten invariants to their tests.
"""
import ast
import contextlib
import io as stdio
import json
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ante import cli  # noqa: E402
from test_strategy import Chain  # noqa: E402

NETWORK_MODULES = {'socket', 'ssl', 'urllib', 'http', 'requests', 'httpx', 'aiohttp', 'ftplib', 'smtplib',
                   'telnetlib', 'xmlrpc', 'websocket', 'websockets'}
# Modules allowed to start processes, and why.
PROCESS_USERS = {
    'ante/nexus/anthropic.py': 'pre-existing Claude Code adapter, moved mechanically; runs only when invoked',
    'ante/develop/policy.py': 'git show / git apply --numstat on the local repository',
    'ante/develop/commands.py': 'local git worktrees and tests; push and gh only under pr --execute',
    'ante/constructs/frozen.py': 'git show of the frozen registry at a base revision',
}


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {alias.name.split('.')[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split('.')[0])
    return found


class NoNewNetwork(unittest.TestCase):
    def test_no_module_imports_a_network_library(self):
        offenders = {str(p.relative_to(ROOT)): sorted(imports(p) & NETWORK_MODULES)
                     for p in (ROOT / 'ante').rglob('*.py') if imports(p) & NETWORK_MODULES}
        self.assertEqual({}, offenders)

    def test_only_declared_modules_start_processes(self):
        users = {str(p.relative_to(ROOT)) for p in (ROOT / 'ante').rglob('*.py')
                 if {'subprocess', 'os'} & imports(p) and 'subprocess' in p.read_text(encoding='utf-8')}
        self.assertEqual(set(PROCESS_USERS), users)

    def test_the_whole_chain_learning_and_deck_run_with_sockets_disabled(self):
        def refuse(*args, **kwargs):
            raise AssertionError('network access attempted')

        chain = Chain()
        self.addCleanup(chain.close)
        with mock.patch.object(socket.socket, 'connect', refuse), \
                mock.patch.object(socket, 'create_connection', refuse):
            chain.build()
            ledger = str(chain.dir / 'ledger.jsonl')
            out = stdio.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(stdio.StringIO()):
                self.assertEqual(0, cli.main(['learn', 'record', str(chain.out / 'decide.json'), '--ledger', ledger,
                                              '--synthetic', '--at', '2026-10-28T15:00:00Z']))
                self.assertEqual(0, cli.main(['learn', 'calibrate', '--ledger', ledger,
                                              '--at', '2026-10-29T00:00:00Z']))
                self.assertEqual(0, cli.main(['deck', '--artifacts', str(chain.out), '--plain']))
                self.assertEqual(0, cli.main(['ice', 'layers']))

    def test_a_dry_run_pull_request_starts_no_process(self):
        from ante.develop import commands as develop
        with mock.patch.object(develop, 'pr_plan', return_value={'branch': 'b', 'commands': [[], []], 'body': ''}), \
                mock.patch.object(subprocess, 'run', side_effect=AssertionError('process started')):
            result = develop.pr('x', 'unused', 'main', '2026-10-28T12:00:00Z', execute=False)
        self.assertFalse(result['executed'])

    def test_model_drafting_is_opt_in(self):
        from ante.strategy import draft
        path = Path(tempfile.mkdtemp()) / 'frame.json'
        path.write_text(json.dumps({'at': '2026-10-28T09:00:00Z', 'claims': []}))
        with mock.patch.object(draft, 'ADAPTERS', {}), mock.patch.object(subprocess, 'run',
                                                                          side_effect=AssertionError('model called')):
            with contextlib.redirect_stdout(stdio.StringIO()), contextlib.redirect_stderr(stdio.StringIO()):
                cli.main(['frame', str(path)])   # fails validation, but never reaches a model


class QuarantineOfChapterXVII(unittest.TestCase):
    def test_doctrine_tables_hold_seven_tests_and_fourteen_pathologies_only(self):
        tables = json.loads((ROOT / 'foundation/proposals/contracts-v2.json').read_text())
        self.assertEqual(7, len(tables['coherence_tests']))
        self.assertEqual(14, len(tables['pathologies']))
        self.assertNotIn('XVII', json.dumps(tables['coherence_tests']) + json.dumps(tables['pathologies']))

    def test_no_check_cites_chapter_xvii(self):
        cited = [str(p.relative_to(ROOT)) for p in (ROOT / 'ante').rglob('*.py')
                 if 'XVII' in p.read_text(encoding='utf-8')]
        self.assertEqual([], cited)


if __name__ == '__main__':
    unittest.main()

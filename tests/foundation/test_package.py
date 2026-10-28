"""The extracted package imports normally and the shims stay shims."""
import importlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ante import registry  # noqa: E402
from ante.paths import ROOT as PACKAGE_ROOT  # noqa: E402

MOVES = json.loads((ROOT / 'foundation/tools/extractions.json').read_text())['moves']


class ExtractedModules(unittest.TestCase):
    def test_every_moved_module_imports_as_a_package_module(self):
        for module in MOVES.values():
            loaded = importlib.import_module(module)
            self.assertEqual(ROOT, loaded.ROOT if hasattr(loaded, 'ROOT') else PACKAGE_ROOT, module)

    def test_moves_are_mechanical(self):
        result = subprocess.run([sys.executable, str(ROOT / 'foundation/tools/extraction.py'), 'verify'],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


class Registry(unittest.TestCase):
    def test_registry_reads_the_self_contained_scripts(self):
        runbooks = registry.runbooks()
        self.assertIn('strategic-decision', runbooks)
        slugs = registry.agent_slugs()
        for runbook in runbooks.values():
            for group in runbook['roster']:
                for slug in group['agents']:
                    self.assertIn(slug, slugs, f'{runbook["slug"]} references {slug}')
        self.assertEqual([name for name, _ in registry.tools()][0], 'claude-code')


if __name__ == '__main__':
    unittest.main()

"""The synthetic foundation example rebuilds byte for byte."""
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'examples/foundation/lab-consortium'


class Example(unittest.TestCase):
    def test_run_reproduces_the_committed_chain_and_ledger(self):
        work = Path(tempfile.mkdtemp(prefix='ante-example-'))
        self.addCleanup(shutil.rmtree, work, True)
        env = dict(os.environ, PATH=f'{Path(sys.executable).parent}{os.pathsep}{os.environ.get("PATH", "")}')
        proc = subprocess.run(['bash', str(EXAMPLE / 'run.sh'), str(work / 'artifacts'), str(work / 'learning')],
                              capture_output=True, text=True, env=env, timeout=300)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn('complete: True', proc.stdout)
        self.assertIn('INSUFFICIENT_SAMPLE 0', proc.stdout)
        for name in ('artifacts', 'learning'):
            comparison = filecmp.dircmp(EXAMPLE / name, work / name)
            self.assertEqual(([], [], []), (comparison.diff_files, comparison.left_only, comparison.right_only), name)
            for common in comparison.common_files:
                self.assertTrue(filecmp.cmp(EXAMPLE / name / common, work / name / common, shallow=False), common)


if __name__ == '__main__':
    unittest.main()

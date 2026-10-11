#!/usr/bin/env python3
"""Regression tests for changed-agent path discovery."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "list-changed-agent-files.py"


class ChangedAgentDiscoveryTests(unittest.TestCase):
    def run_filter(self, paths: list[str]) -> list[str]:
        result = subprocess.run(
            [sys.executable, str(HELPER), "--divisions", str(ROOT / "divisions.json")],
            input="\n".join(paths) + "\n",
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.splitlines()

    def test_direct_and_nested_agents_are_detected(self):
        self.assertEqual(
            [
                "gis/meteo-direct.md",
                "gis/subdir/meteo-nested.md",
                "specialized/legal-direct.md",
            ],
            self.run_filter(
                [
                    "gis/meteo-direct.md",
                    "gis/subdir/meteo-nested.md",
                    "specialized/legal-direct.md",
                ]
            ),
        )

    def test_non_agents_are_excluded(self):
        self.assertEqual(
            [],
            self.run_filter(
                [
                    "gis/README.md",
                    "gis/notes.txt",
                    "strategy/scenario.md",
                    "scripts/lint-agents.sh",
                    "not-a-division/example.md",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()

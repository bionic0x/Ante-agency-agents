#!/usr/bin/env python3
"""Regression tests for granular integration-state synchronization.

Uses a tiny isolated repository fixture so behavior is tested without mutating
this checkout or paying the 487-agent full-corpus cost. The existing conversion
suite remains responsible for byte identity across the real roster and formats.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

AGENT_TEMPLATE = """---
name: {name}
description: Fixture agent for incremental conversion tests
color: blue
---
## Identity

{name} fixture identity.

## Core Mission

Exercise deterministic converter behavior with enough body content to be real.

## Critical Rules

Preserve exact output ownership and never mutate unrelated generated files.
"""


def run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(args),
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"command failed ({completed.returncode}): {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def make_fixture(parent: Path) -> Path:
    repo = parent / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    for name in ("convert.sh", "lib.sh", "registry.py", "integration-state.py"):
        shutil.copy2(HERE / name, scripts / name)

    (repo / "testing").mkdir()
    (repo / "testing" / "testing-alpha.md").write_text(
        AGENT_TEMPLATE.format(name="Alpha Agent"), encoding="utf-8"
    )
    (repo / "testing" / "testing-beta.md").write_text(
        AGENT_TEMPLATE.format(name="Beta Agent"), encoding="utf-8"
    )

    (repo / "divisions.json").write_text(
        json.dumps({"divisions": {"testing": {"label": "Testing", "icon": "FlaskConical", "color": "#000000"}}}),
        encoding="utf-8",
    )
    (repo / "tools.json").write_text(
        json.dumps(
            {
                "tools": {
                    "codex": {"format": "codex-toml", "installKind": "per-agent"},
                    "aider": {"format": "aider-conventions", "installKind": "roster"},
                }
            }
        ),
        encoding="utf-8",
    )
    return repo


class IncrementalConversionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="agency-incremental-test-")
        self.repo = make_fixture(Path(self.tmp.name))
        self.state = self.repo / "scripts" / "integration-state.py"
        self.convert = self.repo / "scripts" / "convert.sh"
        self.alpha = self.repo / "testing" / "testing-alpha.md"
        self.beta = self.repo / "testing" / "testing-beta.md"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def sync(self, tool: str) -> subprocess.CompletedProcess[str]:
        return run(self.repo, "python3", str(self.state), "sync", tool)

    def check_state(self, tool: str) -> subprocess.CompletedProcess[str]:
        return run(self.repo, "python3", str(self.state), "check", tool, check=False)

    def state_file(self, tool: str) -> Path:
        return self.repo / ".cache" / "integration-state" / f"{tool}.json"

    def test_check_is_read_only_and_one_source_sync_preserves_unrelated_output(self) -> None:
        first = self.sync("codex")
        self.assertIn("full rebuild", first.stdout)
        state = json.loads(self.state_file("codex").read_text(encoding="utf-8"))
        self.assertEqual(2, state["version"])
        self.assertEqual(2, len(state["sources"]))

        alpha_out = self.repo / "integrations" / "codex" / "agents" / "alpha-agent.toml"
        beta_out = self.repo / "integrations" / "codex" / "agents" / "beta-agent.toml"
        self.assertTrue(alpha_out.is_file())
        self.assertTrue(beta_out.is_file())

        beta_before = beta_out.read_bytes()
        beta_mtime = beta_out.stat().st_mtime_ns
        state_before = self.state_file("codex").read_bytes()
        alpha_before = alpha_out.read_bytes()

        with self.alpha.open("a", encoding="utf-8") as handle:
            handle.write("\nIncremental marker.\n")

        checked = self.check_state("codex")
        self.assertNotEqual(0, checked.returncode)
        self.assertEqual(state_before, self.state_file("codex").read_bytes())
        self.assertEqual(alpha_before, alpha_out.read_bytes())
        self.assertEqual(beta_before, beta_out.read_bytes())

        second = self.sync("codex")
        self.assertIn("incremental rebuild (1 changed/new, 0 removed)", second.stdout)
        self.assertIn(b"Incremental marker", alpha_out.read_bytes())
        self.assertEqual(beta_before, beta_out.read_bytes())
        self.assertEqual(beta_mtime, beta_out.stat().st_mtime_ns)
        self.assertEqual(0, self.check_state("codex").returncode)

    def test_rename_delete_corruption_and_orphan_pruning(self) -> None:
        self.sync("codex")
        old_output = self.repo / "integrations" / "codex" / "agents" / "alpha-agent.toml"

        text = self.alpha.read_text(encoding="utf-8").replace("name: Alpha Agent", "name: Renamed Alpha Agent", 1)
        self.alpha.write_text(text, encoding="utf-8")
        renamed = self.sync("codex")
        new_output = self.repo / "integrations" / "codex" / "agents" / "renamed-alpha-agent.toml"
        self.assertIn("incremental rebuild (1 changed/new, 0 removed)", renamed.stdout)
        self.assertFalse(old_output.exists())
        self.assertTrue(new_output.is_file())

        self.alpha.unlink()
        deleted = self.sync("codex")
        self.assertIn("0 changed/new, 1 removed", deleted.stdout)
        self.assertFalse(new_output.exists())

        beta_out = self.repo / "integrations" / "codex" / "agents" / "beta-agent.toml"
        expected = beta_out.read_bytes()
        beta_out.write_text("corrupted\n", encoding="utf-8")
        repaired = self.sync("codex")
        self.assertIn("incremental rebuild (1 changed/new, 0 removed)", repaired.stdout)
        self.assertEqual(expected, beta_out.read_bytes())

        orphan = self.repo / "integrations" / "codex" / "agents" / "orphan.toml"
        orphan.write_text("orphan\n", encoding="utf-8")
        pruned = self.sync("codex")
        self.assertIn("incremental rebuild (0 changed/new, 0 removed)", pruned.stdout)
        self.assertFalse(orphan.exists())
        self.assertEqual(0, self.check_state("codex").returncode)

    def test_renderer_change_and_roster_tool_fall_back_to_full_rebuild(self) -> None:
        self.sync("codex")
        with (self.repo / "scripts" / "lib.sh").open("a", encoding="utf-8") as handle:
            handle.write("\n# fixture renderer version change\n")
        renderer_changed = self.sync("codex")
        self.assertIn("full rebuild", renderer_changed.stdout)

        first_aider = self.sync("aider")
        self.assertIn("full rebuild", first_aider.stdout)
        with self.beta.open("a", encoding="utf-8") as handle:
            handle.write("\nRoster change.\n")
        second_aider = self.sync("aider")
        self.assertIn("full rebuild", second_aider.stdout)
        self.assertIn("Roster change.", (self.repo / "integrations" / "aider" / "CONVENTIONS.md").read_text(encoding="utf-8"))

    def test_single_source_mode_rejects_aggregate_and_unregistered_sources(self) -> None:
        rejected = run(
            self.repo,
            "bash",
            str(self.convert),
            "--tool",
            "aider",
            "--source",
            "testing/testing-alpha.md",
            check=False,
        )
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("only valid for per-agent", rejected.stderr)

        docs = self.repo / "docs"
        docs.mkdir()
        outside = docs / "outside.md"
        outside.write_text(AGENT_TEMPLATE.format(name="Outside Agent"), encoding="utf-8")
        rejected = run(
            self.repo,
            "bash",
            str(self.convert),
            "--tool",
            "codex",
            "--source",
            "docs/outside.md",
            check=False,
        )
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("not inside a registered division", rejected.stderr)


if __name__ == "__main__":
    unittest.main()

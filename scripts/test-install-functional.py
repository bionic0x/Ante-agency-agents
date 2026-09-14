#!/usr/bin/env python3
"""Exercise all adapter installs and failure modes in a small isolated checkout."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FunctionalInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="agency-functional-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "repo with spaces"
        self.repo.mkdir()
        shutil.copytree(ROOT / "scripts", self.repo / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(ROOT / "tools.json", self.repo / "tools.json")
        (self.repo / "divisions.json").write_text(json.dumps({"divisions": {"engineering": {"label": "Engineering"}}}))
        (self.repo / "engineering").mkdir()
        for slug, name in [("engineering-alpha", "Alpha Agent"), ("engineering-beta", "Beta Agent")]:
            (self.repo / "engineering" / (slug + ".md")).write_text(
                f"---\nname: {name}\ndescription: Tests installation behavior.\ncolor: blue\n---\n"
                f"# {name}\n\n## Identity\nFixture persona.\n\n---\n\n## Core Mission\nKeep the body intact.\n"
                "\n## Critical Rules\nPreserve the user's scope.\n"
            )
        (self.repo / "strategy").mkdir()
        (self.repo / "strategy/runbooks.json").write_text(json.dumps({"runbooks": [{
            "slug": "fixture", "title": "Fixture", "doc": "strategy/scenario.md",
            "required_artifacts": ["strategy/evidence.md"],
            "roster": [{"agents": ["engineering-alpha", "engineering-beta"]}],
        }]}))
        (self.repo / "strategy/scenario.md").write_text("# Fixture scenario\n")
        (self.repo / "strategy/evidence.md").write_text("# Evidence pending\n")
        (self.repo / "integrations").mkdir()
        self.env = os.environ.copy()
        # Only child processes receive isolated config paths; the real user is untouched.
        self.env["HOME"] = str(self.base / "user")
        for key in ["CLAUDE_CONFIG_DIR", "COPILOT_AGENT_DIR", "CURSOR_RULES_DIR", "GEMINI_AGENTS_DIR",
                    "OPENCODE_AGENTS_DIR", "OPENCLAW_DIR", "QWEN_AGENTS_DIR", "ZCODE_AGENTS_DIR",
                    "CODEX_AGENTS_DIR", "OSAURUS_SKILLS_DIR", "HERMES_HOME", "HERMES_PLUGIN_DIR",
                    "VIBE_HOME", "AGENCY_INSTALL_WORKER"]:
            self.env.pop(key, None)

    def command(self, script, *args, success=True):
        result = subprocess.run(["bash", str(self.repo / "scripts" / script), *args],
                                cwd=self.repo, env=self.env, capture_output=True, text=True)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode == 0, success, output)
        return output

    def install(self, *args, **kwargs):
        return self.command("install.sh", "--no-interactive", *args, **kwargs)

    def test_all_sixteen_tools_install_files(self):
        expected = {
            "claude-code": "engineering-alpha.md", "copilot": "engineering-alpha.md",
            "antigravity": "agency-alpha-agent/SKILL.md", "osaurus": "agency-alpha-agent/SKILL.md",
            "gemini-cli": "alpha-agent.md", "opencode": "alpha-agent.md", "qwen": "alpha-agent.md",
            "zcode": "alpha-agent.md", "cursor": "alpha-agent.mdc", "codex": "alpha-agent.toml",
            "kimi": "alpha-agent/agent.yaml", "openclaw": "alpha-agent/SOUL.md",
            "vibe": "agents/alpha-agent.toml", "hermes": "agency-agents-router/plugin.yaml",
            "aider": "CONVENTIONS.md", "windsurf": ".windsurfrules",
        }
        self.assertEqual(set(expected), set(json.loads((ROOT / "tools.json").read_text())["tools"]))
        for tool, relative in expected.items():
            with self.subTest(tool=tool):
                destination = self.base / "outputs" / tool
                self.install("--tool", tool, "--path", str(destination))
                self.assertTrue((destination / relative).is_file(), f"{tool}: {relative}")
        self.assertFalse((self.base / "user/.copilot/agents").exists())
        self.assertFalse((self.repo / "CONVENTIONS.md").exists())
        self.assertFalse((self.repo / ".windsurfrules").exists())

    def test_parallel_preserves_arguments_and_both_outputs(self):
        destination = self.base / "My [Agents] 'quoted'" / "dest dir"
        roster = self.base / "my agents list.txt"
        roster.write_text("engineering-alpha\n")
        self.install("--tool", "claude-code,codex", "--agents-file", str(roster),
                     "--path", str(destination), "--parallel", "--jobs", "2")
        self.assertEqual({p.name for p in destination.iterdir()}, {"engineering-alpha.md", "alpha-agent.toml"})

    def test_worker_failure_is_nonzero_and_explained(self):
        output = self.install("--tool", "claude-code,codex", "--agent", "engineering-alpha",
                              "--path", str(self.base / "failed"), "--parallel", "--jobs", "2",
                              "--no-convert", success=False)
        self.assertIn("missing", output)
        self.assertNotIn("Done!", output)

    def test_missing_selected_output_fails_without_conversion(self):
        self.command("convert.sh", "--tool", "codex")
        (self.repo / "integrations/codex/agents/alpha-agent.toml").unlink()
        output = self.install("--tool", "codex", "--agent", "engineering-alpha", "--no-convert",
                              "--path", str(self.base / "partial"), success=False)
        self.assertIn("installed 0 of 1", output)

    def test_changed_source_and_deleted_output_are_regenerated(self):
        destination = self.base / "fresh"
        args = ("--tool", "codex", "--agent", "engineering-alpha", "--path", str(destination))
        self.install(*args)
        agent = self.repo / "engineering/engineering-alpha.md"
        agent.write_text(agent.read_text() + "\nFRESH_MARKER\n")
        self.install(*args)
        self.assertIn("FRESH_MARKER", (destination / "alpha-agent.toml").read_text())
        generated = self.repo / "integrations/codex/agents/alpha-agent.toml"
        generated.unlink()
        self.install(*args)
        self.assertTrue(generated.is_file())

    def test_runbook_and_canonical_ids_resolve(self):
        destination = self.base / "runbook"
        self.install("--tool", "claude-code", "--runbook", "fixture", "--path", str(destination))
        self.assertEqual(len(list(destination.glob("*.md"))), 2)
        (self.repo / "strategy/evidence.md").unlink()
        self.install("--tool", "claude-code", "--runbook", "fixture", "--dry-run", success=False)

    def test_empty_invalid_and_unsupported_selections_fail(self):
        roster = self.base / "empty.txt"
        roster.write_text("# no agents\n")
        for args in [("--tool", "claude-code", "--agents-file", str(roster)),
                     ("--tool", "claude-code", "--runbook", "unknown"),
                     ("--tool", ","), ("--agent", ","), ("--division", ","), ("--unknown",), ("--jobs", "0")]:
            with self.subTest(args=args):
                self.install(*args, "--dry-run", success=False)
        for tool in ("aider", "windsurf", "hermes"):
            self.install("--tool", tool, "--agent", "engineering-alpha", "--dry-run", success=False)
        self.command("convert.sh", "--unknown", success=False)
        self.command("convert.sh", "--jobs", "0", success=False)

    def test_switching_links_to_copies_preserves_source(self):
        destination = self.base / "links"
        args = ("--tool", "claude-code", "--agent", "engineering-alpha", "--path", str(destination))
        source = self.repo / "engineering/engineering-alpha.md"
        before = source.read_bytes()
        self.install(*args, "--link")
        self.assertTrue((destination / source.name).is_symlink())
        self.install(*args)
        self.assertFalse((destination / source.name).is_symlink())
        self.assertEqual(source.read_bytes(), before)

    def test_body_separator_survives_conversion(self):
        self.command("convert.sh", "--tool", "qwen")
        output = (self.repo / "integrations/qwen/agents/alpha-agent.md").read_text()
        self.assertIn("Fixture persona.\n\n---\n\n## Core Mission", output)


class RealRunbookTests(unittest.TestCase):
    def test_every_real_runbook_resolves(self):
        runbooks = json.loads((ROOT / "strategy/runbooks.json").read_text())["runbooks"]
        for runbook in runbooks:
            with self.subTest(runbook=runbook["slug"]):
                result = subprocess.run(["python3", str(ROOT / "scripts/resolve-agents.py"),
                                         "--runbook", runbook["slug"]], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = {a for group in runbook["roster"] for a in group["agents"]}
                self.assertEqual(len(result.stdout.splitlines()), len(expected))


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class KimiAdapterTests(unittest.TestCase):
    def run_cmd(self, *args, cwd=ROOT, env=None):
        result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_renderer_uses_current_markdown_contract_and_tool_mapping(self):
        with tempfile.TemporaryDirectory(prefix="agency-kimi-render-") as td:
            out = Path(td)
            self.run_cmd("bash", "scripts/convert.sh", "--tool", "kimi", "--out", str(out))
            privileged = out / "kimi/agents/paid-media-auditor.md"
            self.assertTrue(privileged.is_file())
            text = privileged.read_text()
            front = yaml.safe_load(text.split("\n---", 1)[0][3:])
            self.assertEqual(front["name"], "paid-media-auditor")
            self.assertIn("Read", front["tools"])
            self.assertIn("WebSearch", front["tools"])
            self.assertIn("FetchURL", front["tools"])
            self.assertIn("Write", front["tools"])
            self.assertIn("Edit", front["tools"])
            self.assertNotIn("WebFetch", front["tools"])
            self.assertNotIn("Bash", front["tools"])

            no_tools = None
            for path in sorted(out.glob("kimi/agents/*.md")):
                data = yaml.safe_load(path.read_text().split("\n---", 1)[0][3:])
                if data.get("tools") == []:
                    no_tools = path
                    break
            self.assertIsNotNone(no_tools, "expected at least one source class=none agent to render tools: []")

    def test_installer_honors_kimi_code_home_agents_directory(self):
        with tempfile.TemporaryDirectory(prefix="agency-kimi-install-") as td:
            base = Path(td)
            home = base / "home"
            home.mkdir()
            kimi_home = base / "custom-kimi-home"
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["KIMI_CODE_HOME"] = str(kimi_home)
            self.run_cmd("bash", "scripts/install.sh", "--no-interactive", "--tool", "kimi",
                         "--agent", "paid-media-auditor", cwd=ROOT, env=env)
            installed = kimi_home / "agents/paid-media-auditor.md"
            self.assertTrue(installed.is_file())
            data = yaml.safe_load(installed.read_text().split("\n---", 1)[0][3:])
            self.assertNotIn("Bash", data["tools"])
            self.assertIn("FetchURL", data["tools"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check-agent-privileges.py"
spec = importlib.util.spec_from_file_location("agent_privileges", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ToolDeclarationTests(unittest.TestCase):
    def setUp(self):
        self.classes, self.policy = module.load_tool_policy(ROOT)

    def test_accepts_canonical_scalar(self):
        self.assertEqual(
            ["Read", "WebSearch", "Write"],
            module.parse_tools("Read, WebSearch, Write"),
        )

    def test_rejects_sequence(self):
        with self.assertRaisesRegex(ValueError, "comma-separated YAML scalar"):
            module.parse_tools(["Read", "Write"])

    def test_rejects_empty_and_duplicate_tokens(self):
        with self.assertRaisesRegex(ValueError, "empty token"):
            module.parse_tools("Read, , Write")
        with self.assertRaisesRegex(ValueError, "duplicate tool token"):
            module.parse_tools("Read, Read")

    def test_rejects_invalid_token(self):
        with self.assertRaisesRegex(ValueError, "invalid tool token"):
            module.parse_tools("Read, shell command")

    def test_registry_is_closed_over_current_least_privilege_universe(self):
        self.assertEqual(
            {"Edit", "Read", "WebFetch", "WebSearch", "Write"},
            set(self.policy),
        )
        for token in ("Bash", "UnreviewedTool"):
            with self.assertRaisesRegex(ValueError, "unregistered tool token"):
                module.validate_registered_tools(["Read", token], self.policy)

    def test_declared_class_uses_highest_registered_privilege(self):
        self.assertEqual("read", module.declared_class(["Read"], self.classes, self.policy))
        self.assertEqual(
            "network-read",
            module.declared_class(["Read", "WebFetch"], self.classes, self.policy),
        )
        self.assertEqual(
            "write",
            module.declared_class(["Read", "Write", "Edit"], self.classes, self.policy),
        )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "import-openclaw-community.py"
spec = importlib.util.spec_from_file_location("openclaw_importer", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProvenanceTests(unittest.TestCase):
    def test_git_blob_sha_matches_git_object_format(self):
        self.assertEqual(
            "ce013625030ba8dba906f756967f9e9ca394464a",
            module.git_blob_sha(b"hello\n"),
        )

    def test_verified_blob_text_accepts_exact_bytes(self):
        data = b"canonical source\n"
        expected = module.git_blob_sha(data)
        with mock.patch.object(module, "http_bytes", return_value=data):
            self.assertEqual("canonical source\n", module.verified_blob_text("https://example.invalid/source", expected))

    def test_verified_blob_text_rejects_mismatch(self):
        expected = module.git_blob_sha(b"expected\n")
        with mock.patch.object(module, "http_bytes", return_value=b"tampered\n"):
            with self.assertRaisesRegex(ValueError, "Git blob mismatch"):
                module.verified_blob_text("https://example.invalid/source", expected)

    def test_source_ref_must_be_full_commit_sha(self):
        self.assertTrue(module.immutable_source_ref("05820c51125e86a979432e21651d34dc9b14621f"))
        self.assertFalse(module.immutable_source_ref("main"))
        self.assertFalse(module.immutable_source_ref("05820c5"))

    def test_parallel_fetch_reports_blob_mismatch_without_accepting_bad_text(self):
        good = b"good\n"
        bad = b"bad\n"
        discovered = [
            {"source_path": "agents/a/SOUL.md", "source_blob": module.git_blob_sha(good)},
            {"source_path": "agents/b/SOUL.md", "source_blob": module.git_blob_sha(b"expected\n")},
        ]

        def fake_http_bytes(url: str) -> bytes:
            return good if "agents/a/" in url else bad

        with mock.patch.object(module, "http_bytes", side_effect=fake_http_bytes):
            texts, errors = module.fetch_source_texts(discovered, module.DEFAULT_SOURCE_REF, workers=1)

        self.assertEqual({"agents/a/SOUL.md": "good\n"}, texts)
        self.assertEqual(1, len(errors))
        self.assertEqual("agents/b/SOUL.md", errors[0]["source_path"])
        self.assertIn("Git blob mismatch", errors[0]["error"])


if __name__ == "__main__":
    unittest.main()

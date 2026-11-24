"""Tests for the --help-json machine contract (klanker/harness probe surface)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest

from agents_voice.__main__ import CLASSIFICATION, help_json


class HelpJsonTests(unittest.TestCase):
    def test_commands_is_dict_with_side_effects(self) -> None:
        spec = help_json()
        self.assertIsInstance(spec["commands"], dict)
        self.assertEqual(spec["classification"]["field"], "side_effects")
        for name, meta in spec["commands"].items():
            with self.subTest(command=name):
                self.assertIn(meta["side_effects"], ("read-only", "mutating"))
                self.assertEqual(meta["mutates"], meta["side_effects"] == "mutating")
                self.assertEqual(
                    meta["annotations"]["readOnlyHint"],
                    meta["side_effects"] == "read-only",
                )
                self.assertIn("usage", meta)
                self.assertIn("description", meta)

    def test_tts_inbox_hotkey_commands_host_local(self) -> None:
        commands = help_json()["commands"]
        for name in ("speak", "play", "listen", "test", "stop", "config", "serve"):
            with self.subTest(command=name):
                self.assertTrue(commands[name]["host_local"], name)
        self.assertEqual(commands["status"]["side_effects"], "read-only")

    def test_help_json_subprocess(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "agents_voice", "--help-json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        parsed = json.loads(proc.stdout)
        self.assertIsInstance(parsed["commands"], dict)
        self.assertTrue(parsed["cordis_expose"])


if __name__ == "__main__":
    unittest.main()

"""Tests for the --help-json machine contract (klanker/harness probe surface)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unittest

from agents_voice.__main__ import CLASSIFICATION, _build_parser, help_json


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
        for name in ("speak", "play", "test", "stop", "serve"):
            with self.subTest(command=name):
                self.assertTrue(commands[name]["host_local"], name)
        self.assertEqual(commands["status"]["side_effects"], "read-only")

    def test_host_config_commands_hidden(self) -> None:
        commands = help_json()["commands"]
        for name in ("config", "listen"):
            with self.subTest(command=name):
                self.assertNotIn(name, commands)

    def test_commands_match_argparse_subparsers(self) -> None:
        subs = next(
            a for a in _build_parser()._actions
            if isinstance(a, argparse._SubParsersAction)
        )
        exposed = set(help_json()["commands"])
        declared = set(subs.choices)
        self.assertTrue(exposed <= declared)
        self.assertEqual(declared - exposed, {"config", "listen"})

    def test_chime_argparse_accepts_enum(self) -> None:
        parser = _build_parser()
        for v in ("true", "false"):
            with self.subTest(chime=v):
                args = parser.parse_args(["config", "--chime", v])
                self.assertEqual(args.chime, v)
        with self.assertRaises(SystemExit):
            parser.parse_args(["config", "--chime"])

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

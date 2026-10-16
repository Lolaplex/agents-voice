"""Tests for FastMCP server tools."""

import json
import unittest
from unittest.mock import patch

from agents_voice.mcp_server import voice_speak, voice_status, voice_stop


class TestMCPServer(unittest.TestCase):
    def test_voice_speak_empty(self):
        res = voice_speak("   ")
        self.assertIn("Kein Text", res)

    @patch("agents_voice.mcp_server.speak", return_value="Spoken standalone via azure")
    def test_voice_speak_success(self, mock_speak):
        res = voice_speak("Build completed successfully")
        self.assertIn("OK: Spoken standalone via azure", res)
        self.assertIn("Build completed successfully", res)
        mock_speak.assert_called_once_with(
            "Build completed successfully",
            wait=False,
            provider=None,
            model=None,
            voice=None,
        )

    @patch("agents_voice.mcp_server.stop")
    def test_voice_stop(self, mock_stop):
        res = voice_stop()
        self.assertIn("Audio-Wiedergabe sofort gestoppt", res)
        mock_stop.assert_called_once()

    def test_voice_status(self):
        res_json = voice_status()
        status = json.loads(res_json)
        self.assertIn("provider", status)
        self.assertIn("model", status)
        self.assertIn("voice", status)
        self.assertIn("ready", status)


if __name__ == "__main__":
    unittest.main()

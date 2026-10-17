"""Tests for speech engine orchestration and routing."""

import unittest
from unittest.mock import MagicMock, patch

from agents_voice.config import VoiceConfig
from agents_voice.engine import speak, stop


class TestEngine(unittest.TestCase):
    def test_speak_empty_text(self):
        res = speak("   ")
        self.assertEqual(res, "Empty text, nothing spoken")

    @patch("agents_voice.engine.check_dumbo_bridge_alive", return_value=True)
    @patch("agents_voice.engine.send_to_dumbo_bridge", return_value=True)
    def test_speak_via_dumbo_bridge(self, mock_send, mock_check):
        cfg = VoiceConfig(use_dumbo_bridge_if_available=True)
        res = speak("Hello from test", config=cfg)
        self.assertEqual(res, "Spoken via Dumbo Veadio HUD")
        mock_send.assert_called_once_with("Hello from test", cfg.dumbo_bridge_port)

    @patch("agents_voice.engine.check_dumbo_bridge_alive", return_value=False)
    @patch("agents_voice.engine.synthesize_azure")
    @patch("agents_voice.engine.play_wav")
    def test_speak_standalone_azure(self, mock_play, mock_synth, mock_check):
        mock_synth.return_value = b"RIFFfakeaudio"
        cfg = VoiceConfig(provider="azure", mode="direct", keys={"azure": "fake-key"})

        res = speak("Testing standalone", config=cfg, wait=False)
        self.assertIn("Spoken directly via azure", res)
        mock_synth.assert_called_once()
        mock_play.assert_called_once_with(b"RIFFfakeaudio", wait=False)

    @patch("agents_voice.engine.check_dumbo_bridge_alive", return_value=False)
    @patch("agents_voice.engine.synthesize_azure")
    def test_speak_inbox_mode(self, mock_synth, mock_check):
        mock_synth.return_value = b"RIFFfakeaudio"
        cfg = VoiceConfig(provider="azure", mode="inbox", hotkey="alt+v", keys={"azure": "fake-key"})

        res = speak("Testing inbox", config=cfg, wait=False)
        self.assertIn("In Mailbox gespeichert", res)
        self.assertIn("ALT+V", res)

    @patch("agents_voice.engine.stop_playback")
    def test_stop(self, mock_stop_playback):
        cfg = VoiceConfig()
        res = stop(config=cfg)
        self.assertEqual(res, "Speech stopped")
        mock_stop_playback.assert_called_once_with(cfg.dumbo_bridge_port)


if __name__ == "__main__":
    unittest.main()

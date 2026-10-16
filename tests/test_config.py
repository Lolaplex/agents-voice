"""Tests for configuration dataclass, defaults, and persistence."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents_voice.config import (
    PROVIDER_DEFAULTS,
    VoiceConfig,
    load_config,
    save_config,
)


class TestVoiceConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = VoiceConfig()
        self.assertEqual(cfg.provider, "azure")
        self.assertEqual(cfg.azure_region, "swedencentral")
        self.assertEqual(cfg.speed, 1.0)
        self.assertTrue(cfg.use_dumbo_bridge_if_available)

    def test_to_and_from_dict(self):
        cfg = VoiceConfig(
            provider="openrouter",
            model="openai/gpt-4o-mini-tts",
            voice="marin",
            speed=1.2,
            keys={"openrouter": "test-key-123"},
        )
        data = cfg.to_dict()
        self.assertEqual(data["provider"], "openrouter")
        self.assertEqual(data["keys"]["openrouter"], "test-key-123")

        loaded = VoiceConfig.from_dict(data)
        self.assertEqual(loaded.provider, "openrouter")
        self.assertEqual(loaded.model, "openai/gpt-4o-mini-tts")
        self.assertEqual(loaded.voice, "marin")
        self.assertEqual(loaded.speed, 1.2)
        self.assertEqual(loaded.get_key("openrouter"), "test-key-123")

    def test_env_key_fallback(self):
        cfg = VoiceConfig(provider="gemini")
        with patch.dict("os.environ", {"GEMINI_API_KEY": "env-gemini-key"}):
            self.assertEqual(cfg.get_key("gemini"), "env-gemini-key")
            self.assertEqual(cfg.get_key(), "env-gemini-key")

    def test_save_and_load_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "voice.json"
            with patch("agents_voice.config.CONFIG_FILE", test_file), patch(
                "agents_voice.config.CONFIG_DIR", Path(tmpdir)
            ):
                saved = save_config(
                    provider="openai",
                    key="sk-test-abc",
                    voice="cedar",
                )
                self.assertEqual(saved.provider, "openai")
                self.assertEqual(saved.voice, "cedar")
                self.assertEqual(saved.get_key("openai"), "sk-test-abc")
                self.assertTrue(test_file.exists())

                loaded = load_config()
                self.assertEqual(loaded.provider, "openai")
                self.assertEqual(loaded.voice, "cedar")
                self.assertEqual(loaded.get_key("openai"), "sk-test-abc")


if __name__ == "__main__":
    unittest.main()

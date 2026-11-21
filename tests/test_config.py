"""Tests for configuration dataclass, defaults, and persistence."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

from agents_workspace import Host, doctor, resolve_secret

from agents_voice import config as config_mod
from agents_voice.config import (
    PROVIDER_DEFAULTS,
    VoiceConfig,
    config_file,
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
        self.assertNotIn("keys", data)

        # 1-release fallback read for legacy voice.json containing "keys"
        legacy_payload = dict(data)
        legacy_payload["keys"] = {"openrouter": "test-key-123"}
        loaded = VoiceConfig.from_dict(legacy_payload)
        self.assertEqual(loaded.provider, "openrouter")
        self.assertEqual(loaded.model, "openai/gpt-4o-mini-tts")
        self.assertEqual(loaded.voice, "marin")
        self.assertEqual(loaded.speed, 1.2)
        self.assertEqual(loaded.get_key("openrouter"), "test-key-123")

    def test_env_key_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = VoiceConfig(provider="gemini")
            with patch.dict(
                "os.environ",
                {
                    "AGENTS_HOST_DIR": tmpdir,
                    "APPDATA": "",
                    "GEMINI_API_KEY": "env-gemini-key",
                },
            ):
                self.assertEqual(cfg.get_key("gemini"), "env-gemini-key")
                self.assertEqual(cfg.get_key(), "env-gemini-key")

    def test_save_and_load_config_uses_host_vault(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "voice.json"
            with patch.dict(
                "os.environ",
                {
                    "AGENTS_HOST_DIR": tmpdir,
                    "AGENTS_VOICE_CONFIG": str(test_file),
                    "APPDATA": "",
                    "OPENAI_API_KEY": "",
                },
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

                raw = test_file.read_text(encoding="utf-8")
                self.assertNotIn("sk-test-abc", raw)
                self.assertNotIn("keys", json.loads(raw))
                self.assertEqual(
                    resolve_secret("OPENAI_API_KEY", scope="host"), "sk-test-abc"
                )
                self.assertEqual(doctor(Host.open(tmpdir))["status"], "ok")

                loaded = load_config()
                self.assertEqual(loaded.provider, "openai")
                self.assertEqual(loaded.voice, "cedar")
                self.assertEqual(loaded.get_key("openai"), "sk-test-abc")

    def test_legacy_keys_fallback_and_migration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            voice_path = Path(tmpdir) / "voice.json"
            voice_path.write_text(
                json.dumps(
                    {
                        "provider": "azure",
                        "keys": {"azure": "legacy-az", "openai": "legacy-oa"},
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(
                "os.environ",
                {
                    "AGENTS_HOST_DIR": tmpdir,
                    "APPDATA": "",
                    "AZURE_SPEECH_KEY": "",
                    "AZURE_TTS_KEY": "",
                    "OPENAI_API_KEY": "",
                },
            ):
                os.environ.pop("AGENTS_VOICE_CONFIG", None)
                loaded = load_config()
                self.assertEqual(loaded.get_key("azure"), "legacy-az")
                self.assertEqual(loaded.get_key("openai"), "legacy-oa")

                save_config(voice="de-DE-ConradNeural")
                disk = json.loads(voice_path.read_text(encoding="utf-8"))
                self.assertNotIn("keys", disk)
                self.assertEqual(
                    resolve_secret("AZURE_SPEECH_KEY", scope="host"), "legacy-az"
                )
                self.assertEqual(
                    resolve_secret("OPENAI_API_KEY", scope="host"), "legacy-oa"
                )
                self.assertEqual(doctor(Host.open(tmpdir))["status"], "ok")

    def test_save_empty_key_clears_vault(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(
                "os.environ",
                {
                    "AGENTS_HOST_DIR": tmpdir,
                    "APPDATA": "",
                    "AZURE_SPEECH_KEY": "",
                    "AZURE_TTS_KEY": "",
                },
            ):
                os.environ.pop("AGENTS_VOICE_CONFIG", None)
                save_config(provider="azure", key="az-secret")
                self.assertEqual(load_config().get_key("azure"), "az-secret")
                save_config(provider="azure", key="")
                self.assertEqual(load_config().get_key("azure"), "")

    def test_standalone_without_agents_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            spec = importlib.util.spec_from_file_location(
                "agents_voice_standalone_cfg_test", config_mod.__file__
            )
            assert spec is not None and spec.loader is not None
            standalone_mod = importlib.util.module_from_spec(spec)
            with patch.dict(
                sys.modules,
                {
                    "agents_workspace": None,
                    "agents_voice_standalone_cfg_test": standalone_mod,
                },
            ):
                spec.loader.exec_module(standalone_mod)
            self.assertIsNone(standalone_mod.Host)
            self.assertIsNone(standalone_mod.resolve_secret)
            self.assertIsNone(standalone_mod.write_secret)

            with patch.dict(
                "os.environ",
                {
                    "AGENTS_HOST_DIR": tmpdir,
                    "APPDATA": "",
                    "OPENAI_API_KEY": "env-only-key",
                },
            ):
                os.environ.pop("AGENTS_VOICE_CONFIG", None)
                self.assertEqual(standalone_mod.config_file(), Path(tmpdir) / "voice.json")
                cfg = standalone_mod.save_config(provider="openai", voice="coral")
                self.assertEqual(cfg.get_key("openai"), "env-only-key")
                disk = json.loads((Path(tmpdir) / "voice.json").read_text(encoding="utf-8"))
                self.assertNotIn("keys", disk)

                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    cfg2 = standalone_mod.save_config(provider="openai", key="in-mem-only")
                self.assertTrue(any(issubclass(w.category, UserWarning) for w in caught))
                self.assertEqual(cfg2.get_key("openai"), "in-mem-only")
                self.assertNotIn(
                    "in-mem-only",
                    (Path(tmpdir) / "voice.json").read_text(encoding="utf-8"),
                )


if __name__ == "__main__":
    unittest.main()

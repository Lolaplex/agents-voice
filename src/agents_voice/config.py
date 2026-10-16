"""Configuration management for agents-voice."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".agents"
CONFIG_FILE = CONFIG_DIR / "voice.json"

DEFAULT_PROVIDER = "azure"
DEFAULT_AZURE_REGION = "westeurope"
DEFAULT_AZURE_VOICE = "de-DE-SeraphinaMultilingualNeural"
DEFAULT_SPEED = 1.05


@dataclass
class VoiceConfig:
    provider: str = DEFAULT_PROVIDER
    azure_key: str = ""
    azure_region: str = DEFAULT_AZURE_REGION
    voice: str = DEFAULT_AZURE_VOICE
    speed: float = DEFAULT_SPEED
    dumbo_bridge_port: int = 12480
    use_dumbo_bridge_if_available: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> VoiceConfig:
        return cls(
            provider=data.get("provider", DEFAULT_PROVIDER),
            azure_key=data.get("azure_key", ""),
            azure_region=data.get("azure_region", DEFAULT_AZURE_REGION),
            voice=data.get("voice", DEFAULT_AZURE_VOICE),
            speed=float(data.get("speed", DEFAULT_SPEED)),
            dumbo_bridge_port=int(data.get("dumbo_bridge_port", 12480)),
            use_dumbo_bridge_if_available=bool(data.get("use_dumbo_bridge_if_available", True)),
        )


def _read_dumbo_fallback_key() -> str:
    """Best-effort discovery of existing Azure key from Dumbo app data."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return ""
    candidates = [
        Path(appdata) / "com.lolaplex.dumbo" / "tts_keys.json",
        Path(appdata) / "com.lolax.dumbo" / "tts_keys.json",
    ]
    for path in candidates:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                key = data.get("azure", "")
                if key and isinstance(key, str) and key.strip():
                    return key.strip()
            except Exception:
                pass
    return ""


def load_config() -> VoiceConfig:
    """Loads configuration from ~/.agents/voice.json with env and Dumbo fallbacks."""
    config = VoiceConfig()

    # 1. Read from ~/.agents/voice.json if exists
    if CONFIG_FILE.is_file():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            config = VoiceConfig.from_dict(data)
        except Exception:
            pass

    # 2. Environment variables override
    env_key = os.environ.get("AZURE_SPEECH_KEY") or os.environ.get("AZURE_TTS_KEY")
    if env_key:
        config.azure_key = env_key.strip()

    env_region = os.environ.get("AZURE_SPEECH_REGION") or os.environ.get("AZURE_TTS_REGION")
    if env_region:
        config.azure_region = env_region.strip()

    env_voice = os.environ.get("VOICE_NAME") or os.environ.get("AZURE_VOICE")
    if env_voice:
        config.voice = env_voice.strip()

    env_provider = os.environ.get("VOICE_PROVIDER")
    if env_provider:
        config.provider = env_provider.strip().lower()

    # 3. If still no azure key, fallback to existing Dumbo key
    if not config.azure_key:
        config.azure_key = _read_dumbo_fallback_key()

    return config


def save_config(
    provider: Optional[str] = None,
    azure_key: Optional[str] = None,
    azure_region: Optional[str] = None,
    voice: Optional[str] = None,
    speed: Optional[float] = None,
) -> VoiceConfig:
    """Saves updated configuration to ~/.agents/voice.json."""
    config = load_config()

    if provider is not None:
        config.provider = provider.strip().lower()
    if azure_key is not None:
        config.azure_key = azure_key.strip()
    if azure_region is not None:
        config.azure_region = azure_region.strip()
    if voice is not None:
        config.voice = voice.strip()
    if speed is not None:
        config.speed = float(speed)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    return config

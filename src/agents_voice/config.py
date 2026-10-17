"""Multi-provider configuration management for agents-voice."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

CONFIG_DIR = Path.home() / ".agents"
CONFIG_FILE = CONFIG_DIR / "voice.json"

PROVIDER_DEFAULTS = {
    "azure": {
        "model": "dragon-hd",
        "voice": "de-DE-Seraphina:DragonHDLatestNeural",
        "region": "swedencentral",
        "base_url": "",
    },
    "openrouter": {
        "model": "openai/gpt-4o-mini-tts",
        "voice": "marin",
        "region": "",
        "base_url": "https://openrouter.ai/api/v1",
    },
    "openai": {
        "model": "gpt-4o-mini-tts",
        "voice": "marin",
        "region": "",
        "base_url": "https://api.openai.com/v1",
    },
    "gemini": {
        "model": "gemini-2.5-flash-preview-tts",
        "voice": "Kore",
        "region": "",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
    },
    "elevenlabs": {
        "model": "eleven_turbo_v2_5",
        "voice": "JBFqnCBsd6RMkjVDRZzb",
        "region": "",
        "base_url": "https://api.elevenlabs.io/v1",
    },
    "custom": {
        "model": "tts-1",
        "voice": "af_heart",
        "region": "",
        "base_url": "http://127.0.0.1:8880/v1",
    },
}

DEFAULT_INSTRUCTIONS = (
    "Speak naturally and briskly in German. Pronounce English technical and programming "
    "terms with native English pronunciation."
)


@dataclass
class VoiceConfig:
    provider: str = "azure"
    model: str = "dragon-hd"
    voice: str = "de-DE-Seraphina:DragonHDLatestNeural"
    speed: float = 1.0
    azure_region: str = "swedencentral"
    base_url: str = ""
    instructions: str = DEFAULT_INSTRUCTIONS
    keys: Dict[str, str] = field(default_factory=dict)
    dumbo_bridge_port: int = 12480
    use_dumbo_bridge_if_available: bool = True
    mode: str = "inbox"  # "inbox" (save + chime + hotkey play) or "direct" (immediate playback)
    hotkey: str = "alt+v"
    chime: bool = True

    @property
    def azure_key(self) -> str:
        return self.get_key("azure")

    def get_key(self, provider: Optional[str] = None) -> str:
        prov = (provider or self.provider).strip().lower()
        # 1. Explicit keys dict
        if prov in self.keys and self.keys[prov].strip():
            return self.keys[prov].strip()

        # 2. Environment variables
        env_map = {
            "azure": ["AZURE_SPEECH_KEY", "AZURE_TTS_KEY"],
            "openrouter": ["OPENROUTER_API_KEY"],
            "openai": ["OPENAI_API_KEY"],
            "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
            "elevenlabs": ["ELEVENLABS_API_KEY", "XI_API_KEY"],
            "custom": ["CUSTOM_TTS_KEY", "OPENAI_API_KEY"],
        }
        for env_name in env_map.get(prov, []):
            val = os.environ.get(env_name, "").strip()
            if val:
                return val

        # 3. Dumbo fallback keys
        dumbo_keys = _read_dumbo_fallback_keys()
        if prov in dumbo_keys and dumbo_keys[prov].strip():
            return dumbo_keys[prov].strip()

        return ""

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "voice": self.voice,
            "speed": self.speed,
            "azure_region": self.azure_region,
            "base_url": self.base_url,
            "instructions": self.instructions,
            "keys": self.keys,
            "dumbo_bridge_port": self.dumbo_bridge_port,
            "use_dumbo_bridge_if_available": self.use_dumbo_bridge_if_available,
            "mode": self.mode,
            "hotkey": self.hotkey,
            "chime": self.chime,
        }

    @classmethod
    def from_dict(cls, data: dict) -> VoiceConfig:
        prov = str(data.get("provider", "azure")).strip().lower()
        defaults = PROVIDER_DEFAULTS.get(prov, PROVIDER_DEFAULTS["azure"])
        keys = dict(data.get("keys") or {})
        legacy_azure_key = str(data.get("azure_key", "")).strip()
        if legacy_azure_key and "azure" not in keys:
            keys["azure"] = legacy_azure_key

        return cls(
            provider=prov,
            model=str(data.get("model") or defaults["model"]),
            voice=str(data.get("voice") or defaults["voice"]),
            speed=float(data.get("speed", 1.0)),
            azure_region=str(data.get("azure_region") or defaults["region"] or "swedencentral"),
            base_url=str(data.get("base_url") or defaults["base_url"]),
            instructions=str(data.get("instructions") or DEFAULT_INSTRUCTIONS),
            keys=keys,
            dumbo_bridge_port=int(data.get("dumbo_bridge_port", 12480)),
            use_dumbo_bridge_if_available=bool(data.get("use_dumbo_bridge_if_available", True)),
            mode=str(data.get("mode", "inbox")).strip().lower(),
            hotkey=str(data.get("hotkey", "alt+v")).strip().lower(),
            chime=bool(data.get("chime", True)),
        )


def _read_dumbo_fallback_keys() -> Dict[str, str]:
    """Best-effort discovery of existing TTS keys from Dumbo app data."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return {}
    result: Dict[str, str] = {}
    candidates = [
        Path(appdata) / "com.lolaplex.dumbo" / "tts_keys.json",
        Path(appdata) / "com.lolax.dumbo" / "tts_keys.json",
    ]
    for path in candidates:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, str) and v.strip() and k not in result:
                            result[k.strip().lower()] = v.strip()
            except Exception:
                pass
    return result


def load_config() -> VoiceConfig:
    """Loads configuration from ~/.agents/voice.json with env and Dumbo fallbacks."""
    config = VoiceConfig()

    if CONFIG_FILE.is_file():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            config = VoiceConfig.from_dict(data)
        except Exception:
            pass

    # Env overrides
    env_provider = os.environ.get("VOICE_PROVIDER")
    if env_provider:
        config.provider = env_provider.strip().lower()

    env_model = os.environ.get("VOICE_MODEL")
    if env_model:
        config.model = env_model.strip()

    env_voice = os.environ.get("VOICE_NAME") or os.environ.get("AZURE_VOICE")
    if env_voice:
        config.voice = env_voice.strip()

    env_region = os.environ.get("AZURE_SPEECH_REGION") or os.environ.get("AZURE_TTS_REGION")
    if env_region:
        config.azure_region = env_region.strip()

    env_base_url = os.environ.get("VOICE_BASE_URL")
    if env_base_url:
        config.base_url = env_base_url.strip()

    return config


def save_config(
    provider: Optional[str] = None,
    key: Optional[str] = None,
    model: Optional[str] = None,
    voice: Optional[str] = None,
    azure_region: Optional[str] = None,
    base_url: Optional[str] = None,
    instructions: Optional[str] = None,
    speed: Optional[float] = None,
    mode: Optional[str] = None,
    hotkey: Optional[str] = None,
    chime: Optional[bool] = None,
) -> VoiceConfig:
    """Saves updated configuration to ~/.agents/voice.json."""
    config = load_config()

    provider_changed = False
    if provider is not None:
        new_prov = provider.strip().lower()
        if new_prov != config.provider:
            provider_changed = True
            config.provider = new_prov

    defaults = PROVIDER_DEFAULTS.get(config.provider, PROVIDER_DEFAULTS["custom"])

    # If user switched provider without specifying model/voice/base_url, apply provider defaults
    if provider_changed:
        if model is None:
            config.model = defaults["model"]
        if voice is None:
            config.voice = defaults["voice"]
        if base_url is None:
            config.base_url = defaults["base_url"]

    if model is not None:
        config.model = model.strip()
    if voice is not None:
        config.voice = voice.strip()
    if azure_region is not None:
        config.azure_region = azure_region.strip()
    if base_url is not None:
        config.base_url = base_url.strip()
    if instructions is not None:
        config.instructions = instructions.strip()
    if speed is not None:
        config.speed = float(speed)
    if mode is not None:
        config.mode = mode.strip().lower()
    if hotkey is not None:
        config.hotkey = hotkey.strip().lower()
    if chime is not None:
        config.chime = bool(chime)

    if key is not None:
        clean_key = key.strip()
        config.keys[config.provider] = clean_key

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    return config

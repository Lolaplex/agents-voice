"""Multi-provider configuration management for agents-voice."""

from __future__ import annotations

import json
import os
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    from agents_workspace import Host, delete_secret, resolve_secret, write_secret
except ImportError:
    Host = None  # type: ignore[assignment]
    delete_secret = None  # type: ignore[assignment]
    resolve_secret = None  # type: ignore[assignment]
    write_secret = None  # type: ignore[assignment]


def _fallback_host_dir() -> Path:
    raw = os.environ.get("AGENTS_HOST_DIR", "").strip()
    return Path(raw).expanduser() if raw else Path.home() / ".agents"


def config_file() -> Path:
    """voice.json lives on the host root next to mcp.json/secrets.json —
    provider keys are host infra, not workspace data. AGENTS_VOICE_CONFIG
    overrides for tests and standalone use."""
    override = os.environ.get("AGENTS_VOICE_CONFIG")
    if override:
        return Path(override)
    if Host is not None:
        return Host.from_env().dir / "voice.json"
    return _fallback_host_dir() / "voice.json"


PROVIDER_KEY_ENVS: Dict[str, Tuple[str, ...]] = {
    "azure": ("AZURE_SPEECH_KEY", "AZURE_TTS_KEY"),
    "openrouter": ("OPENROUTER_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "elevenlabs": ("ELEVENLABS_API_KEY", "XI_API_KEY"),
    "custom": ("CUSTOM_TTS_KEY", "OPENAI_API_KEY"),
}


def _provider_secret_names(provider: str) -> Tuple[str, ...]:
    prov = (provider or "").strip().lower()
    if prov in PROVIDER_KEY_ENVS:
        return PROVIDER_KEY_ENVS[prov]
    slug = re.sub(r"[^A-Za-z0-9]+", "_", prov).strip("_").upper() or "CUSTOM"
    return (f"{slug}_TTS_KEY",)


def _resolve_secret_value(key: str) -> str:
    if resolve_secret is not None:
        return resolve_secret(key, scope="host").strip()
    return os.environ.get(key, "").strip()


def _vault_has_secret(key: str) -> bool:
    if resolve_secret is None:
        return False
    env_no_key = {k: v for k, v in os.environ.items() if k != key}
    return bool(resolve_secret(key, env=env_no_key, scope="host").strip())

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
        # 1. Explicit in-memory keys dict / 1-release legacy voice.json["keys"] fallback
        if prov in self.keys and str(self.keys[prov]).strip():
            return str(self.keys[prov]).strip()

        # 2. Host Secret Vault (ENV > /run/secrets > keyring > host.json), or os.environ fallback
        for env_name in _provider_secret_names(prov):
            val = _resolve_secret_value(env_name)
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
        raw_keys = data.get("keys")
        keys = (
            {
                str(k).strip().lower(): str(v).strip()
                for k, v in raw_keys.items()
                if isinstance(v, str) and v.strip()
            }
            if isinstance(raw_keys, dict)
            else {}
        )
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

    cfg_file = config_file()
    if cfg_file.is_file():
        try:
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
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

    if write_secret is not None:
        # Migrate legacy voice.json["keys"] into host vault if not already stored
        for legacy_prov, legacy_val in list(config.keys.items()):
            clean_legacy = str(legacy_val or "").strip()
            if not clean_legacy:
                continue
            if key is not None and legacy_prov == config.provider:
                continue
            secret_names = _provider_secret_names(legacy_prov)
            if not any(_vault_has_secret(name) for name in secret_names):
                write_secret(secret_names[0], clean_legacy, scope="host")
        config.keys.clear()

    if key is not None:
        clean_key = key.strip()
        secret_names = _provider_secret_names(config.provider)
        if write_secret is not None:
            if clean_key:
                write_secret(secret_names[0], clean_key, scope="host")
            elif delete_secret is not None:
                for name in secret_names:
                    delete_secret(name, scope="host")
            config.keys.pop(config.provider, None)
        else:
            warnings.warn(
                f"agents-workspace is not installed; cannot persist {secret_names[0]} "
                "to host vault (set it in the environment instead)",
                UserWarning,
                stacklevel=2,
            )
            if clean_key:
                config.keys[config.provider] = clean_key
            else:
                config.keys.pop(config.provider, None)

    cfg_file = config_file()
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    cfg_file.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    return config

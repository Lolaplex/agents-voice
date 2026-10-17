"""High-level speech engine coordinating synthesis, playback, and bridges across all providers."""

from __future__ import annotations

import copy
from typing import Optional

from .azure import synthesize_azure
from .config import PROVIDER_DEFAULTS, VoiceConfig, load_config
from .player import check_dumbo_bridge_alive, play_wav, send_to_dumbo_bridge, stop_playback
from .providers import (
    synthesize_elevenlabs,
    synthesize_gemini,
    synthesize_openai_compatible,
)


def speak(
    text: str,
    wait: bool = False,
    config: Optional[VoiceConfig] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    voice: Optional[str] = None,
) -> str:
    """Speaks the given text using the configured or overridden provider/model/voice."""
    clean_text = text.strip()
    if not clean_text:
        return "Empty text, nothing spoken"

    base_cfg = config or load_config()
    cfg = copy.deepcopy(base_cfg)

    if provider:
        new_prov = provider.strip().lower()
        if new_prov != cfg.provider:
            cfg.provider = new_prov
            defaults = PROVIDER_DEFAULTS.get(new_prov, PROVIDER_DEFAULTS["custom"])
            if not model:
                cfg.model = defaults["model"]
            if not voice:
                cfg.voice = defaults["voice"]
            cfg.base_url = defaults["base_url"]
    if model:
        cfg.model = model.strip()
    if voice:
        cfg.voice = voice.strip()

    # 1. Check if Dumbo HUD bridge is active (only if no explicit provider override requested)
    if cfg.use_dumbo_bridge_if_available and not provider and not model and not voice:
        if check_dumbo_bridge_alive(cfg.dumbo_bridge_port):
            if send_to_dumbo_bridge(clean_text, cfg.dumbo_bridge_port):
                return "Spoken via Dumbo Veadio HUD"

    # 2. Standalone synthesis across providers
    prov = cfg.provider.strip().lower()
    if prov == "azure":
        audio_data = synthesize_azure(clean_text, cfg)
    elif prov in ("openrouter", "openai", "custom", "local", "kokoro"):
        norm_prov = "custom" if prov in ("local", "kokoro") else prov
        audio_data = synthesize_openai_compatible(clean_text, cfg, provider_override=norm_prov)
    elif prov == "gemini":
        audio_data = synthesize_gemini(clean_text, cfg)
    elif prov == "elevenlabs":
        audio_data = synthesize_elevenlabs(clean_text, cfg)
    else:
        raise ValueError(
            f"Unbekannter Provider '{prov}'. Unterstützt: openrouter, openai, gemini, elevenlabs, azure, custom"
        )

    # 3. Delivery mode: inbox (silent/chime, play on hotkey) vs direct (immediate playback)
    from .inbox import save_to_inbox

    save_to_inbox(
        audio_data=audio_data,
        text=clean_text,
        provider=prov,
        model=cfg.model,
        voice=cfg.voice,
        play_chime=cfg.chime,
    )

    if cfg.mode == "direct" or wait:
        play_wav(audio_data, wait=wait)
        return f"Spoken directly via {prov} ({cfg.model} / {cfg.voice})"

    return (
        f"In Mailbox gespeichert ({prov} {cfg.model}/{cfg.voice}). "
        f"Drücke {cfg.hotkey.upper()} zum Anhören."
    )


def stop(config: Optional[VoiceConfig] = None) -> str:
    """Stops any currently playing speech."""
    cfg = config or load_config()
    stop_playback(cfg.dumbo_bridge_port)
    return "Speech stopped"

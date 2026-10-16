"""High-level speech engine coordinating synthesis, playback, and bridges."""

from __future__ import annotations

from typing import Optional

from .azure import synthesize_azure
from .config import VoiceConfig, load_config
from .player import check_dumbo_bridge_alive, play_wav, send_to_dumbo_bridge, stop_playback


def speak(text: str, wait: bool = False, config: Optional[VoiceConfig] = None) -> str:
    """Speaks the given text using the best available backend.
    
    1. If Dumbo is running and enabled, delegates to Dumbo for synchronized Veadio HUD.
    2. Otherwise, synthesizes directly with Azure Speech and plays standalone.
    """
    clean_text = text.strip()
    if not clean_text:
        return "Empty text, nothing spoken"

    cfg = config or load_config()

    # 1. Check if Dumbo HUD bridge is active
    if cfg.use_dumbo_bridge_if_available:
        if check_dumbo_bridge_alive(cfg.dumbo_bridge_port):
            if send_to_dumbo_bridge(clean_text, cfg.dumbo_bridge_port):
                return "Spoken via Dumbo Veadio HUD"

    # 2. Standalone synthesis & playback
    if cfg.provider == "azure":
        wav_data = synthesize_azure(clean_text, cfg)
        play_wav(wav_data, wait=wait)
        return "Spoken standalone via Azure Speech"

    raise ValueError(f"Nicht unterstützter Voice Provider: {cfg.provider}")


def stop(config: Optional[VoiceConfig] = None) -> str:
    """Stops any currently playing speech."""
    cfg = config or load_config()
    stop_playback(cfg.dumbo_bridge_port)
    return "Speech stopped"

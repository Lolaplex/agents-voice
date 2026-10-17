"""FastMCP Server for agents-voice.

Gives AI coding agents direct speech output capabilities across OpenRouter, OpenAI, Gemini, ElevenLabs, Azure, and custom endpoints.
"""

from __future__ import annotations

import json
from typing import Optional
from mcp.server.fastmcp import FastMCP

from .config import PROVIDER_DEFAULTS, load_config
from .engine import speak, stop
from .player import check_dumbo_bridge_alive

mcp = FastMCP("agents-voice")


@mcp.tool()
def voice_speak(
    message: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    voice: Optional[str] = None,
) -> str:
    """Speak a short, natural voice summary (1-2 sentences) directly to the user's ears.

    Use this tool at the end of substantive turns to tell the user what was done,
    without reading code, diffs, or markdown formatting. Keep it concise, natural, and friendly.

    Args:
        message: The concise spoken text (e.g. 'Hab den Bug gefixt und Tests sind grün.').
        provider: Optional override ('openrouter', 'openai', 'gemini', 'elevenlabs', 'azure', 'custom').
        model: Optional model override (e.g. 'openai/gpt-4o-mini-tts', 'elevenlabs/eleven-v4-turbo').
        voice: Optional voice override (e.g. 'marin', 'cedar', 'Kore', 'de-DE-Seraphina:DragonHDLatestNeural').
    """
    clean_msg = message.strip()
    if not clean_msg:
        return "Kein Text zum Sprechen übergeben."

    try:
        result = speak(clean_msg, wait=False, provider=provider, model=model, voice=voice)
        return f"OK: {result}. Gesprochen: \"{clean_msg}\""
    except Exception as e:
        return f"Fehler bei Sprachausgabe: {e}"


@mcp.tool()
def voice_stop() -> str:
    """Immediately stops any currently playing speech audio if the user requests silence."""
    try:
        stop()
        return "Audio-Wiedergabe sofort gestoppt."
    except Exception as e:
        return f"Fehler beim Stoppen: {e}"


@mcp.tool()
def voice_play_latest() -> str:
    """Plays the most recent speech summary stored in the voice inbox."""
    from .inbox import play_latest

    try:
        return play_latest(wait=False)
    except Exception as e:
        return f"Fehler beim Abspielen: {e}"


@mcp.tool()
def voice_status() -> str:
    """Checks the status of the voice output system, active provider, configured keys, and bridge."""
    cfg = load_config()
    dumbo_alive = check_dumbo_bridge_alive(cfg.dumbo_bridge_port)
    has_active_key = bool(cfg.get_key(cfg.provider)) or cfg.provider == "custom"
    configured_providers = [
        p for p in PROVIDER_DEFAULTS if bool(cfg.get_key(p)) or p == "custom"
    ]
    from .inbox import get_latest_metadata

    latest_meta = get_latest_metadata()

    status = {
        "provider": cfg.provider,
        "model": cfg.model,
        "voice": cfg.voice,
        "mode": cfg.mode,
        "hotkey": cfg.hotkey,
        "chime": cfg.chime,
        "region": cfg.azure_region if cfg.provider == "azure" else None,
        "base_url": cfg.base_url or None,
        "has_key": has_active_key,
        "configured_providers": configured_providers,
        "dumbo_hud_bridge_active": dumbo_alive,
        "ready": has_active_key or dumbo_alive,
        "latest_inbox_message": latest_meta.get("text") if latest_meta else None,
    }
    return json.dumps(status, indent=2)


def serve() -> None:
    """Runs the FastMCP server via stdio transport and starts the background hotkey listener."""
    cfg = load_config()
    if cfg.mode == "inbox":
        from .hotkey import ensure_hotkey_listener

        ensure_hotkey_listener(cfg.hotkey)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    serve()

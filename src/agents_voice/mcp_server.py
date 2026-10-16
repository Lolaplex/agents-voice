"""FastMCP Server for agents-voice.

Gives AI coding agents direct speech output capabilities.
"""

from __future__ import annotations

import json
from mcp.server.fastmcp import FastMCP

from .config import load_config
from .engine import speak, stop
from .player import check_dumbo_bridge_alive

mcp = FastMCP("agents-voice")


@mcp.tool()
def voice_speak(message: str) -> str:
    """Speak a short, natural voice summary (1-2 sentences) directly to the user's ears.

    Use this tool at the end of substantive turns to tell the user what was done,
    without reading code, diffs, or markdown formatting. Keep it concise, natural, and friendly.

    Args:
        message: The concise spoken text (e.g. 'Hab den Bug gefixt und Tests sind grün.').
    """
    clean_msg = message.strip()
    if not clean_msg:
        return "Kein Text zum Sprechen übergeben."

    try:
        result = speak(clean_msg, wait=False)
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
def voice_status() -> str:
    """Checks the status of the voice output system, active provider, and bridge."""
    cfg = load_config()
    dumbo_alive = check_dumbo_bridge_alive(cfg.dumbo_bridge_port)
    has_key = bool(cfg.azure_key.strip())

    status = {
        "provider": cfg.provider,
        "voice": cfg.voice,
        "region": cfg.azure_region,
        "has_key": has_key,
        "dumbo_hud_bridge_active": dumbo_alive,
        "ready": has_key or dumbo_alive,
    }
    return json.dumps(status, indent=2)


def serve() -> None:
    """Runs the FastMCP server via stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    serve()

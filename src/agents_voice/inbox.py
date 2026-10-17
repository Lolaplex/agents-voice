"""Mailbox store for generated agent speech."""

from __future__ import annotations

import json
import os
import platform
import time
from pathlib import Path
from typing import Optional

from .player import play_wav, stop_playback

_IS_WINDOWS = platform.system() == "Windows"
if _IS_WINDOWS:
    import winsound

INBOX_DIR = Path.home() / ".agents" / "voice_inbox"
AUDIO_FILE = INBOX_DIR / "latest.audio"
META_FILE = INBOX_DIR / "latest.json"


def save_to_inbox(
    audio_data: bytes,
    text: str,
    provider: str,
    model: str,
    voice: str,
    play_chime: bool = True,
) -> None:
    """Saves generated speech audio and metadata into the local voice inbox."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_FILE.write_bytes(audio_data)

    meta = {
        "text": text,
        "provider": provider,
        "model": model,
        "voice": voice,
        "timestamp": time.time(),
        "played": False,
    }
    META_FILE.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    if play_chime:
        trigger_chime()


def trigger_chime() -> None:
    """Plays a subtle system notification sound (chime) indicating new speech is ready."""
    if _IS_WINDOWS:
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass


def get_latest_metadata() -> Optional[dict]:
    """Retrieves metadata of the most recent voice message."""
    if META_FILE.is_file():
        try:
            return json.loads(META_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def play_latest(wait: bool = False) -> str:
    """Plays the latest audio message from the voice inbox."""
    if not AUDIO_FILE.is_file():
        return "Keine Sprachnachricht in der Mailbox vorhanden."

    data = AUDIO_FILE.read_bytes()
    if not data:
        return "Mailbox-Datei ist leer."

    meta = get_latest_metadata() or {}
    text_preview = meta.get("text", "")
    if len(text_preview) > 60:
        text_preview = text_preview[:57] + "..."

    # Mark as played in metadata
    meta["played"] = True
    try:
        META_FILE.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    play_wav(data, wait=wait)
    return f"Spiele ab: {text_preview}" if text_preview else "Spiele letzte Sprachnachricht ab."


def has_unread() -> bool:
    """Checks if there is an unplayed voice message in the inbox."""
    meta = get_latest_metadata()
    if not meta:
        return False
    return not bool(meta.get("played", False))

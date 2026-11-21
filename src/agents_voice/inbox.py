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

def _inbox_dir() -> Path:
    """Transient spool under <host>/run/ — audio artifacts are runtime
    state, not workspace data. AGENTS_VOICE_INBOX overrides for tests."""
    override = os.environ.get("AGENTS_VOICE_INBOX", "").strip()
    if override:
        return Path(override)
    try:
        from agents_workspace import Host

        return Host.from_env().run / "voice_inbox"
    except ImportError:
        voice_dir = os.environ.get("AGENTS_VOICE_DIR", "").strip()
        if voice_dir:
            return Path(voice_dir).expanduser() / "voice_inbox"
        host_raw = os.environ.get("AGENTS_HOST_DIR", "").strip()
        base = Path(host_raw).expanduser() if host_raw else Path.home() / ".agents"
        return base / "run" / "voice_inbox"


def _audio_file() -> Path:
    return _inbox_dir() / "latest.audio"


def _meta_file() -> Path:
    return _inbox_dir() / "latest.json"


def save_to_inbox(
    audio_data: bytes,
    text: str,
    provider: str,
    model: str,
    voice: str,
    play_chime: bool = True,
) -> None:
    """Saves generated speech audio and metadata into the local voice inbox."""
    inbox = _inbox_dir()
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "latest.audio").write_bytes(audio_data)

    meta = {
        "text": text,
        "provider": provider,
        "model": model,
        "voice": voice,
        "timestamp": time.time(),
        "played": False,
    }
    _meta_file().write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

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
    meta_file = _meta_file()
    if meta_file.is_file():
        try:
            return json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def play_latest(wait: bool = False) -> str:
    """Plays the latest audio message from the voice inbox."""
    audio_file = _audio_file()
    if not audio_file.is_file():
        return "Keine Sprachnachricht in der Mailbox vorhanden."

    data = audio_file.read_bytes()
    if not data:
        return "Mailbox-Datei ist leer."

    meta = get_latest_metadata() or {}
    text_preview = meta.get("text", "")
    if len(text_preview) > 60:
        text_preview = text_preview[:57] + "..."

    # Mark as played in metadata
    meta["played"] = True
    try:
        _meta_file().write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
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

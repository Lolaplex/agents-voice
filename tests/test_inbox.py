"""Tests for agents_voice.inbox standalone and host-scoped resolution."""

from __future__ import annotations

import sys
from pathlib import Path

from agents_voice import inbox


def test_inbox_standalone_without_agents_workspace(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "agents_workspace", None)
    monkeypatch.delenv("AGENTS_VOICE_INBOX", raising=False)
    monkeypatch.delenv("AGENTS_VOICE_DIR", raising=False)

    host = tmp_path / "host"
    monkeypatch.setenv("AGENTS_HOST_DIR", str(host))
    assert inbox._inbox_dir() == host / "run" / "voice_inbox"

    inbox.save_to_inbox(b"RIFF", "hello", "azure", "dragon-hd", "voice-1", play_chime=False)
    assert (host / "run" / "voice_inbox" / "latest.audio").read_bytes() == b"RIFF"
    assert inbox.has_unread() is True
    meta = inbox.get_latest_metadata()
    assert meta is not None and meta["text"] == "hello"

    voice_dir = tmp_path / "voice_dir"
    monkeypatch.setenv("AGENTS_VOICE_DIR", str(voice_dir))
    assert inbox._inbox_dir() == voice_dir / "voice_inbox"

    monkeypatch.delenv("AGENTS_VOICE_DIR", raising=False)
    monkeypatch.delenv("AGENTS_HOST_DIR", raising=False)
    fake_home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    assert inbox._inbox_dir() == fake_home / ".agents" / "run" / "voice_inbox"

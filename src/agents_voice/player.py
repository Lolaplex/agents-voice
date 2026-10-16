"""Cross-platform audio player with zero heavy dependencies."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import tempfile
import urllib.request
from typing import Optional

from .config import VoiceConfig

_IS_WINDOWS = platform.system() == "Windows"
_IS_DARWIN = platform.system() == "Darwin"

if _IS_WINDOWS:
    import winsound


def check_dumbo_bridge_alive(port: int = 12480) -> bool:
    """Checks if Dumbo Agent Voice Bridge is alive and responding on localhost."""
    url = f"http://127.0.0.1:{port}/v1/status"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=0.4) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return bool(data.get("agentVoiceBridge"))
    except Exception:
        pass
    return False


def send_to_dumbo_bridge(text: str, port: int = 12480) -> bool:
    """Sends text to Dumbo Bridge for synchronized Veadio HUD display and playback."""
    url = f"http://127.0.0.1:{port}/v1/speak"
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=2.0) as response:
            return response.status == 200
    except Exception:
        return False


def stop_dumbo_bridge(port: int = 12480) -> bool:
    """Stops audio in Dumbo Bridge."""
    url = f"http://127.0.0.1:{port}/v1/stop"
    req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=1.0) as response:
            return response.status == 200
    except Exception:
        return False


def play_wav(data: bytes, wait: bool = False) -> None:
    """Plays WAV audio directly with zero external apps or dependencies."""
    if _IS_WINDOWS:
        flags = winsound.SND_MEMORY
        if not wait:
            flags |= winsound.SND_ASYNC
        winsound.PlaySound(data, flags)
        return

    # Fallback for macOS / Linux
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(data)
        temp_path = f.name

    try:
        if _IS_DARWIN:
            cmd = ["afplay", temp_path]
        else:
            cmd = ["aplay", "-q", temp_path]

        if wait:
            subprocess.run(cmd, check=False)
        else:
            subprocess.Popen(cmd)
    finally:
        if wait and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def stop_playback(port: int = 12480) -> None:
    """Immediately terminates any currently playing audio (local and Dumbo)."""
    # 1. Stop local audio
    if _IS_WINDOWS:
        winsound.PlaySound(None, 0)
    elif _IS_DARWIN:
        subprocess.run(["killall", "afplay"], check=False, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(["killall", "aplay"], check=False, stderr=subprocess.DEVNULL)

    # 2. Also notify Dumbo bridge if running
    stop_dumbo_bridge(port)

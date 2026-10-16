"""Direct Azure Speech REST API client using Python standard library."""

from __future__ import annotations

import html
import urllib.error
import urllib.request
from typing import Optional

from .config import VoiceConfig


def synthesize_azure(text: str, config: VoiceConfig) -> bytes:
    """Synthesizes German/multilingual text to raw 48kHz HD WAV bytes via Azure Speech REST API."""
    key = config.azure_key.strip()
    if not key:
        raise ValueError(
            "Azure Speech Key fehlt. Bitte mit 'python -m agents_voice config --key ...' setzen "
            "oder Umgebungsvariable AZURE_SPEECH_KEY definieren."
        )

    region = config.azure_region.strip() or "swedencentral"
    voice = config.voice.strip() or "de-DE-Seraphina:DragonHDLatestNeural"
    speed = config.speed if config.speed else 1.0

    # Derive locale from voice name (e.g., 'de-DE' from 'de-DE-Seraphina:DragonHDLatestNeural')
    locale = "de-DE"
    if "-" in voice:
        parts = voice.split(":")[0].split("-")
        if len(parts) >= 2:
            locale = f"{parts[0]}-{parts[1]}"

    # Clean and escape text for XML
    clean_text = html.escape(text.strip())

    # Build SSML (avoid wrapping DragonHD in prosody if speed is 1.0 to preserve natural HD prosody)
    if abs(speed - 1.0) > 0.01:
        rate_str = f"{int(round((speed - 1.0) * 100)):+d}%"
        inner = f"<prosody rate='{rate_str}'>{clean_text}</prosody>"
    else:
        inner = clean_text

    ssml = (
        f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
        f"xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='{locale}'>"
        f"<voice name='{voice}'>{inner}</voice>"
        f"</speak>"
    )

    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "riff-48khz-16bit-mono-pcm",
        "User-Agent": "agents-voice",
    }

    req = urllib.request.Request(url, data=ssml.encode("utf-8"), headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Azure Speech API Fehler ({e.code}): {err_msg}") from e
    except Exception as e:
        raise RuntimeError(f"Netzwerkfehler bei Azure Speech API: {e}") from e

"""Multi-provider TTS synthesis clients (OpenRouter, OpenAI, Gemini, ElevenLabs, Custom, Azure)."""

from __future__ import annotations

import base64
import json
import struct
import urllib.error
import urllib.request
from typing import Optional

from .azure import synthesize_azure
from .config import PROVIDER_DEFAULTS, VoiceConfig


def pcm_to_wav(
    pcm_bytes: bytes,
    sample_rate: int = 24000,
    channels: int = 1,
    bits_per_sample: int = 16,
) -> bytes:
    """Wraps raw signed 16-bit little-endian PCM bytes in a 44-byte RIFF WAV header."""
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    data_size = len(pcm_bytes)
    riff_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        riff_size,
        b"WAVE",
        b"fmt ",
        16,  # PCM chunk size
        1,   # AudioFormat 1 = PCM
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm_bytes


def _is_mp3(data: bytes) -> bool:
    if len(data) < 4:
        return False
    if data[:3] == b"ID3":
        return True
    return data[0] == 0xFF and (data[1] & 0xE0) == 0xE0


def _synthesize_openrouter_audio(
    text: str,
    key: str,
    model: str,
    voice: str,
    instructions: Optional[str] = None,
) -> bytes:
    """Synthesizes speech via OpenRouter audio chat models (openai/gpt-audio-mini, openai/gpt-audio)."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    prompt = (
        "Lies den folgenden Text laut auf Deutsch vor. Antworte ausschließlich mit dem gesprochenen Audio "
        f"dieses Textes ohne Einleitung oder eigene Kommentare:\n\n{text.strip()}"
    )
    messages = []
    if instructions:
        messages.append({"role": "system", "content": instructions})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "modalities": ["text", "audio"],
        "audio": {
            "voice": voice,
            "format": "pcm16",
        },
        "stream": True,
        "messages": messages,
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://lolaplex.org",
        "X-Title": "agents-voice",
        "User-Agent": "agents-voice",
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            chunks = []
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        obj = json.loads(line[6:])
                        choices = obj.get("choices") or []
                        if choices:
                            delta = choices[0].get("delta") or {}
                            audio_meta = delta.get("audio") or {}
                            b64_data = audio_meta.get("data")
                            if b64_data:
                                chunks.append(base64.b64decode(b64_data))
                    except Exception:
                        continue
            if not chunks:
                raise RuntimeError("OpenRouter Audio hat keine Audiodaten zurückgegeben.")
            pcm_data = b"".join(chunks)
            return pcm_to_wav(pcm_data, sample_rate=24000)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter Audio Fehler ({e.code}): {err_body}") from e


def synthesize_openai_compatible(
    text: str,
    config: VoiceConfig,
    provider_override: Optional[str] = None,
) -> bytes:
    """Synthesizes speech via OpenAI, OpenRouter, or custom OpenAI-compatible /audio/speech endpoint."""
    prov = (provider_override or config.provider).strip().lower()
    defaults = PROVIDER_DEFAULTS.get(prov, PROVIDER_DEFAULTS["openai"])

    key = config.get_key(prov)
    if not key and prov != "custom":
        raise ValueError(
            f"API Key für Provider '{prov}' fehlt. Bitte setzen mit:\n"
            f"python -m agents_voice config --provider {prov} --key <API_KEY>"
        )

    model = config.model.strip() or defaults["model"]
    voice = config.voice.strip() or defaults["voice"]
    speed = config.speed if config.speed else 1.0

    # If OpenRouter and using gpt-audio models, use OpenRouter's audio completion endpoint
    if prov == "openrouter" and ("gpt-audio" in model or "audio" in model):
        return _synthesize_openrouter_audio(
            text=text,
            key=key,
            model=model,
            voice=voice,
            instructions=config.instructions,
        )

    base_url = (config.base_url or defaults["base_url"]).rstrip("/")
    if not base_url.endswith("/v1") and "/api/v1" not in base_url:
        base_url = f"{base_url}/v1"
    url = f"{base_url}/audio/speech"

    # Try wav first for zero-latency RAM playback, fallback to mp3 if sub-provider requires it
    for fmt in ("wav", "mp3"):
        payload: dict = {
            "model": model,
            "input": text.strip(),
            "voice": voice,
            "response_format": fmt,
        }
        if abs(speed - 1.0) > 0.01:
            payload["speed"] = speed
        if config.instructions and ("gpt-4o-mini-tts" in model or "steerable" in model):
            payload["instructions"] = config.instructions

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "agents-voice",
        }
        if key:
            headers["Authorization"] = f"Bearer {key}"
        if prov == "openrouter":
            headers["HTTP-Referer"] = "https://lolaplex.org"
            headers["X-Title"] = "agents-voice"

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read()
                content_type = (response.headers.get("Content-Type") or "").lower()
                if raw[:4] == b"RIFF" or _is_mp3(raw) or "mpeg" in content_type or "mp3" in content_type:
                    return raw
                # Raw PCM returned -> wrap in 24kHz WAV header
                return pcm_to_wav(raw, sample_rate=24000)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if fmt == "wav" and e.code in (400, 422):
                continue
            raise RuntimeError(f"{prov} TTS Fehler ({e.code}): {err_body}") from e

    raise RuntimeError(f"{prov} TTS fehlgeschlagen.")


def synthesize_gemini(text: str, config: VoiceConfig) -> bytes:
    """Synthesizes speech via Google Gemini 2.5 TTS API (returns 24kHz WAV)."""
    key = config.get_key("gemini")
    if not key:
        raise ValueError(
            "Gemini API Key fehlt. Bitte setzen mit:\n"
            "python -m agents_voice config --provider gemini --key <GEMINI_API_KEY>"
        )

    defaults = PROVIDER_DEFAULTS["gemini"]
    model = config.model.strip() or defaults["model"]
    voice = config.voice.strip() or defaults["voice"]

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )

    prompt = (
        "Read the following text naturally and fluently in German, pronouncing English "
        f"technical terms natively:\n\n{text.strip()}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice,
                    }
                }
            },
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "agents-voice"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini TTS Fehler ({e.code}): {err_body}") from e

    try:
        part = parsed["candidates"][0]["content"]["parts"][0]["inlineData"]
        raw_bytes = base64.b64decode(part["data"])
        if raw_bytes[:4] == b"RIFF":
            return raw_bytes
        return pcm_to_wav(raw_bytes, sample_rate=24000)
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Gemini lieferte keine Audio-Daten: {parsed}") from e


def synthesize_elevenlabs(text: str, config: VoiceConfig) -> bytes:
    """Synthesizes speech directly via ElevenLabs API using 24kHz PCM wrapped as WAV."""
    key = config.get_key("elevenlabs")
    if not key:
        raise ValueError(
            "ElevenLabs API Key fehlt. Bitte setzen mit:\n"
            "python -m agents_voice config --provider elevenlabs --key <ELEVENLABS_KEY>"
        )

    defaults = PROVIDER_DEFAULTS["elevenlabs"]
    model = config.model.strip() or defaults["model"]
    voice_id = config.voice.strip() or defaults["voice"]

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=pcm_24000"
    payload = {
        "text": text.strip(),
        "model_id": model,
    }
    headers = {
        "xi-api-key": key,
        "Content-Type": "application/json",
        "User-Agent": "agents-voice",
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            pcm_data = response.read()
            return pcm_to_wav(pcm_data, sample_rate=24000)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs TTS Fehler ({e.code}): {err_body}") from e

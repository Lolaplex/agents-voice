<h1 align="center">agents-voice</h1>

<p align="center">
  <a href="https://github.com/Lolaplex/agents-voice/releases"><img src="https://img.shields.io/badge/version-0.0.1-blue.svg?style=flat-square" alt="Version 0.0.1"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Standard-orange.svg?style=flat-square" alt="MCP"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://pypi.org/project/agents-voice/"><img src="https://img.shields.io/pypi/v/agents-voice.svg?style=flat-square" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <strong>Fast, minimal multi-provider speech output MCP server and CLI for AI coding agents.</strong><br>
  Zero heavy dependencies. Pure Python standard library audio playback with seamless Dumbo HUD bridge synergy.
</p>

---

## Overview

`agents-voice` equips AI coding agents (Antigravity, Cursor, Zed, Claude, agents-harness) with a native voice tool (`voice_speak`). Instead of reading long code diffs or screen-scraping text, the agent formulates a concise, natural spoken summary (1–2 sentences) directly to the developer's ears upon completing tasks.

### Highlights
- **Multi-Provider Support**: Out-of-the-box support for Azure Speech (48kHz DragonHD), OpenRouter (`gpt-audio` PCM16 streaming, `gpt-4o-mini-tts`), OpenAI, Google Gemini 2.5 TTS, ElevenLabs, and custom OpenAI-compatible local endpoints (e.g., Kokoro, LocalAI).
- **Zero Heavy Dependencies**: Pure Python standard library (`urllib.request`, `winsound` / `winmm` on Windows, native OS audio players on macOS/Linux). No `ffmpeg`, no `pygame`, no C compiler required.
- **Standalone or HUD Synergy**: Plays directly through OS audio when standalone. If the Dumbo desktop overlay is running (`127.0.0.1:12480`), optionally routes through Dumbo's Veadio HUD for synchronized word-by-word highlighted playback.
- **Local Credentials**: Kept securely on the local machine in `~/.agents/voice.json` with fallback discovery from environment variables and existing Dumbo settings.

---

## Installation

```bash
pip install agents-voice
```

Or install in editable mode from source:
```bash
git clone https://github.com/Lolaplex/agents-voice.git
cd agents-voice
pip install -e .
```

---

## Configuration

Credentials and settings are saved to `~/.agents/voice.json`:

### Azure Speech (Default)
```bash
agents-voice config --provider azure --key "YOUR_AZURE_KEY" --region "swedencentral" --voice "de-DE-Seraphina:DragonHDLatestNeural"
```

### OpenRouter (Steerable & GPT Audio Streaming)
```bash
agents-voice config --provider openrouter --key "YOUR_OPENROUTER_KEY" --model "openai/gpt-4o-mini-tts" --voice "marin"
```

### OpenAI
```bash
agents-voice config --provider openai --key "YOUR_OPENAI_KEY" --model "gpt-4o-mini-tts" --voice "marin"
```

### Google Gemini
```bash
agents-voice config --provider gemini --key "YOUR_GEMINI_KEY" --model "gemini-2.5-flash-preview-tts" --voice "Kore"
```

### ElevenLabs
```bash
agents-voice config --provider elevenlabs --key "YOUR_ELEVENLABS_KEY" --voice "JBFqnCBsd6RMkjVDRZzb"
```

### Custom / Local Endpoint (e.g. Kokoro, LocalAI)
```bash
agents-voice config --provider custom --base-url "http://127.0.0.1:8880/v1" --voice "af_heart"
```

---

## MCP Server Setup

Add to your MCP configuration (e.g. `~/.cursor/mcp.json`, `~/.agents/mcp.json`, or Claude Desktop config):

```json
{
  "mcpServers": {
    "agents-voice": {
      "command": "python",
      "args": ["-m", "agents_voice", "serve"]
    }
  }
}
```

---

## MCP Tools

| Tool | Description |
| :--- | :--- |
| `voice_speak(message, provider?, model?, voice?)` | Synthesizes and plays a concise 1–2 sentence spoken summary directly to the user. |
| `voice_stop()` | Immediately terminates any currently playing speech audio. |
| `voice_status()` | Reports backend status, configured providers, active voice, and bridge availability. |

---

## CLI Reference

| Command | Description |
| :--- | :--- |
| `agents-voice speak "Text to speak"` | Speaks text directly via the active provider. |
| `agents-voice speak --wait "Text"` | Speaks text and waits until playback finishes. |
| `agents-voice test` | Plays a quick test speech sample to verify audio output. |
| `agents-voice stop` | Cuts off any running audio playback immediately. |
| `agents-voice status` | Prints active provider configuration and status JSON. |
| `agents-voice config [options]` | Updates provider, model, voice, speed, region, or API keys. |
| `agents-voice serve` | Runs the FastMCP server via stdio transport. |

---

## License

MIT License. See [LICENSE](LICENSE) for details.

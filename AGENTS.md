# AGENTS.md — agents-voice Developer Guidelines

## Architecture Principles
- **Mouth for Coding Agents**: Direct speech output MCP server and CLI for AI coding agents (Antigravity, Cursor, Zed, agents-harness).
- **Separation of Concerns**: Diffs, code, and file listings belong on screen in markdown. Voice is exclusively for concise, natural 1-2 sentence spoken summaries (`voice_speak`).
- **Zero Heavy Dependencies**: Pure Python standard library (`urllib.request`, `winsound` on Windows) + `mcp>=1.0.0,<2`. No ffmpeg, no Pygame, no heavy C libraries.
- **Standalone with HUD Synergy**: Plays directly through OS audio when standalone. If Dumbo desktop overlay is running (`127.0.0.1:12480`), optionally routes through Dumbo's Veadio HUD for synchronized word highlighting.
- **Local Configuration**: Stored in `~/.agents/voice.json` with fallback discovery from environment and existing Dumbo settings.

## Commands
- Test status: `python -m agents_voice status`
- Configure: `python -m agents_voice config --key <key> --region westeurope --voice de-DE-SeraphinaMultilingualNeural`
- Speak phrase: `python -m agents_voice speak "Hallo Felix"`
- Test audio: `python -m agents_voice test`
- Stop playback: `python -m agents_voice stop`
- Start FastMCP: `python -m agents_voice serve`

## Tools
- `voice_speak(message: str)`: Synthesize and play 1-2 sentences spoken summary.
- `voice_stop()`: Immediate audio cutoff.
- `voice_status()`: Report readiness, provider, and bridge state.

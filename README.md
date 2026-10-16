# agents-voice

> Fast, minimal speech output MCP server and CLI for AI coding agents.

## Overview
`agents-voice` equips AI coding agents (Antigravity, Cursor, Zed, agents-harness) with a native voice tool (`voice_speak`). Instead of reading huge code diffs or screen-scraping text, the agent formulates a concise, natural spoken summary (1–2 sentences) directly to the developer's ears.

## Installation
```bash
pip install -e .
```

## Configuration
Credentials are saved to `~/.agents/voice.json`:
```bash
python -m agents_voice config --key "YOUR_AZURE_KEY" --region "westeurope" --voice "de-DE-SeraphinaMultilingualNeural"
```
If you already configured Azure in Dumbo, `agents-voice` automatically detects and uses it.

## MCP Server Setup
Add to `~/.cursor/mcp.json` or `~/.agents/mcp.json`:
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

## License
MIT

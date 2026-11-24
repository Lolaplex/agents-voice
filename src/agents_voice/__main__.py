"""CLI entry point for agents-voice."""

from __future__ import annotations

import argparse
import json

from . import __version__
from .config import save_config
from .engine import speak, stop
from .mcp_server import serve, voice_status

CLASSIFICATION = {
    "field": "side_effects",
    "enum": ["read-only", "mutating"],
    "boolean_field": "mutates",
    "annotation": "annotations.readOnlyHint",
    "missing": "mutating",
    "description": (
        "Read commands[name].side_effects. "
        "Missing side_effects metadata means mutating. "
        "Do not infer the class from the command name. "
        "host_local marks commands that drive this host's audio device, "
        "hotkeys, inbox spool, or host config."
    ),
}


def _cmd(
    usage: str,
    description: str,
    side_effects: str,
    *,
    host_local: bool,
    parameters: dict | None = None,
) -> dict:
    read_only = side_effects == "read-only"
    spec = {
        "usage": usage,
        "description": description,
        "side_effects": side_effects,
        "mutates": not read_only,
        "annotations": {
            "readOnlyHint": read_only,
            "destructiveHint": not read_only,
            "idempotentHint": read_only,
            "openWorldHint": False,
        },
        "host_local": host_local,
    }
    if parameters:
        spec["parameters"] = parameters
    return spec


def _obj(props: dict, required: list | None = None) -> dict:
    out = {"type": "object", "properties": props}
    if required:
        out["required"] = required
    return out


def help_json() -> dict:
    s = {"type": "string"}
    b = {"type": "boolean"}
    return {
        "name": "agents-voice",
        "version": __version__,
        "cordis_expose": True,
        "description": "Multi-provider speech output MCP server and CLI for AI coding agents.",
        "classification": CLASSIFICATION,
        "commands": {
            "serve": _cmd(
                "agents-voice serve",
                "Run the FastMCP server via stdio transport",
                "mutating",
                host_local=True,
            ),
            "speak": _cmd(
                "agents-voice speak TEXT [--wait] [--provider P] [--model M] [--voice V]",
                "Speak text directly through the host audio device",
                "mutating",
                host_local=True,
                parameters=_obj(
                    {
                        "text": {**s, "description": "The text to speak"},
                        "wait": {**b, "description": "Wait until audio finishes playing"},
                        "provider": {**s, "description": "Provider override (openrouter, openai, gemini, elevenlabs, azure, custom)"},
                        "model": {**s, "description": "Model override"},
                        "voice": {**s, "description": "Voice override"},
                    },
                    ["text"],
                ),
            ),
            "stop": _cmd(
                "agents-voice stop",
                "Stop currently playing audio on the host",
                "mutating",
                host_local=True,
            ),
            "status": _cmd(
                "agents-voice status",
                "Show current voice configuration and backend status",
                "read-only",
                host_local=True,
            ),
            "play": _cmd(
                "agents-voice play",
                "Play the latest voice message stored in the mailbox on the host",
                "mutating",
                host_local=True,
            ),
            "test": _cmd(
                "agents-voice test",
                "Play a quick test speech sample on the host",
                "mutating",
                host_local=True,
            ),
        },
        "flags": ["--help-json"],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agents-voice",
        description="Fast, minimal multi-provider speech output MCP server and CLI for AI coding agents.",
    )
    parser.add_argument("--help-json", action="store_true", help="Emit machine-readable CLI spec as JSON.")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to run")

    # serve
    subparsers.add_parser("serve", help="Run the FastMCP server via stdio transport")

    # speak
    speak_p = subparsers.add_parser("speak", help="Speak text directly")
    speak_p.add_argument("text", nargs="+", help="The text to speak")
    speak_p.add_argument("--wait", action="store_true", help="Wait until audio finishes playing")
    speak_p.add_argument("--provider", help="Override provider (openrouter, openai, gemini, elevenlabs, azure, custom)")
    speak_p.add_argument("--model", help="Override model (e.g. openai/gpt-4o-mini-tts, elevenlabs/eleven-v4-turbo)")
    speak_p.add_argument("--voice", help="Override voice (e.g. marin, cedar, Kore, de-DE-Seraphina:DragonHDLatestNeural)")

    # stop
    subparsers.add_parser("stop", help="Stop currently playing audio")

    # status
    subparsers.add_parser("status", help="Show current voice configuration and backend status")

    # config
    config_p = subparsers.add_parser("config", help="Configure voice provider, model, voice, and credentials")
    config_p.add_argument(
        "--provider",
        help="Voice provider: openrouter | openai | gemini | elevenlabs | azure | custom",
    )
    config_p.add_argument("--key", help="API key for the active provider")
    config_p.add_argument(
        "--model",
        help="Model ID (e.g. openai/gpt-4o-mini-tts, elevenlabs/eleven-v4-turbo, gemini-2.5-flash-preview-tts)",
    )
    config_p.add_argument(
        "--voice",
        help="Voice ID/name (e.g. marin, cedar, coral, Kore, de-DE-Seraphina:DragonHDLatestNeural)",
    )
    config_p.add_argument("--region", help="Azure Speech region (e.g. swedencentral)")
    config_p.add_argument("--base-url", dest="base_url", help="Custom OpenAI-compatible base URL")
    config_p.add_argument("--instructions", help="Tone/style instructions for steerable TTS models")
    config_p.add_argument("--speed", type=float, help="Speech rate multiplier (e.g. 1.0)")
    config_p.add_argument(
        "--mode",
        choices=["inbox", "direct"],
        help="Delivery mode: 'inbox' (silent + chime + hotkey play) or 'direct' (speak immediately)",
    )
    config_p.add_argument("--hotkey", help="Global Windows shortcut to play latest message (e.g. alt+v)")
    config_p.add_argument(
        "--chime",
        type=str.lower,
        choices=["true", "false"],
        help="Enable/disable chime when new message arrives (true/false)",
    )

    # play (play latest message)
    subparsers.add_parser("play", help="Play the latest voice message stored in the mailbox")

    # listen (run background hotkey daemon)
    subparsers.add_parser("listen", help="Run background hotkey daemon listening for global shortcut")

    # test
    subparsers.add_parser("test", help="Play a quick test speech sample")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.help_json:
        print(json.dumps(help_json(), indent=2))
        return

    if args.subcommand == "serve":
        serve()
    elif args.subcommand == "speak":
        text = " ".join(args.text)
        res = speak(
            text,
            wait=args.wait,
            provider=args.provider,
            model=args.model,
            voice=args.voice,
        )
        print(res)
    elif args.subcommand == "play":
        from .inbox import play_latest

        res = play_latest(wait=True)
        print(res)
    elif args.subcommand == "listen":
        from .config import load_config
        from .hotkey import ensure_hotkey_listener
        import time

        cfg = load_config()
        print(f"agents-voice lauscht auf globalen Hotkey [{cfg.hotkey.upper()}]...")
        ensure_hotkey_listener(cfg.hotkey)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nBeendet.")
    elif args.subcommand == "stop":
        res = stop()
        print(res)
    elif args.subcommand == "status":
        print(voice_status())
    elif args.subcommand == "config":
        cfg = save_config(
            provider=args.provider,
            key=args.key,
            model=args.model,
            voice=args.voice,
            azure_region=args.region,
            base_url=args.base_url,
            instructions=args.instructions,
            speed=args.speed,
            mode=args.mode,
            hotkey=args.hotkey,
            chime=args.chime == "true" if args.chime is not None else None,
        )
        print(
            f"Konfiguration gespeichert: Provider={cfg.provider}, "
            f"Model={cfg.model}, Voice={cfg.voice}, Mode={cfg.mode}, Hotkey={cfg.hotkey}"
        )
    elif args.subcommand == "test":
        print("Spreche Testphrase...")
        res = speak("agents-voice ist bereit.", wait=True)
        print(res)
    else:
        serve()


if __name__ == "__main__":
    main()

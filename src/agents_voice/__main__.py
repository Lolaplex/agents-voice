"""CLI entry point for agents-voice."""

from __future__ import annotations

import argparse

from .config import save_config
from .engine import speak, stop
from .mcp_server import serve, voice_status


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agents-voice",
        description="Fast, minimal multi-provider speech output MCP server and CLI for AI coding agents.",
    )
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
        type=lambda v: str(v).lower() in ("1", "true", "yes", "on"),
        help="Enable/disable chime when new message arrives (true/false)",
    )

    # play (play latest message)
    subparsers.add_parser("play", help="Play the latest voice message stored in the mailbox")

    # listen (run background hotkey daemon)
    subparsers.add_parser("listen", help="Run background hotkey daemon listening for global shortcut")

    # test
    subparsers.add_parser("test", help="Play a quick test speech sample")

    args = parser.parse_args()

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
            chime=args.chime,
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

"""CLI entry point for agents-voice."""

from __future__ import annotations

import argparse
import sys

from .config import load_config, save_config
from .engine import speak, stop
from .mcp_server import serve, voice_status


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agents-voice",
        description="Fast, minimal speech output MCP server and CLI for AI coding agents.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to run")

    # serve
    subparsers.add_parser("serve", help="Run the FastMCP server via stdio transport")

    # speak
    speak_p = subparsers.add_parser("speak", help="Speak text directly")
    speak_p.add_argument("text", nargs="+", help="The text to speak")
    speak_p.add_argument("--wait", action="store_true", help="Wait until audio finishes playing")

    # stop
    subparsers.add_parser("stop", help="Stop currently playing audio")

    # status
    subparsers.add_parser("status", help="Show current voice configuration and backend status")

    # config
    config_p = subparsers.add_parser("config", help="Configure voice credentials and settings")
    config_p.add_argument("--key", help="Azure Speech subscription key")
    config_p.add_argument("--region", help="Azure Speech region (e.g. westeurope)")
    config_p.add_argument("--voice", help="Neural voice name (e.g. de-DE-SeraphinaMultilingualNeural)")
    config_p.add_argument("--speed", type=float, help="Speech rate multiplier (e.g. 1.05)")
    config_p.add_argument("--provider", help="Voice provider (azure)")

    # test
    subparsers.add_parser("test", help="Play a quick test speech sample")

    args = parser.parse_args()

    if args.subcommand == "serve":
        serve()
    elif args.subcommand == "speak":
        text = " ".join(args.text)
        res = speak(text, wait=args.wait)
        print(res)
    elif args.subcommand == "stop":
        res = stop()
        print(res)
    elif args.subcommand == "status":
        print(voice_status())
    elif args.subcommand == "config":
        cfg = save_config(
            provider=args.provider,
            azure_key=args.key,
            azure_region=args.region,
            voice=args.voice,
            speed=args.speed,
        )
        print(f"Konfiguration gespeichert: Provider={cfg.provider}, Region={cfg.azure_region}, Voice={cfg.voice}")
    elif args.subcommand == "test":
        print("Spreche Testphrase...")
        res = speak("Hallo Felix! agents-voice ist bereit.", wait=True)
        print(res)
    else:
        # Default to serve if no subcommand provided (standard for MCP invocations)
        serve()


if __name__ == "__main__":
    main()

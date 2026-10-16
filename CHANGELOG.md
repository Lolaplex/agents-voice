# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.1] - 2026-10-16

### Added
- FastMCP stdio server exposing `voice_speak`, `voice_stop`, and `voice_status` tools.
- Multi-provider TTS backend supporting Azure Speech, OpenRouter (pcm16 streaming), OpenAI, Gemini 2.5, ElevenLabs, and custom OpenAI-compatible endpoints.
- Lightweight standalone audio playback for Windows (WAV & MP3 via MCI/winsound) and macOS/Linux.
- Seamless bridge integration with Dumbo desktop overlay when present.
- Command-line interface (`agents-voice`) for speaking, configuration, testing, status, and MCP serving.

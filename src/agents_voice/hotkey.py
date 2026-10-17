"""System-wide background hotkey daemon for agents-voice."""

from __future__ import annotations

import ctypes
import os
import platform
import sys
import threading
import time
from typing import Callable, Optional

from .inbox import play_latest

_IS_WINDOWS = platform.system() == "Windows"


class HotkeyListener:
    """Windows global hotkey listener for playback of the latest voice message."""

    def __init__(
        self,
        key_char: str = "v",
        modifiers: str = "alt",
        on_trigger: Optional[Callable[[], None]] = None,
    ) -> None:
        self.key_char = key_char.upper()
        self.modifiers_str = modifiers.lower()
        self.on_trigger = on_trigger or (lambda: play_latest(wait=False))
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _parse_modifiers(self) -> int:
        MOD_ALT = 0x0001
        MOD_CONTROL = 0x0002
        MOD_SHIFT = 0x0004
        MOD_WIN = 0x0008
        MOD_NOREPEAT = 0x4000

        flags = MOD_NOREPEAT
        if "alt" in self.modifiers_str:
            flags |= MOD_ALT
        if "ctrl" in self.modifiers_str or "control" in self.modifiers_str:
            flags |= MOD_CONTROL
        if "shift" in self.modifiers_str:
            flags |= MOD_SHIFT
        if "win" in self.modifiers_str:
            flags |= MOD_WIN
        return flags

    def _vk_code(self) -> int:
        if len(self.key_char) == 1 and self.key_char.isalnum():
            return ord(self.key_char)
        return 0x56  # 'V' by default

    def _run_loop(self) -> None:
        if not _IS_WINDOWS:
            return

        user32 = ctypes.windll.user32
        HOTKEY_ID = 42801

        mod_flags = self._parse_modifiers()
        vk = self._vk_code()

        success = user32.RegisterHotKey(None, HOTKEY_ID, mod_flags, vk)
        if not success:
            return

        try:
            msg = ctypes.wintypes.MSG()
            while self._running:
                # PeekMessage with PM_REMOVE allows non-blocking checking
                if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    if msg.message == 0x0312:  # WM_HOTKEY
                        if msg.wParam == HOTKEY_ID:
                            try:
                                self.on_trigger()
                            except Exception:
                                pass
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                else:
                    time.sleep(0.05)
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)

    def start(self) -> None:
        """Starts the hotkey listener in a daemon background thread."""
        if not _IS_WINDOWS or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="agents-voice-hotkey")
        self._thread.start()

    def stop(self) -> None:
        """Stops the hotkey listener."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)


_GLOBAL_LISTENER: Optional[HotkeyListener] = None


def ensure_hotkey_listener(hotkey: str = "alt+v") -> None:
    """Ensures a global hotkey listener is active."""
    global _GLOBAL_LISTENER
    if _GLOBAL_LISTENER and _GLOBAL_LISTENER._running:
        return

    parts = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
    key_char = parts[-1] if parts else "v"
    mods = "+".join(parts[:-1]) if len(parts) > 1 else "alt"

    _GLOBAL_LISTENER = HotkeyListener(key_char=key_char, modifiers=mods)
    _GLOBAL_LISTENER.start()

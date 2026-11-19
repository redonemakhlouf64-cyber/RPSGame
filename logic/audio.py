"""Audio playback with a Termux-friendly fallback chain.

Kivy's SDL audio can block forever when a desktop-style Termux/X11 session
has no usable sound device, so the Kivy backend is probed in a throwaway
subprocess.  Until it is proven safe, playback goes through
``termux-media-player`` (installed with Termux:API) or is skipped.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time

from config import CHARACTERS_BY_ID
from logic import assets_gen

try:  # Kivy may not exist in headless mode
    from kivy.core.audio import SoundLoader
    _HAS_KIVY = True
except Exception:  # pragma: no cover
    SoundLoader = None
    _HAS_KIVY = False

_PROBE = """
import sys
try:
    from kivy.core.audio import SoundLoader
    s = SoundLoader.load(sys.argv[1])
    print('AUDIO_OK' if s is not None else 'AUDIO_NONE', flush=True)
except Exception as exc:
    print('AUDIO_FAIL', exc, flush=True)
"""


class AudioManager:
    def __init__(self, store):
        self.store = store
        self._cache = {}
        self._backend = "none"
        self._lock = threading.RLock()
        self._termux = shutil.which("termux-media-player")
        self._no_audio = os.environ.get("RPS_NO_AUDIO") == "1"
        self._loading = False
        self._last_play = {}
        assets_gen.ensure_sounds()
        if self._termux:
            self._backend = "termux"

    @property
    def backend(self):
        return self._backend

    def preload(self):
        """Start backend probing/loading in the background (never blocks UI)."""
        if self._no_audio or not _HAS_KIVY or self._loading:
            return
        self._loading = True
        threading.Thread(target=self._load_async, daemon=True).start()

    def _load_async(self):
        path = assets_gen.sound_path("click")
        on_android = bool(os.environ.get("ANDROID_ARGUMENT") or
                          os.environ.get("P4A_BOOTSTRAP"))
        if os.environ.get("RPS_AUDIO") != "kivy" and not on_android:
            try:
                env = dict(os.environ)
                env["KIVY_NO_ARGS"] = "1"
                env["KIVY_NO_CONSOLELOG"] = "1"
                proc = subprocess.run(
                    [sys.executable, "-c", _PROBE, path],
                    capture_output=True, text=True, timeout=6,
                    env=env,
                )
                if "AUDIO_OK" not in (proc.stdout or ""):
                    return
            except Exception:
                return
        # Probe succeeded: load the rest in this worker thread.
        for name in assets_gen.SOUND_FILES:
            try:
                snd = SoundLoader.load(assets_gen.sound_path(name))
                if snd is not None:
                    snd.volume = 0.9
                    with self._lock:
                        self._cache[name] = snd
            except Exception:
                continue
        with self._lock:
            if self._cache:
                self._backend = "kivy"

    def enabled(self) -> bool:
        try:
            return bool(self.store.get("sound", True))
        except Exception:
            return True

    def play(self, name: str, volume: float = 0.9):
        if self._no_audio or not self.enabled():
            return
        path = assets_gen.sound_path(name)
        if not os.path.exists(path):
            return
        with self._lock:
            snd = self._cache.get(name)
        if snd is not None:
            try:
                snd.volume = max(0.05, min(1.0, volume))
                snd.stop()
                snd.play()
                return
            except Exception:
                pass
        if self._termux:
            now = time.monotonic()
            last = self._last_play.get(name, 0.0)
            if now - last < 0.10:
                return
            self._last_play[name] = now
            try:
                subprocess.Popen(
                    [self._termux, "play", path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass

    # semantic helpers ------------------------------------------------------
    def click(self):
        self.play("click", 0.55)

    def tick(self):
        self.play("tick", 0.7)

    def whoosh(self):
        self.play("whoosh", 0.7)

    def smack(self):
        self.play("smack", 1.0)

    def win(self):
        self.play("win", 0.85)

    def lose(self):
        self.play("lose", 0.85)

    def scream(self, char_id: str):
        if char_id in CHARACTERS_BY_ID or char_id == "robot":
            self.play("scream_" + char_id, 1.0)
        else:
            self.play("scream_amara", 1.0)


AUDIO = None


def init_audio(store):
    global AUDIO
    AUDIO = AudioManager(store)
    AUDIO.preload()
    return AUDIO


def get_audio():
    return AUDIO

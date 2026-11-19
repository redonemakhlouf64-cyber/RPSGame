"""Procedural audio + asset generation.

Everything the game needs is synthesised locally: no downloads, no missing
files, no placeholder assets.
"""
from __future__ import annotations

import json
import math
import os
import random
import struct
import wave

from config import ASSETS_DIR, CHARACTERS, SOUND_DIR

SR = 22050


# ------------------------------------------------------------------ helpers --
def _clamp(x: float) -> float:
    return max(-1.0, min(1.0, x))


def _write_wav(path: str, samples) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    frames = bytearray()
    for s in samples:
        frames += struct.pack("<h", int(_clamp(s) * 32000))
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(bytes(frames))


def _env(t: float, dur: float, attack=0.01, release=0.15) -> float:
    if t < 0 or t > dur:
        return 0.0
    a = min(1.0, t / max(0.001, attack))
    r = min(1.0, max(0.0, (dur - t) / max(0.001, release)))
    return a * r


def _bell(t, peak, width):
    return math.exp(-((t - peak) ** 2) / (2 * width * width))


# ----------------------------------------------------------------- screams --
_FORMANTS = {
    "amara": [(720, 1.0, 130), (1240, 0.75, 170), (2700, 0.55, 320)],
    "kenji": [(640, 1.0, 120), (1100, 0.8, 150), (2400, 0.5, 280)],
    "sofia": [(900, 1.0, 160), (1550, 0.8, 200), (3000, 0.6, 350)],
    "malik": [(560, 1.0, 110), (980, 0.7, 140), (2200, 0.45, 260)],
    "mei": [(980, 1.0, 170), (1700, 0.85, 210), (3200, 0.65, 370)],
    "lucas": [(670, 1.0, 125), (1180, 0.7, 160), (2500, 0.5, 300)],
}


def make_scream(char_id: str, base: float, dur: float = 1.15):
    """Formant-synth 'AAAARGH' -- each fighter has a unique voice."""
    rng = random.Random(abs(hash(char_id)) % (2 ** 31))
    formants = _FORMANTS.get(char_id, _FORMANTS["amara"])
    n = int(SR * dur)
    out = [0.0] * n
    phase = 0.0
    breath = 0.0
    tilt = 0.55 + (base / 1800.0) * 0.2
    for i in range(n):
        t = i / SR
        # dramatic pitch contour: rises fast, wobbles, falls at the end
        contour = 1.0 + 0.22 * _bell(t, dur * 0.30, dur * 0.22) - 0.18 * (t / dur) ** 2
        vib = 1.0 + 0.035 * math.sin(2 * math.pi * 5.7 * t)
        f0 = base * contour * vib
        phase += 2 * math.pi * f0 / SR
        sample = 0.0
        for h in range(1, 11):
            hf = f0 * h
            if hf > SR * 0.45:
                break
            amp = 0.0
            for (fc, g, bw) in formants:
                amp += g * math.exp(-((hf - fc) ** 2) / (2 * bw * bw))
            sample += (amp / (h ** tilt)) * math.sin(phase * h)
        # breath / rasp
        breath = 0.82 * breath + 0.18 * (rng.random() * 2 - 1)
        sample += breath * 0.16
        # waveshape for a screaming edge
        sample = math.tanh(sample * 1.8) * 0.55
        env = _env(t, dur, attack=0.035, release=0.22)
        # tremolo / panic
        env *= 0.86 + 0.14 * math.sin(2 * math.pi * 8.3 * t)
        out[i] = sample * env
    peak = max(1e-6, max(abs(x) for x in out))
    return [x / peak * 0.9 for x in out]


# ------------------------------------------------------------------ effects --
def make_smack():
    rng = random.Random(4242)
    dur = 0.26
    n = int(SR * dur)
    out = []
    low = 0.0
    for i in range(n):
        t = i / SR
        noise = rng.random() * 2 - 1
        low = low * 0.72 + noise * 0.28
        thump = math.sin(2 * math.pi * (150 - 60 * t / dur) * t) * math.exp(-t * 26)
        crack = (noise - low) * math.exp(-t * 55) * 0.7
        body = low * math.exp(-t * 16) * 1.2
        out.append(math.tanh((thump * 0.9 + crack + body) * 1.4) * 0.95)
    return out


def make_click(freq=1180.0, dur=0.055):
    n = int(SR * dur)
    return [math.sin(2 * math.pi * freq * (i / SR)) * _env(i / SR, dur, 0.002, 0.04) * 0.4
            for i in range(n)]


def make_whoosh(dur=0.34):
    rng = random.Random(99)
    n = int(SR * dur)
    out = []
    smooth = 0.0
    for i in range(n):
        t = i / SR
        f = 0.08 + 0.5 * math.sin(math.pi * t / dur)
        smooth = smooth * (1 - f) + (rng.random() * 2 - 1) * f
        out.append(smooth * math.sin(math.pi * t / dur) * 0.7)
    return out


def make_win():
    notes = (523.25, 659.25, 783.99, 1046.5)
    out = []
    for idx, f in enumerate(notes):
        dur = 0.16 if idx < 3 else 0.42
        n = int(SR * dur)
        for i in range(n):
            t = i / SR
            e = _env(t, dur, 0.006, dur * 0.7)
            s = (math.sin(2 * math.pi * f * t) * 0.6 +
                 math.sin(2 * math.pi * f * 2 * t) * 0.22 +
                 math.sin(2 * math.pi * f * 3 * t) * 0.1)
            out.append(s * e * 0.5)
    return out


def make_lose():
    notes = (392.0, 329.63, 261.63, 196.0)
    out = []
    for f in notes:
        dur = 0.22
        n = int(SR * dur)
        for i in range(n):
            t = i / SR
            e = _env(t, dur, 0.01, dur * 0.6)
            s = math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * f * 2 * t)
            out.append(s * e * 0.4)
    return out


def make_countdown():
    out = []
    for f in (660, 660, 660, 990):
        dur = 0.09
        n = int(SR * dur)
        for i in range(n):
            t = i / SR
            out.append(math.sin(2 * math.pi * f * t) * _env(t, dur, 0.003, 0.06) * 0.35)
    return out


def make_robot_scream():
    """A glitchy machine death-cry (used when the robot gets slapped)."""
    rng = random.Random(777)
    dur = 0.95
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 220 * (1 + 0.55 * math.sin(2 * math.pi * 17 * t)) * (0.7 + 0.5 * (1 - t / dur))
        f = max(60, min(1400, f))
        phase += 2 * math.pi * f / SR
        sq = 1.0 if math.sin(phase) >= 0 else -1.0
        glitch = 1.0 if (int(t * 26) % 5) else 0.25
        noise = rng.random() * 2 - 1
        s = (sq * 0.22 + math.sin(phase * 1.5) * 0.18 + noise * 0.10) * glitch
        out.append(math.tanh(s * 1.5) * _env(t, dur, 0.01, 0.25) * 0.8)
    return out


# --------------------------------------------------------------------- api ---
SOUND_FILES = {
    "click": make_click,
    "tick": make_countdown,
    "whoosh": make_whoosh,
    "smack": make_smack,
    "win": make_win,
    "lose": make_lose,
    "scream_amara": lambda: make_scream("amara", 515),
    "scream_kenji": lambda: make_scream("kenji", 640),
    "scream_sofia": lambda: make_scream("sofia", 720),
    "scream_malik": lambda: make_scream("malik", 425),
    "scream_mei": lambda: make_scream("mei", 780),
    "scream_lucas": lambda: make_scream("lucas", 470),
    "scream_robot": make_robot_scream,
}


def sound_path(name: str) -> str:
    return os.path.join(SOUND_DIR, name + ".wav")


def ensure_sounds(force: bool = False, progress=None) -> dict:
    os.makedirs(SOUND_DIR, exist_ok=True)
    made = {}
    total = len(SOUND_FILES)
    for idx, (name, fn) in enumerate(SOUND_FILES.items()):
        path = sound_path(name)
        if force or not os.path.exists(path) or os.path.getsize(path) < 128:
            try:
                _write_wav(path, fn())
                made[name] = True
            except Exception:
                made[name] = False
        if progress:
            try:
                progress((idx + 1) / total, name)
            except Exception:
                pass
    try:
        with open(os.path.join(ASSETS_DIR, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({
                "version": 1,
                "sounds": sorted(SOUND_FILES.keys()),
                "characters": [c["id"] for c in CHARACTERS],
                "art": "vector-canvas",
            }, fh, indent=2)
    except Exception:
        pass
    return made


def ensure_all(force: bool = False, progress=None) -> dict:
    return ensure_sounds(force=force, progress=progress)

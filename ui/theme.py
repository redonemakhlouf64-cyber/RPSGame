"""Visual identity: palette, scaling, fonts."""
from __future__ import annotations

import functools
import os

from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window

# ---------------------------------------------------------------- palette ----
BG_DEEP = "#080B18"
BG_MID = "#101A33"
BG_SOFT = "#17244A"
CYAN = "#25E6D0"
CYAN_DIM = "#0E8F86"
MAGENTA = "#FF3D8B"
MAGENTA_DIM = "#A51E58"
GOLD = "#FFC940"
WHITE = "#F7FBFF"
MUTED = "#93A4C7"
DARK = "#0B1020"
RED = "#FF4D4D"
GREEN = "#4DFF9A"

COLORS = {
    "bg_deep": BG_DEEP,
    "bg_mid": BG_MID,
    "bg_soft": BG_SOFT,
    "cyan": CYAN,
    "cyan_dim": CYAN_DIM,
    "magenta": MAGENTA,
    "magenta_dim": MAGENTA_DIM,
    "gold": GOLD,
    "white": WHITE,
    "muted": MUTED,
    "dark": DARK,
    "red": RED,
    "green": GREEN,
}


def rgba(value, alpha: float = 1.0):
    """Accept '#RRGGBB', '#RRGGBBAA' or an RGBA tuple."""
    if isinstance(value, (tuple, list)):
        if len(value) == 4:
            return tuple(value)
        return (value[0], value[1], value[2], alpha)
    v = value.strip().lstrip("#")
    if len(v) == 8:
        return tuple(int(v[i:i + 2], 16) / 255.0 for i in (0, 2, 4, 6))
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    r, g, b = (int(v[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (r, g, b, alpha)


def mix(c1, c2, f: float):
    a = rgba(c1)
    b = rgba(c2)
    return tuple(a[i] * (1 - f) + b[i] * f for i in range(4))


# ------------------------------------------------------------------ scale ----
def _compute_scale() -> float:
    try:
        w = max(320.0, float(Window.width or 432))
        h = max(480.0, float(Window.height or 768))
    except Exception:
        w, h = 432.0, 768.0
    return max(0.8, min(4.0, min(w / 432.0, h / 768.0)))


UI_SCALE = _compute_scale()


def U(value: float) -> float:
    """Scale a design-space measurement (based on a 432x768 stage)."""
    return value * UI_SCALE


# ------------------------------------------------------------------ fonts ----
FONT_REGULAR = None
FONT_MAP = {}
_SYSTEM_FONTS = {
    "CJK": "/system/fonts/NotoSansCJK-Regular.ttc",
    "ARABIC": "/system/fonts/NotoNaskhArabic-Regular.ttf",
    "DEVA": "/system/fonts/NotoSansDevanagari-VF.ttf",
    "HEBREW": "/system/fonts/NotoSansHebrew-Regular.ttf",
    "THAI": "/system/fonts/NotoSansThai-Regular.ttf",
}


def _register_fonts():
    global FONT_REGULAR
    for name, path in _SYSTEM_FONTS.items():
        try:
            if os.path.exists(path):
                LabelBase.register(name=f"App{name}", fn_regular=path)
                FONT_MAP[name] = f"App{name}"
        except Exception:
            pass
    # Prefer a system font that ships Latin + CJK for game text on Android.
    for candidate in ("/system/fonts/NotoSansCJK-Regular.ttc",
                      "/system/fonts/RobotoStatic-Regular.ttf",
                      "/system/fonts/Roboto-Regular.ttf"):
        try:
            if os.path.exists(candidate):
                LabelBase.register(name="AppLatin", fn_regular=candidate)
                FONT_REGULAR = "AppLatin"
                break
        except Exception:
            continue


_register_fonts()


def font_for(text: str):
    """Pick a font capable of rendering ``text`` (Kivy has no font fallback)."""
    if not text:
        return FONT_REGULAR
    for ch in text:
        o = ord(ch)
        if 0x4E00 <= o <= 0x9FFF or 0x3040 <= o <= 0x30FF or 0xAC00 <= o <= 0xD7AF:
            return FONT_MAP.get("CJK", FONT_REGULAR)
        if 0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F:
            return FONT_MAP.get("ARABIC", FONT_REGULAR)
        if 0x0900 <= o <= 0x097F:
            return FONT_MAP.get("DEVA", FONT_REGULAR)
    return FONT_REGULAR


def is_rtl(text: str) -> bool:
    return any(0x0590 <= ord(ch) <= 0x08FF for ch in (text or ""))


def canvas_draw(func):
    """Decorator: clear the widget canvas and make it current while drawing.

    Kivy only auto-attaches bare graphics instructions to the canvas that is
    active in a ``with canvas`` block; without it a custom-drawn widget stays
    blank even though its draw code runs.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.canvas.clear()
        with self.canvas:
            result = func(self, *args, **kwargs)
        # Instructions created before the widget is attached to a window can
        # be dropped when its canvas is reparented; one delayed redraw after
        # layout guarantees the art is visible on first show.
        if not getattr(self, "_canvas_ready", False):
            self._canvas_ready = True
            Clock.schedule_once(lambda dt: wrapper(self), 0.05)
        return result

    return wrapper


HAND_SKIN = {
    "base": "#F0B98C",
    "dark": "#C98A5F",
    "light": "#FFD8BA",
    "nail": "#FFE9DC",
    "line": "#8C5538",
}

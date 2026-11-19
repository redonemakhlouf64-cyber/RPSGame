"""Reusable neon UI components drawn entirely with Kivy canvas."""
from __future__ import annotations

import math
import random

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import (Color as GColor, Ellipse, Line, PopMatrix, PushMatrix,
                           Rectangle, Rotate, RoundedRectangle, Triangle)
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             StringProperty)
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from ui.theme import (BG_DEEP, BG_MID, CYAN, DARK, GOLD, MAGENTA, MUTED,
                      WHITE, U, canvas_draw, font_for, rgba)


class Text(Label):
    """Label that automatically loads a font with glyphs for its script."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(text=self._fix_font)
        self._fix_font()

    def _fix_font(self, *args):
        try:
            f = font_for(self.text)
            if f:
                self.font_name = f
        except Exception:
            pass


def label(text="", size=16, color=WHITE, **kwargs):
    kwargs.setdefault("halign", "center")
    kwargs.setdefault("valign", "middle")
    kwargs.setdefault("markup", False)
    kwargs.setdefault("font_size", U(size))
    kwargs.setdefault("color", rgba(color))
    kwargs.setdefault("font_name", font_for(text) or "Roboto")
    lbl = Text(text=text, **kwargs)
    return lbl


def set_label(lbl: Label, text: str):
    lbl.text = text
    f = font_for(text)
    if f:
        lbl.font_name = f


class GradientBG(Widget):
    """Layered animated-feeling background with neon depth."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw)
        self._phase = 0.0

    def _tick(self, dt):
        self._phase += dt * 0.35
        self._draw()

    @canvas_draw
    def _draw(self, *args):
        self.canvas.clear()
        w, h = self.size
        if w < 2 or h < 2:
            return
        steps = 46
        for i in range(steps):
            f = i / max(1, steps - 1)
            r = 0.035 + 0.055 * f
            g = 0.050 + 0.075 * f
            b = 0.115 + 0.140 * f
            GColor(r, g, b, 1)
            Rectangle(pos=(self.x, self.y + h * (1 - (i + 1) / steps)),
                      size=(w, h / steps + 1))
        # neon orbs
        ph = self._phase
        cx = self.x + w * (0.22 + 0.05 * math.sin(ph * 0.7))
        cy = self.y + h * (0.82 + 0.03 * math.cos(ph * 0.9))
        GColor(*rgba(CYAN, 0.10))
        Ellipse(pos=(cx - w * 0.52, cy - w * 0.52), size=(w * 1.04, w * 1.04))
        GColor(*rgba(CYAN, 0.06))
        Ellipse(pos=(cx - w * 0.30, cy - w * 0.30), size=(w * 0.60, w * 0.60))
        GColor(*rgba(MAGENTA, 0.09))
        Ellipse(pos=(self.x + w * 0.50, self.y + h * 0.12), size=(w * 0.9, w * 0.9))
        GColor(*rgba(MAGENTA, 0.05))
        Ellipse(pos=(self.x + w * 0.64, self.y + h * 0.22), size=(w * 0.55, w * 0.55))
        # subtle vignette bars
        GColor(0, 0, 0, 0.20)
        Rectangle(pos=(self.x, self.y), size=(w, h * 0.16))
        GColor(0, 0, 0, 0.10)
        Rectangle(pos=(self.x, self.y + h * 0.84), size=(w, h * 0.16))


class PillButton(Button):
    """Rounded neon button with a shadow, glow and press feedback."""

    bg_color = ListProperty(rgba(CYAN))
    text_color = ListProperty(rgba(DARK))
    border_color = ListProperty(rgba("#FFFFFF", 0.0))
    glow = BooleanProperty(False)
    radius = NumericProperty(0)
    pulse = NumericProperty(0.0)

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("font_size", U(17))
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (U(240), U(56)))
        super().__init__(**kwargs)
        self.color = self.text_color
        if font_for(self.text):
            self.font_name = font_for(self.text)
        r = U(16)
        if self.radius:
            r = U(self.radius)
        with self.canvas.before:
            self._shadow_c = GColor(0, 0, 0, 0.45)
            self._shadow = RoundedRectangle(radius=[r])
            self._glow_c = GColor(*rgba(CYAN, 0.0))
            self._glow_r = RoundedRectangle(radius=[r])
            self._bg_c = GColor(*self.bg_color)
            self._bg = RoundedRectangle(radius=[r])
            self._hi_c = GColor(1, 1, 1, 0.13)
            self._hi = RoundedRectangle(radius=[r])
            self._border_c = GColor(*self.border_color)
            self._border = Line(width=max(1.0, U(1.2)))
        self.bind(pos=self._sync, size=self._sync, state=self._sync,
                  bg_color=self._sync, text_color=self._sync,
                  border_color=self._sync, disabled=self._sync,
                  pulse=self._sync, text=self._fix_text)
        self._sync()

    def _fix_text(self, *a):
        f = font_for(self.text)
        if f:
            self.font_name = f
        self.color = self.text_color

    def _sync(self, *args):
        if not hasattr(self, "_bg"):
            return
        x, y = self.pos
        w, h = self.size
        r = min(h / 2.0, U(self.radius) if self.radius else h / 2.0)
        pad = U(3)
        pressed = self.state == "down"
        self._shadow.pos = (x - U(1), y - U(5 if not pressed else 2))
        self._shadow.size = (w + U(2), h + U(2))
        self._glow_r.pos = (x - U(6), y - U(6))
        self._glow_r.size = (w + U(12), h + U(12))
        self._glow_c.a = ((0.30 if self.glow else 0.0) + 0.30 * self.pulse) if not pressed else 0.5
        col = self.bg_color
        if pressed:
            col = (col[0] * 0.75, col[1] * 0.75, col[2] * 0.75, col[3])
        if self.disabled:
            col = (col[0] * 0.45, col[1] * 0.45, col[2] * 0.45, col[3])
        self._bg_c.rgba = col
        self._bg.pos = (x, y)
        self._bg.size = (w, h)
        self._hi.pos = (x + pad, y + h * 0.52)
        self._hi.size = (w - pad * 2, h * 0.40)
        self._hi_c.a = 0.12 if not pressed else 0.04
        self._border_c.rgba = self.border_color
        self._border.rounded_rectangle = (x, y, w, h, r)
        self.opacity = 0.55 if self.disabled else 1.0
        self.color = self.text_color


class Chip(PillButton):
    def __init__(self, **kwargs):
        kwargs.setdefault("size", (U(90), U(36)))
        kwargs.setdefault("font_size", U(13))
        kwargs.setdefault("radius", 18)
        super().__init__(**kwargs)


class Card(FloatLayout):
    fill = ListProperty(rgba("#FFFFFF", 0.06))
    border_color = ListProperty(rgba(CYAN, 0.22))
    radius = NumericProperty(20)
    glow = NumericProperty(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._shadow_c = GColor(0, 0, 0, 0.35)
            self._shadow = RoundedRectangle(radius=[U(24)])
            self._glow_c = GColor(*rgba(CYAN, 0.0))
            self._glow_r = RoundedRectangle(radius=[U(24)])
            self._fill_c = GColor(*self.fill)
            self._fill_r = RoundedRectangle(radius=[U(20)])
            self._line_c = GColor(*self.border_color)
            self._line = Line(width=max(1.0, U(1.1)))
        self.bind(pos=self._sync, size=self._sync, fill=self._sync,
                  border_color=self._sync, glow=self._sync)
        self._sync()

    def _sync(self, *a):
        if not hasattr(self, "_fill_r"):
            return
        x, y = self.pos
        w, h = self.size
        r = U(self.radius)
        self._shadow.pos = (x + U(2), y - U(4))
        self._shadow.size = (w, h)
        self._glow_r.pos = (x - U(4), y - U(4))
        self._glow_r.size = (w + U(8), h + U(8))
        self._glow_c.rgba = rgba(CYAN, 0.26 * self.glow)
        self._fill_c.rgba = self.fill
        self._fill_r.pos = (x, y)
        self._fill_r.size = (w, h)
        self._line_c.rgba = self.border_color
        self._line.rounded_rectangle = (x, y, w, h, r)


class TopBar(FloatLayout):
    def __init__(self, title="", back=None, right_text="", **kwargs):
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", U(52))
        super().__init__(**kwargs)
        self.back_cb = back
        self.btn = PillButton(text="<", size=(U(40), U(38)),
                              bg_color=rgba("#FFFFFF", 0.08),
                              text_color=rgba(WHITE),
                              border_color=rgba("#FFFFFF", 0.12),
                              radius=14, font_size=U(18))
        self.btn.pos_hint = {"x": 0.02, "center_y": 0.5}
        self.btn.bind(on_release=self._on_back)
        self.add_widget(self.btn)
        self.title = label(title, size=12, color=MUTED)
        self.title.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.add_widget(self.title)
        self.right_lbl = label(right_text, size=12, color=CYAN)
        self.right_lbl.pos_hint = {"right": 0.97, "center_y": 0.5}
        self.add_widget(self.right_lbl)

    def _on_back(self, *a):
        if self.back_cb:
            self.back_cb()

    def set_title(self, text):
        set_label(self.title, text)


class Spinner(Widget):
    active = BooleanProperty(False)
    angle = NumericProperty(0)
    tint = ListProperty(rgba(CYAN))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw, active=self._draw)
        self._draw()
        Clock.schedule_interval(self._tick, 1 / 30.0)

    def _tick(self, dt):
        if not self.active:
            return
        self.angle = (self.angle + dt * 330) % 360
        self._draw()

    @canvas_draw
    def _draw(self, *a):
        self.canvas.clear()
        if not self.active or self.width < 4:
            return
        cx = self.center_x
        cy = self.center_y
        r = min(self.width, self.height) * 0.38
        GColor(*self.tint)
        for i in range(10):
            frac = i / 10.0
            a = math.radians(self.angle + i * 36)
            alpha = 0.15 + 0.85 * frac
            GColor(self.tint[0], self.tint[1], self.tint[2], alpha)
            rad = 3 + 5 * frac
            Ellipse(pos=(cx + math.cos(a) * r - rad, cy + math.sin(a) * r - rad),
                    size=(rad * 2, rad * 2))


class ScorePips(Widget):
    score = NumericProperty(0)
    target = NumericProperty(3)
    tint = ListProperty(rgba(CYAN))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw, score=self._draw,
                  target=self._draw, tint=self._draw)
        self._draw()

    @canvas_draw
    def _draw(self, *a):
        self.canvas.clear()
        if self.width < 4:
            return
        n = max(1, int(self.target))
        gap = self.width / (n + 0.35)
        r = min(self.height * 0.30, gap * 0.30)
        y = self.center_y
        for i in range(n):
            x = self.x + gap * (i + 0.68)
            if i < self.score:
                GColor(*self.tint)
                Ellipse(pos=(x - r, y - r), size=(r * 2, r * 2))
            else:
                GColor(*rgba(self.tint, 0.18))
                Ellipse(pos=(x - r, y - r), size=(r * 2, r * 2))
                GColor(*rgba(self.tint, 0.55))
                Line(circle=(x, y, r), width=max(1.0, U(1.3)))


class Toast(FloatLayout):
    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("opacity", 0)
        super().__init__(**kwargs)
        with self.canvas.before:
            self._c = GColor(*rgba("#0A1122", 0.95))
            self._bg = RoundedRectangle(radius=[U(14)])
            self._lc = GColor(*rgba(CYAN, 0.45))
            self._line = Line(width=max(1.0, U(1.2)))
        self.lbl = label("", size=13, color=WHITE)
        self.add_widget(self.lbl)
        self.bind(pos=self._sync, size=self._sync)
        self._hide_ev = None

    def _sync(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, U(14))
        self.lbl.size = self.size
        self.lbl.pos = self.pos

    def show_toast(self, text, duration=2.2):
        set_label(self.lbl, text)
        if self._hide_ev:
            self._hide_ev.cancel()
        Animation.cancel_all(self)
        self.opacity = 0
        Animation(opacity=1, d=0.16).start(self)
        self._hide_ev = Clock.schedule_once(lambda dt: Animation(
            opacity=0, d=0.25).start(self), duration)


class Divider(Widget):
    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", 1)
        super().__init__(**kwargs)
        with self.canvas:
            self._c = GColor(*rgba("#FFFFFF", 0.10))
            self._r = Rectangle()
        self.bind(pos=self._sync, size=self._sync)
        self._sync()

    def _sync(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size


class CatIcon(Widget):
    """Small cat face used for the joke language, no emoji font needed."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    @canvas_draw
    def _draw(self, *a):
        self.canvas.clear()
        s = min(self.width, self.height)
        if s < 6:
            return
        cx, cy = self.center
        col = rgba("#FFC940")
        GColor(*col)
        Triangle(points=[cx - s * .32, cy + s * .16, cx - s * .24, cy + s * .48,
                         cx - s * .02, cy + s * .26])
        Triangle(points=[cx + s * .32, cy + s * .16, cx + s * .24, cy + s * .48,
                         cx + s * .02, cy + s * .26])
        Ellipse(pos=(cx - s * .34, cy - s * .34), size=(s * .68, s * .62))
        GColor(0, 0, 0, 0.9)
        Ellipse(pos=(cx - s * .18, cy), size=(s * .07, s * .10))
        Ellipse(pos=(cx + s * .11, cy), size=(s * .07, s * .10))
        GColor(*rgba("#FF8A9E"))
        Triangle(points=[cx, cy - s * .04, cx - s * .05, cy - s * .10,
                         cx + s * .05, cy - s * .10])
        GColor(0, 0, 0, 0.5)
        Line(points=[cx - s * .30, cy - s * .02, cx - s * .12, cy - s * .06],
             width=max(1.0, U(1)))
        Line(points=[cx + s * .30, cy - s * .02, cx + s * .12, cy - s * .06],
             width=max(1.0, U(1)))


class RobotIcon(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    @canvas_draw
    def _draw(self, *a):
        self.canvas.clear()
        s = min(self.width, self.height)
        if s < 8:
            return
        cx, cy = self.center
        GColor(*rgba(CYAN, 0.22))
        Ellipse(pos=(cx - s * .46, cy - s * .46), size=(s * .92, s * .92))
        GColor(*rgba(CYAN))
        Line(points=[cx, cy + s * .26, cx, cy + s * .38], width=max(1.4, U(2)))
        Ellipse(pos=(cx - s * .04, cy + s * .36), size=(s * .08, s * .08))
        GColor(*rgba("#152B4A"))
        RoundedRectangle(pos=(cx - s * .30, cy - s * .22), size=(s * .60, s * .46),
                         radius=[s * .12])
        GColor(*rgba(CYAN))
        Line(rounded_rectangle=(cx - s * .30, cy - s * .22, s * .60, s * .46, s * .12),
             width=max(1.2, U(1.6)))
        GColor(*rgba(CYAN))
        Ellipse(pos=(cx - s * .17, cy + s * .02), size=(s * .10, s * .10))
        Ellipse(pos=(cx + s * .07, cy + s * .02), size=(s * .10, s * .10))
        GColor(*rgba("#FFFFFF", 0.8))
        for mx in (cx - s * .16, cx + s * .08):
            Rectangle(pos=(mx, cy + s * .06), size=(s * .08, s * .012))
        GColor(*rgba(CYAN, 0.9))
        Line(points=[cx - s * .12, cy - s * .12, cx - s * .04, cy - s * .12,
                     cx + s * .04, cy - s * .12, cx + s * .12, cy - s * .12],
             width=max(1.4, U(2)))


class DuelIcon(Widget):
    """Two rivals facing off with a spark of rivalry between them."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    @canvas_draw
    def _draw(self, *a):
        self.canvas.clear()
        s = min(self.width, self.height)
        if s < 8:
            return
        cx, cy = self.center
        for side, accent in ((-1, CYAN), (1, MAGENTA)):
            hx = cx + side * s * 0.21
            GColor(*rgba(accent, 0.16))
            Ellipse(pos=(hx - s * 0.26, cy - s * 0.26),
                    size=(s * 0.52, s * 0.52))
            GColor(*rgba("#152B4A"))
            Ellipse(pos=(hx - s * 0.20, cy - s * 0.20),
                    size=(s * 0.40, s * 0.40))
            GColor(*rgba(accent))
            Line(circle=(hx, cy, s * 0.20), width=max(1.2, U(1.6)))
            GColor(*rgba("#FFFFFF", 0.92))
            Ellipse(pos=(hx - s * 0.10 + side * s * 0.02, cy + s * 0.02),
                    size=(s * 0.065, s * 0.075))
            Ellipse(pos=(hx + s * 0.035 + side * s * 0.02, cy + s * 0.02),
                    size=(s * 0.065, s * 0.075))
            GColor(*rgba(accent, 0.85))
            Line(points=[hx - s * 0.06, cy - s * 0.075,
                         hx + s * 0.06, cy - s * 0.075],
                 width=max(1.2, U(1.5)))
        GColor(*rgba(GOLD))
        Line(points=[cx, cy + s * 0.30, cx - s * 0.06, cy + s * 0.10,
                     cx + s * 0.05, cy + s * 0.02, cx - s * 0.03, cy - s * 0.20],
             width=max(1.6, U(2.2)), joint="round")


class Confetti(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._parts = []
        self._active = False
        self._ev = None
        self.bind(pos=self._draw, size=self._draw)

    def start(self, count=42):
        self._active = True
        self._parts = []
        for _ in range(count):
            self._parts.append({
                "x": random.uniform(0.03, 0.97),
                "y": random.uniform(0.45, 1.05),
                "vy": random.uniform(0.22, 0.55),
                "vx": random.uniform(-0.08, 0.08),
                "rot": random.uniform(0, 360),
                "vr": random.uniform(-160, 160),
                "size": random.uniform(0.012, 0.028),
                "color": random.choice((CYAN, MAGENTA, GOLD, WHITE, "#7FE7FF")),
            })
        if self._ev:
            self._ev.cancel()
        self._ev = Clock.schedule_interval(self._step, 1 / 30.0)
        self._draw()

    def stop(self):
        self._active = False
        if self._ev:
            self._ev.cancel()
            self._ev = None
        self.canvas.clear()

    def _step(self, dt):
        if not self._active:
            return
        h = max(1, self.height)
        for p in self._parts:
            p["y"] -= p["vy"] * dt
            p["x"] += p["vx"] * dt + 0.02 * math.sin(p["y"] * 9 + p["rot"]) * dt
            p["rot"] += p["vr"] * dt
            if p["y"] < -0.05:
                p["y"] = 1.06
                p["x"] = random.uniform(0.03, 0.97)
        self._draw()

    @canvas_draw
    def _draw(self, *a):
        self.canvas.clear()
        if not self._active:
            return
        w, h = self.size
        if w < 4:
            return
        for p in self._parts:
            px = self.x + p["x"] * w
            py = self.y + p["y"] * h
            sz = p["size"] * w
            GColor(*rgba(p["color"], 0.9))
            PushMatrix()
            Rotate(angle=p["rot"], origin=(px, py))
            Rectangle(pos=(px - sz / 2, py - sz / 4), size=(sz, sz / 2))
            PopMatrix()


class GlowDot(Widget):
    tint = ListProperty(rgba(CYAN))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw, tint=self._draw)
        self._draw()

    @canvas_draw
    def _draw(self, *a):
        self.canvas.clear()
        s = min(self.width, self.height)
        if s < 2:
            return
        cx, cy = self.center
        GColor(*self.tint[:3], 0.18)
        Ellipse(pos=(cx - s * .5, cy - s * .5), size=(s, s))
        GColor(*self.tint[:3], 0.9)
        Ellipse(pos=(cx - s * .18, cy - s * .18), size=(s * .36, s * .36))

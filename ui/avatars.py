"""Procedurally drawn fighters -- six genuinely different characters."""
from __future__ import annotations

import math

from kivy.graphics import (Color as GColor, Ellipse, Line, PushMatrix, PopMatrix,
                           Rotate, RoundedRectangle)
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.widget import Widget

from config import CHARACTERS_BY_ID
from ui.theme import canvas_draw, rgba


class CharacterAvatar(Widget):
    """Vector portrait drawn with Kivy canvas instructions."""

    char_id = StringProperty("amara")
    mood = StringProperty("idle")  # idle | win | lose | hit
    tilt = NumericProperty(0.0)
    glow = NumericProperty(0.0)
    animate = BooleanProperty(False)

    def __init__(self, char_id="amara", **kwargs):
        super().__init__(**kwargs)
        self.char_id = char_id
        self._phase = 0.0
        self.bind(pos=self._redraw, size=self._redraw, char_id=self._redraw,
                  mood=self._redraw, tilt=self._redraw, glow=self._redraw)
        self._redraw()

    # ------------------------------------------------------------------ draw
    @canvas_draw
    def _redraw(self, *args):
        self.canvas.clear()
        w, h = self.size
        if w < 8 or h < 8:
            return
        char = CHARACTERS_BY_ID.get(self.char_id, next(iter(CHARACTERS_BY_ID.values())))
        S = min(w, h)
        ox = self.x + (w - S) / 2
        oy = self.y + (h - S) / 2
        bob = math.sin(self._phase) * S * 0.006 if self.animate else 0.0

        def X(u):
            return ox + u * S

        def Y(v):
            return oy + v * S + bob

        def col(c, a=1.0):
            return rgba(c, a)

        def ell(cx, cy, rx, ry, color, alpha=1.0, angle=0.0, pivot=None):
            GColor(*col(color, alpha))
            if angle:
                PushMatrix()
                Rotate(angle=angle, origin=(X(cx), Y(cy)))
            Ellipse(pos=(X(cx) - rx * S, Y(cy) - ry * S), size=(rx * 2 * S, ry * 2 * S))
            if angle:
                PopMatrix()

        def rrect(x, y, rw, rh, radius, color, alpha=1.0):
            GColor(*col(color, alpha))
            RoundedRectangle(pos=(X(x), Y(y)), size=(rw * S, rh * S),
                             radius=[radius * S])

        def line(points, color, width=2.0, alpha=1.0):
            GColor(*col(color, alpha))
            Line(points=[coord for p in points for coord in (X(p[0]), Y(p[1]))],
                 width=max(1.0, width * S / 100.0), cap="round", joint="round")

        skin = char["skin"]
        skin_d = char["skin_dark"]
        skin_l = char["skin_light"]
        hair = char["hair"]
        hair_hi = char["hair_hi"]
        outfit = char["outfit"]
        outfit_d = char["outfit_dark"]
        accent = char["accent"]
        style = char["style"]
        eye_col = char["eyes"]
        mood = self.mood
        is_girl = char["gender"] == "girl"

        # ambient glow behind the portrait
        if self.glow > 0:
            ell(0.5, 0.57, 0.47, 0.5, accent, 0.10 * self.glow)
            ell(0.5, 0.57, 0.42, 0.45, accent, 0.10 * self.glow)

        # backplate disc
        ell(0.5, 0.55, 0.44, 0.46, "#1B2A52", 0.65)
        ell(0.5, 0.55, 0.41, 0.43, "#22356A", 0.45)

        # -------------------------------------------------- shoulders / body
        rrect(0.13, -0.02, 0.74, 0.42, 0.15, outfit, 1.0)
        rrect(0.13, 0.02, 0.74, 0.10, 0.06, outfit_d, 0.7)
        # collar / shirt detail
        ell(0.5, 0.32, 0.16, 0.10, outfit_d, 0.85)
        rrect(0.44, 0.00, 0.12, 0.25, 0.05, accent, 0.55)
        if char["gender"] == "boy":
            line([(0.42, 0.03), (0.5, 0.20), (0.58, 0.03)], accent, 3.0, 0.5)
        else:
            ell(0.5, 0.18, 0.035, 0.035, accent, 0.9)
        # neck
        rrect(0.43, 0.28, 0.14, 0.12, 0.05, skin)
        rrect(0.43, 0.28, 0.14, 0.05, 0.02, skin_d, 0.5)

        # ---------------------------------------------------------- hair back
        if style == "afro":
            for ang in range(0, 360, 30):
                a = math.radians(ang)
                ell(0.5 + math.cos(a) * 0.31, 0.68 + math.sin(a) * 0.30,
                    0.105, 0.105, hair)
            ell(0.5, 0.68, 0.33, 0.32, hair)
            ell(0.40, 0.83, 0.10, 0.08, hair_hi, 0.6)
        elif style == "ponytail":
            ell(0.5, 0.70, 0.26, 0.26, hair)
            ell(0.79, 0.63, 0.14, 0.22, hair, 1.0, angle=-16)
            ell(0.80, 0.48, 0.09, 0.13, hair, 1.0, angle=-18)
            ell(0.82, 0.70, 0.07, 0.11, hair_hi, 0.65, angle=-16)
            rrect(0.68, 0.72, 0.10, 0.05, 0.025, accent)
        elif style == "buns":
            ell(0.30, 0.90, 0.12, 0.11, hair)
            ell(0.70, 0.90, 0.12, 0.11, hair)
            ell(0.30, 0.92, 0.07, 0.06, hair_hi, 0.55)
            ell(0.70, 0.92, 0.07, 0.06, hair_hi, 0.55)
            ell(0.5, 0.70, 0.27, 0.27, hair)
        elif style == "spiky":
            ell(0.5, 0.69, 0.28, 0.26, hair)
            for i, (bx, ang) in enumerate(((0.31, -34), (0.40, -18), (0.50, 0),
                                           (0.60, 16), (0.69, 32))):
                GColor(*col(hair))
                PushMatrix()
                Rotate(angle=ang, origin=(X(bx), Y(0.82)))
                Ellipse(pos=(X(bx) - 0.045 * S, Y(0.82)), size=(0.09 * S, 0.24 * S))
                PopMatrix()
            line([(0.36, 0.80), (0.44, 0.86)], hair_hi, 2.0, 0.7)
        elif style == "fade":
            ell(0.5, 0.78, 0.24, 0.13, hair)
            rrect(0.28, 0.76, 0.44, 0.08, 0.04, hair)
        elif style == "curly":
            for ang in range(10, 175, 22):
                a = math.radians(ang)
                ell(0.5 + math.cos(a) * 0.26, 0.76 + math.sin(a) * 0.16,
                    0.085, 0.075, hair, 1.0)
                ell(0.5 + math.cos(a) * 0.26, 0.78 + math.sin(a) * 0.16,
                    0.045, 0.035, hair_hi, 0.55)
            ell(0.5, 0.76, 0.24, 0.13, hair)

        # ------------------------------------------------------------ head
        PushMatrix()
        Rotate(angle=self.tilt + (7 if mood == "hit" else 0), origin=(X(0.5), Y(0.60)))
        # ears
        ell(0.275, 0.59, 0.04, 0.055, skin)
        ell(0.725, 0.59, 0.04, 0.055, skin)
        if is_girl:
            ell(0.275, 0.545, 0.018, 0.018, accent, 0.95)
            ell(0.725, 0.545, 0.018, 0.018, accent, 0.95)
        # head
        ell(0.5, 0.60, 0.235, 0.275, skin)
        ell(0.55, 0.66, 0.15, 0.18, skin_l, 0.18)
        # jaw shading
        ell(0.5, 0.44, 0.14, 0.05, skin_d, 0.16)

        # ------------------------------------------------------- face details
        # brows
        brow_y = 0.685
        if mood == "hit":
            line([(0.385, 0.705), (0.46, 0.685)], hair, 3.2)
            line([(0.54, 0.685), (0.615, 0.705)], hair, 3.2)
        elif mood == "lose":
            line([(0.385, 0.70), (0.46, 0.715)], hair, 3.0)
            line([(0.54, 0.715), (0.615, 0.70)], hair, 3.0)
        else:
            line([(0.385, 0.70), (0.46, 0.712)], hair, 2.6)
            line([(0.54, 0.712), (0.615, 0.70)], hair, 2.6)
        # eyes
        for ex in (0.43, 0.57):
            if mood == "hit":
                line([(ex - 0.035, 0.655), (ex + 0.035, 0.605)], eye_col, 3.4)
                line([(ex - 0.035, 0.605), (ex + 0.035, 0.655)], eye_col, 3.4)
            elif mood == "win":
                line([(ex - 0.032, 0.615), (ex, 0.642), (ex + 0.032, 0.615)],
                     eye_col, 3.2)
            else:
                ell(ex, 0.625, 0.043, 0.034, "#FFFFFF", 0.95)
                ell(ex + 0.004, 0.622, 0.021, 0.025, eye_col)
                ell(ex - 0.006, 0.635, 0.007, 0.008, "#FFFFFF", 0.95)
                if is_girl:
                    line([(ex - 0.045, 0.658), (ex + 0.042, 0.665)], hair, 2.0, 0.8)
        # nose
        line([(0.5, 0.585), (0.49, 0.548), (0.515, 0.546)], skin_d, 2.2, 0.9)
        # blush
        if is_girl:
            ell(0.36, 0.55, 0.045, 0.024, "#FF8A9E", 0.30)
            ell(0.64, 0.55, 0.045, 0.024, "#FF8A9E", 0.30)
        if char.get("freckles"):
            for fx, fy in ((0.36, 0.57), (0.39, 0.545), (0.34, 0.54),
                           (0.61, 0.57), (0.64, 0.545), (0.66, 0.57)):
                ell(fx, fy, 0.008, 0.008, skin_d, 0.9)
        # mouth
        if mood == "win":
            ell(0.5, 0.505, 0.075, 0.052, "#3A1220")
            ell(0.5, 0.489, 0.045, 0.022, "#FF7C93", 0.9)
            line([(0.425, 0.53), (0.575, 0.53)], "#FFFFFF", 2.2, 0.85)
        elif mood == "lose":
            line([(0.45, 0.49), (0.5, 0.475), (0.55, 0.49)], "#7A2B37", 2.6)
        elif mood == "hit":
            ell(0.5, 0.49, 0.045, 0.055, "#4A1520")
            ell(0.5, 0.50, 0.03, 0.02, "#C4515E", 0.6)
        else:
            line([(0.445, 0.50), (0.5, 0.478), (0.555, 0.50)], "#8B3A48", 2.8)
            line([(0.47, 0.520), (0.53, 0.520)], skin_d, 1.6, 0.5)
        PopMatrix()

        # ---------------------------------------------------------- hair front
        if style == "afro":
            ell(0.5, 0.83, 0.21, 0.07, hair)
            ell(0.36, 0.80, 0.07, 0.09, hair)
            ell(0.64, 0.80, 0.07, 0.09, hair)
            ell(0.43, 0.86, 0.07, 0.05, hair_hi, 0.5)
        elif style == "ponytail":
            ell(0.5, 0.82, 0.22, 0.10, hair)
            # side-swept fringe
            ell(0.44, 0.80, 0.15, 0.07, hair, 1.0, angle=-10)
            ell(0.62, 0.81, 0.10, 0.06, hair, 1.0, angle=14)
            line([(0.38, 0.80), (0.46, 0.855)], hair_hi, 2.2, 0.6)
        elif style == "buns":
            ell(0.5, 0.82, 0.22, 0.10, hair)
            ell(0.46, 0.79, 0.10, 0.05, hair, 1.0, angle=-12)
            line([(0.38, 0.81), (0.62, 0.81)], hair_hi, 2.0, 0.4)
        elif style == "spiky":
            ell(0.5, 0.81, 0.20, 0.08, hair)
            line([(0.38, 0.83), (0.50, 0.88), (0.62, 0.83)], hair_hi, 2.0, 0.5)
        elif style == "fade":
            rrect(0.29, 0.775, 0.42, 0.055, 0.025, hair)
            rrect(0.34, 0.82, 0.32, 0.03, 0.015, hair_hi)
            rrect(0.27, 0.72, 0.035, 0.08, 0.01, hair)
            rrect(0.695, 0.72, 0.035, 0.08, 0.01, hair)
            rrect(0.27, 0.765, 0.46, 0.035, 0.015, accent, 0.95)
        elif style == "curly":
            for fx, fy, r in ((0.34, 0.80, 0.075), (0.43, 0.85, 0.08),
                              (0.53, 0.85, 0.075), (0.62, 0.81, 0.07),
                              (0.47, 0.79, 0.06), (0.57, 0.79, 0.055)):
                ell(fx, fy, r, r * 0.85, hair)
                ell(fx - r * 0.25, fy + r * 0.25, r * 0.42, r * 0.35, hair_hi, 0.5)

        # outfit emblem
        if char["id"] in ("amara", "mei"):
            ell(0.5, 0.16, 0.05, 0.05, accent, 0.75)
            ell(0.5, 0.16, 0.025, 0.025, "#FFFFFF", 0.55)
        elif char["id"] == "kenji":
            line([(0.42, 0.15), (0.5, 0.22), (0.58, 0.15), (0.5, 0.08), (0.42, 0.15)],
                 accent, 2.4, 0.9)
        elif char["id"] == "malik":
            line([(0.43, 0.10), (0.43, 0.21)], accent, 3.0)
            line([(0.5, 0.08), (0.5, 0.23)], accent, 3.0)
            line([(0.57, 0.10), (0.57, 0.21)], accent, 3.0)

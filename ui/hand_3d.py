"""Pseudo-3D hand renderer: vector art, shadow, perspective and motion."""
from __future__ import annotations

import math

from kivy.graphics import (Color as GColor, Ellipse, Line, PopMatrix, PushMatrix,
                           Rotate, RoundedRectangle, Scale, Translate)
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.widget import Widget

from config import CHARACTERS_BY_ID
from ui.theme import HAND_SKIN, canvas_draw, rgba


class Hand3D(Widget):
    """A chunky vector hand with real depth cues (shadow + scale + tilt)."""

    gesture = StringProperty("rock")
    side = StringProperty("left")
    reveal = NumericProperty(0.0)
    rot = NumericProperty(0.0)
    glow = NumericProperty(0.0)
    skin = StringProperty(HAND_SKIN["base"])
    skin_dark = StringProperty(HAND_SKIN["dark"])
    skin_light = StringProperty(HAND_SKIN["light"])
    sleeve = StringProperty("#2E86DE")
    sleeve_dark = StringProperty("#16548F")
    accent = StringProperty("#25E6D0")
    winner = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for prop in ("gesture", "side", "reveal", "rot", "glow", "skin",
                     "skin_dark", "skin_light", "sleeve", "sleeve_dark",
                     "accent", "winner"):
            self.bind(**{prop: self._redraw})
        self.bind(pos=self._redraw, size=self._redraw)
        self.set_character(CHARACTERS_BY_ID["amara"])

    def set_character(self, char: dict):
        self.skin = char.get("skin", HAND_SKIN["base"])
        self.skin_dark = char.get("skin_dark", HAND_SKIN["dark"])
        self.skin_light = char.get("skin_light", HAND_SKIN["light"])
        self.sleeve = char.get("outfit", "#2E86DE")
        self.sleeve_dark = char.get("outfit_dark", "#16548F")
        self.accent = char.get("accent", "#25E6D0")
        self._redraw()

    # ------------------------------------------------------------------ draw
    @canvas_draw
    def _redraw(self, *args):
        self.canvas.clear()
        w, h = self.size
        if w < 10 or h < 10:
            return
        S = min(w, h)
        ox = self.x + (w - S) / 2
        oy = self.y + (h - S) / 2

        def X(u):
            return ox + ((1.0 - u) if mirror < 0 else u) * S

        def Y(v):
            return oy + v * S

        def col(c, a=1.0):
            return rgba(c, a)

        def rot_pt(cx, cy, dx, dy, deg):
            a = math.radians(deg)
            return (cx + dx * math.cos(a) - dy * math.sin(a),
                    cy + dx * math.sin(a) + dy * math.cos(a))

        def capsule(cx, cy, cw, ch, deg, color, alpha=1.0, outline=None,
                    outline_w=0.010, radius=None):
            if outline:
                capsule(cx, cy, cw + outline_w * 2, ch + outline_w * 2,
                        deg, outline, alpha * 0.85, None, 0, radius)
            PushMatrix()
            Translate(X(cx), Y(cy))
            Rotate(angle=deg)
            GColor(*col(color, alpha))
            rr = radius if radius is not None else min(cw, ch) * 0.5
            RoundedRectangle(pos=(-cw * S / 2, -ch * S / 2),
                             size=(cw * S, ch * S),
                             radius=[rr * S])
            PopMatrix()

        def ellipse(cx, cy, rx, ry, color, alpha=1.0, deg=0.0):
            PushMatrix()
            Translate(X(cx), Y(cy))
            Rotate(angle=deg)
            GColor(*col(color, alpha))
            Ellipse(pos=(-rx * S, -ry * S), size=(rx * 2 * S, ry * 2 * S))
            PopMatrix()

        def line(points, color, width=2.0, alpha=1.0):
            GColor(*col(color, alpha))
            Line(points=[c for p in points for c in (X(p[0]), Y(p[1]))],
                 width=max(1.0, width * S / 120.0), cap="round", joint="round")

        gesture = self.gesture
        reveal = max(0.0, min(1.0, self.reveal))
        lift = -(1.0 - reveal) * 0.34
        scale = 0.62 + 0.38 * reveal
        mirror = -1.0 if self.side == "left" else 1.0

        # ------------------------------------------------------------- shadow
        GColor(0, 0, 0, 0.20 * reveal)
        Ellipse(pos=(X(0.16), Y(-0.01)), size=(0.68 * S, 0.12 * S))
        GColor(0, 0, 0, 0.36 * reveal)
        Ellipse(pos=(X(0.27), Y(0.02)), size=(0.46 * S, 0.075 * S))
        # accent glow for the winner
        if self.glow > 0:
            GColor(*col(self.accent, 0.10 * self.glow))
            Ellipse(pos=(X(0.10), Y(0.10)), size=(0.80 * S, 0.80 * S))
            GColor(*col(self.accent, 0.08 * self.glow))
            Ellipse(pos=(X(0.17), Y(0.15)), size=(0.66 * S, 0.66 * S))

        # --------------------------------------------------------- transform
        PushMatrix()
        Translate(0, lift * S)
        Rotate(angle=self.rot, origin=(X(0.5), Y(0.42)))
        Scale(x=scale, y=scale, origin=(X(0.5), Y(0.42)))

        skin = self.skin
        skin_d = self.skin_dark
        skin_l = self.skin_light
        outline = rgba(skin_d, 0.55)
        nail = rgba("#FFEFE4", 0.85)

        # ------------------------------------------------------------ sleeve
        capsule(0.5, 0.045, 0.34, 0.30, 0, self.sleeve, 1.0, radius=0.05)
        capsule(0.5, 0.175, 0.36, 0.07, 0, self.sleeve_dark, 0.95, radius=0.02)
        capsule(0.5, 0.135, 0.345, 0.045, 0, self.accent, 0.75, radius=0.02)
        # wrist
        capsule(0.5, 0.245, 0.235, 0.14, 0, skin_d, 1.0, radius=0.045)
        capsule(0.5, 0.255, 0.225, 0.135, 0, skin, 1.0, radius=0.045)

        if gesture == "paper":
            # four extended fingers
            fingers = (
                (0.355, 0.255, 0.078, -9),
                (0.445, 0.305, 0.083, -3),
                (0.535, 0.285, 0.080, 2),
                (0.620, 0.225, 0.072, 8),
            )
            for fx, ln, fw, ang in fingers:
                base_y = 0.55
                cy = base_y + ln * 0.5
                capsule(fx, cy, fw, ln, ang, skin, 1.0, outline, 0.008)
                # lighter inner edge
                ix, iy = rot_pt(fx, cy, -fw * 0.22, ln * 0.08, ang)
                capsule(ix, iy, fw * 0.32, ln * 0.72, ang, skin_l, 0.30, radius=fw * 0.16)
                tipx, tipy = rot_pt(fx, cy, 0, ln * 0.37, ang)
                ellipse(tipx, tipy, fw * 0.20, fw * 0.16, "#FFEFE4", 0.55, ang)
            # thumb out to the side (left of palm before mirroring)
            capsule(0.285, 0.405, 0.092, 0.235, 33, skin, 1.0, outline, 0.008)
            tx, ty = rot_pt(0.285, 0.405, 0, 0.092, 33)
            ellipse(tx, ty, 0.020, 0.017, "#FFEFE4", 0.55, 33)

        elif gesture == "scissors":
            # index + middle in a V
            for fx, ln, fw, ang in ((0.435, 0.315, 0.082, -15),
                                    (0.555, 0.335, 0.082, 15)):
                cy = 0.55 + ln * 0.5
                capsule(fx, cy, fw, ln, ang, skin, 1.0, outline, 0.008)
                ix, iy = rot_pt(fx, cy, -fw * 0.22, ln * 0.06, ang)
                capsule(ix, iy, fw * 0.30, ln * 0.70, ang, skin_l, 0.30, radius=fw * 0.15)
                tx, ty = rot_pt(fx, cy, 0, ln * 0.37, ang)
                ellipse(tx, ty, fw * 0.20, fw * 0.16, "#FFEFE4", 0.55, ang)
            # folded ring + pinky
            capsule(0.615, 0.535, 0.072, 0.105, 8, skin, 1.0, outline, 0.007)
            capsule(0.678, 0.515, 0.066, 0.090, 12, skin, 1.0, outline, 0.007)
            line([(0.655, 0.545), (0.665, 0.500)], skin_d, 2.3, 0.55)
            # thumb folded across
            capsule(0.405, 0.375, 0.085, 0.185, 58, skin, 1.0, outline, 0.008)
            ellipse(0.435, 0.36, 0.018, 0.026, skin_d, 0.25, 58)

        else:  # rock ------------------------------------------------------
            # curled finger stack
            for i, (fx, fw) in enumerate(((0.355, 0.082), (0.445, 0.086),
                                          (0.535, 0.084), (0.625, 0.078))):
                capsule(fx, 0.545, fw, 0.135, 0, skin, 1.0, outline, 0.008)
                capsule(fx, 0.465, fw * 0.96, 0.085, 0, skin_d, 0.45, radius=0.03)
            # thumb crossing the fingers
            capsule(0.375, 0.415, 0.095, 0.185, 62, skin, 1.0, outline, 0.008)
            ellipse(0.33, 0.455, 0.020, 0.027, skin_d, 0.22, 62)

        # --------------------------------------------------------------- palm
        if gesture == "rock":
            capsule(0.5, 0.40, 0.355, 0.32, 0, skin, 1.0, outline, 0.012, 0.09)
            capsule(0.5, 0.39, 0.32, 0.29, 0, skin_l, 0.18, radius=0.07)
            # knuckles
            for kx in (0.355, 0.445, 0.535, 0.625):
                ellipse(kx, 0.585, 0.044, 0.036, skin_l, 0.45)
                ellipse(kx, 0.578, 0.022, 0.017, skin_d, 0.18)
            line([(0.32, 0.47), (0.35, 0.44)], skin_d, 2.2, 0.5)
        else:
            capsule(0.5, 0.40, 0.36, 0.35, 0, skin, 1.0, outline, 0.012, 0.095)
            ellipse(0.44, 0.44, 0.10, 0.11, skin_l, 0.16)
            # palm creases
            line([(0.37, 0.39), (0.45, 0.35), (0.53, 0.38)], skin_d, 2.0, 0.35)
            line([(0.40, 0.32), (0.48, 0.30)], skin_d, 1.8, 0.28)
            # fingertips shading on top of palm edge
            GColor(*rgba(skin_d, 0.18))
            Ellipse(pos=(X(0.31), Y(0.545)), size=(0.38 * S, 0.045 * S))

        # wrist shading seam
        line([(0.39, 0.275), (0.61, 0.275)], skin_d, 1.8, 0.28)
        line([(0.36, 0.30), (0.64, 0.30)], skin_l, 1.4, 0.18)

        # winner accent ring on the wrist
        if self.winner:
            GColor(*rgba(self.accent, 0.85))
            Line(ellipse=(X(0.38), Y(0.245), 0.24 * S, 0.065 * S),
                 width=max(1.5, S * 0.008))

        PopMatrix()

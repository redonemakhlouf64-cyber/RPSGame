"""Splash / main menu."""
from __future__ import annotations

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color as GColor, Ellipse, Line, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget

from config import APP_VERSION
from screens.base import BaseScreen
from ui.hand_3d import Hand3D
from ui.theme import (CYAN, DARK, GOLD, MAGENTA, MUTED, WHITE, U, canvas_draw, rgba)
from ui.widgets import PillButton, label, set_label


class TitleOrb(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    @canvas_draw
    def _draw(self, *a):
        self.canvas.clear()
        s = min(self.width, self.height)
        if s < 4:
            return
        cx, cy = self.center
        for i, (f, alpha, col) in enumerate((
                (1.00, 0.06, CYAN), (0.82, 0.08, MAGENTA), (0.62, 0.10, CYAN))):
            GColor(*rgba(col, alpha))
            Ellipse(pos=(cx - s * f / 2, cy - s * f / 2), size=(s * f, s * f))
        GColor(*rgba(CYAN, 0.55))
        Line(circle=(cx, cy, s * 0.47), width=max(1.0, U(1.2)))
        GColor(*rgba(MAGENTA, 0.35))
        Line(circle=(cx, cy, s * 0.56), width=max(1.0, U(1.0)))


class SplashScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="splash", **kwargs)

        self.orb = TitleOrb(size_hint=(None, None), size=(U(300), U(300)))
        self.orb.pos_hint = {"center_x": 0.5, "center_y": 0.79}
        self.body.add_widget(self.orb)

        self.title = label("RPS", size=64, color=WHITE)
        self.title.pos_hint = {"center_x": 0.5, "center_y": 0.835}
        self.body.add_widget(self.title)
        self.title_glow = label("RPS", size=64, color=CYAN)
        self.title_glow.opacity = 0.35
        self.title_glow.pos_hint = {"center_x": 0.5, "center_y": 0.839}
        self.body.add_widget(self.title_glow)

        self.subtitle = self.T("app_sub", size=12, color=CYAN)
        self.subtitle.pos_hint = {"center_x": 0.5, "center_y": 0.742}
        self.body.add_widget(self.subtitle)

        self.arena = label("ARENA", size=26, color=GOLD)
        self.arena.pos_hint = {"center_x": 0.47, "center_y": 0.885}
        self.body.add_widget(self.arena)
        self.badge = label("3D", size=13, color=DARK, bold=True)
        self.badge.size_hint = (None, None)
        self.badge.size = (U(34), U(20))
        self.badge.pos_hint = {"center_x": 0.66, "center_y": 0.885}
        self.badge.canvas.before.clear()
        with self.badge.canvas.before:
            self._bc = GColor(*rgba(GOLD))
            self._br = Rectangle(pos=self.badge.pos, size=self.badge.size)
        self.badge.bind(pos=lambda *a: setattr(self._br, "pos", self.badge.pos),
                        size=lambda *a: setattr(self._br, "size", self.badge.size))
        self.body.add_widget(self.badge)

        # trio of hands
        self.hands = []
        specs = (("rock", "left", -10, 0.20), ("paper", "right", 0, 0.50),
                 ("scissors", "right", 10, 0.80))
        for gesture, side, rot, cx in specs:
            hnd = Hand3D(size_hint=(None, None), size=(U(150), U(160)),
                         gesture=gesture, side=side, reveal=1.0, rot=rot)
            hnd.pos_hint = {"center_x": cx, "center_y": 0.52}
            self.body.add_widget(hnd)
            self.hands.append(hnd)
            anim = (Animation(rot=rot + 4, d=1.4, t="in_out_sine") +
                    Animation(rot=rot - 4, d=1.4, t="in_out_sine"))
            anim.repeat = True
            Clock.schedule_once(lambda dt, h=hnd, a=anim, r=rot: a.start(h), 0.2)

        self.start_btn = PillButton(
            text=app.t("start"), size=(U(276), U(70)),
            bg_color=rgba(CYAN), text_color=rgba(DARK),
            font_size=U(24), radius=22)
        self.start_btn.pos_hint = {"center_x": 0.5, "center_y": 0.30}
        self.start_btn.glow = True
        self.start_btn.bind(on_release=self._start)
        self.body.add_widget(self.start_btn)
        self.pulse_anim = Animation(pulse=1.0, d=1.1, t="in_out_sine") + \
            Animation(pulse=0.0, d=1.1, t="in_out_sine")
        self.pulse_anim.repeat = True
        self.pulse_anim.start(self.start_btn)

        self.hint = self.T("tap_start", size=12, color=MUTED)
        self.hint.pos_hint = {"center_x": 0.5, "center_y": 0.215}
        self.hint.size_hint = (0.9, None)
        self.hint.height = U(20)
        self.body.add_widget(self.hint)

        self.stats = label("", size=11, color=MUTED)
        self.stats.pos_hint = {"center_x": 0.5, "center_y": 0.14}
        self.stats.size_hint = (0.9, None)
        self.stats.height = U(18)
        self.body.add_widget(self.stats)

        # top controls
        self.sound_btn = PillButton(text="", size=(U(112), U(34)),
                                    bg_color=rgba("#FFFFFF", 0.07),
                                    text_color=rgba(WHITE),
                                    border_color=rgba("#FFFFFF", 0.12),
                                    font_size=U(11), radius=12)
        self.sound_btn.pos_hint = {"x": 0.035, "top": 0.982}
        self.sound_btn.bind(on_release=self._toggle_sound)
        self.body.add_widget(self.sound_btn)

        self.lang_btn = PillButton(text="", size=(U(126), U(34)),
                                   bg_color=rgba("#FFFFFF", 0.07),
                                   text_color=rgba(CYAN),
                                   border_color=rgba(CYAN, 0.28),
                                   font_size=U(11), radius=12)
        self.lang_btn.pos_hint = {"right": 0.965, "top": 0.982}
        self.lang_btn.bind(on_release=lambda *a: self._open_lang())
        self.body.add_widget(self.lang_btn)

        self.footer = label(f"v{APP_VERSION}  ·  vector 3D studio", size=9, color=MUTED)
        self.footer.pos_hint = {"center_x": 0.5, "center_y": 0.035}
        self.footer.opacity = 0.65
        self.body.add_widget(self.footer)

    # ------------------------------------------------------------- actions
    def _start(self, *a):
        self.app.audio.click()
        if self.app.store.get("first_run", True):
            self.go("language", "left")
        else:
            self.go("character", "left")

    def _open_lang(self):
        self.app.audio.click()
        self.go("language", "left")

    def _toggle_sound(self, *a):
        current = bool(self.app.store.get("sound", True))
        self.app.store.set("sound", not current)
        if not current:
            self.app.audio.click()
        self._refresh_sound()

    def _refresh_sound(self):
        key = "sound_on" if self.app.store.get("sound", True) else "sound_off"
        set_label(self.sound_btn, self.app.t(key))
        lang = self.app.language_native()
        set_label(self.lang_btn, f"{lang}  v")
        st = self.app.store.stats()
        set_label(self.stats,
                  f"{self.app.t('matches')} {st['matches']}   ·   "
                  f"{self.app.t('stats')} {st['wins']}")

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._refresh_sound()
        set_label(self.start_btn, self.app.t("start"))
        self.start_btn.color = rgba(DARK)

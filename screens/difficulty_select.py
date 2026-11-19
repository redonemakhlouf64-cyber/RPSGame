"""Difficulty selection (four robot brains)."""
from __future__ import annotations

from kivy.graphics import Color as GColor, RoundedRectangle
from kivy.uix.widget import Widget

from config import DIFFICULTIES
from screens.base import BaseScreen
from ui.theme import CYAN, MAGENTA, MUTED, WHITE, U, canvas_draw, rgba
from ui.widgets import Card, PillButton, RobotIcon, label, set_label


class LevelBars(Widget):
    def __init__(self, level=1, accent=CYAN, **kwargs):
        super().__init__(**kwargs)
        self.level = level
        self.accent = accent
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    @canvas_draw
    def _draw(self, *a):
        self.canvas.clear()
        w, h = self.size
        if w < 4:
            return
        for i in range(4):
            bh = h * (0.38 + i * 0.20)
            bw = w * 0.16
            x = self.x + i * w * 0.22
            y = self.y
            if i < self.level:
                GColor(*rgba(self.accent))
            else:
                GColor(*rgba("#FFFFFF", 0.14))
            RoundedRectangle(pos=(x, y), size=(bw, bh), radius=[U(2)])


class DifficultyCard(Card):
    def __init__(self, level_key, desc_key, index, accent, on_pick, app, **kwargs):
        super().__init__(**kwargs)
        self.on_pick = on_pick
        self.border_color = rgba(accent, 0.22)
        self.fill = rgba("#0F1B36", 0.78)
        self.name_lbl = label(app.t(level_key), size=15, color=accent)
        self.name_lbl.pos_hint = {"x": 0.055, "top": 0.82}
        self.name_lbl.size_hint = (0.5, None)
        self.name_lbl.height = U(22)
        self.name_lbl.halign = "left"
        self.name_lbl.text_size = (U(200), None)
        self.add_widget(self.name_lbl)
        self.desc = label(app.t(desc_key), size=10, color=MUTED)
        self.desc.pos_hint = {"x": 0.055, "top": 0.50}
        self.desc.size_hint = (0.66, None)
        self.desc.height = U(30)
        self.desc.halign = "left"
        self.desc.text_size = (U(250), None)
        self.add_widget(self.desc)
        self.bars = LevelBars(level=index, accent=accent,
                              size_hint=(None, None), size=(U(66), U(30)))
        self.bars.pos_hint = {"right": 0.94, "center_y": 0.5}
        self.add_widget(self.bars)
        self._keys = (level_key, desc_key)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self.glow = 0.9
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self.glow = 0.0
            if self.collide_point(*touch.pos):
                self.on_pick()
            return True
        return super().on_touch_up(touch)


class DifficultyScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="difficulty", **kwargs)
        self.cards = {}
        self.add_topbar("difficulty", back=lambda: self.go("mode", "right"))

        self.robot = RobotIcon(size_hint=(None, None), size=(U(84), U(84)))
        self.robot.pos_hint = {"center_x": 0.5, "top": 0.905}
        self.body.add_widget(self.robot)
        self.heading = self.T("choose_difficulty", size=14, color=MUTED)
        self.heading.pos_hint = {"center_x": 0.5, "top": 0.775}
        self.heading.size_hint = (0.9, None)
        self.heading.height = U(24)
        self.body.add_widget(self.heading)

        accents = {"beginner": "#6FE7A8", "medium": CYAN,
                   "strong": "#FFB347", "very_strong": MAGENTA}
        top = 0.725
        for i, level in enumerate(DIFFICULTIES, start=1):
            card = DifficultyCard(level, level + "_desc", i,
                                  accents[level],
                                  lambda lv=level: self._pick(lv), app,
                                  size_hint=(0.9, None), height=U(80),
                                  pos_hint={"center_x": 0.5, "top": top})
            self.body.add_widget(card)
            self.cards[level] = card
            self._tr.append((card.name_lbl, level))
            self._tr.append((card.desc, level + "_desc"))
            top -= 0.105

        self.note = label("The robot never sees your move before you pick.",
                          size=9, color=MUTED)
        self.note.pos_hint = {"center_x": 0.5, "y": 0.062}
        self.note.size_hint = (0.9, None)
        self.note.height = U(16)
        self.note.opacity = 0.75
        self.body.add_widget(self.note)

    def _pick(self, level):
        self.app.audio.click()
        self.app.set_difficulty(level)
        self.app.start_robot_match(level)

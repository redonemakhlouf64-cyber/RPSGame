"""Mode selection: robot or human rival."""
from __future__ import annotations

from kivy.uix.floatlayout import FloatLayout

from screens.base import BaseScreen
from ui.avatars import CharacterAvatar
from ui.theme import CYAN, MAGENTA, MUTED, WHITE, U, rgba
from ui.widgets import (Card, DuelIcon, PillButton, RobotIcon, label, set_label)


class ModeCard(Card):
    def __init__(self, icon, title, subtitle, accent, on_pick, **kwargs):
        super().__init__(**kwargs)
        self.on_pick = on_pick
        self.border_color = rgba(accent, 0.35)
        self.fill = rgba("#0F1B36", 0.82)
        self.icon = icon
        self.icon.size_hint = (None, None)
        self.icon.size = (U(92), U(92))
        self.icon.pos_hint = {"x": 0.07, "center_y": 0.53}
        self.add_widget(self.icon)
        self.title = label(title, size=20, color=WHITE)
        self.title.pos_hint = {"x": 0.36, "top": 0.70}
        self.title.size_hint = (0.60, None)
        self.title.height = U(28)
        self.title.halign = "left"
        self.title.text_size = (U(210), None)
        self.add_widget(self.title)
        self.subtitle = label(subtitle, size=10, color=MUTED)
        self.subtitle.pos_hint = {"x": 0.37, "top": 0.47}
        self.subtitle.size_hint = (0.56, None)
        self.subtitle.height = U(42)
        self.subtitle.halign = "left"
        self.subtitle.text_size = (U(200), None)
        self.add_widget(self.subtitle)
        self._accent = accent

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self.glow = 0.8
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


class ModeScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="mode", **kwargs)
        self.add_topbar("mode", back=lambda: self.go("character", "right"))

        self.avatar = CharacterAvatar(char_id=app.character_id,
                                      size_hint=(None, None),
                                      size=(U(54), U(54)))
        self.avatar.pos_hint = {"x": 0.055, "top": 0.905}
        self.body.add_widget(self.avatar)
        self.who = label("", size=14, color=WHITE)
        self.who.pos_hint = {"x": 0.20, "top": 0.90}
        self.who.size_hint = (0.7, None)
        self.who.height = U(24)
        self.who.halign = "left"
        self.who.text_size = (U(300), None)
        self.body.add_widget(self.who)

        self.heading = self.T("choose_mode", size=18, color=MUTED)
        self.heading.pos_hint = {"center_x": 0.5, "top": 0.755}
        self.heading.size_hint = (0.9, None)
        self.heading.height = U(26)
        self.body.add_widget(self.heading)

        self.robot_card = ModeCard(
            RobotIcon(), app.t("vs_robot"), app.t("vs_robot_sub"),
            CYAN, lambda: self._choose("robot"),
            size_hint=(0.9, None), height=U(156),
            pos_hint={"center_x": 0.5, "top": 0.71})
        self.robot_card.title.color = rgba(CYAN)
        self.body.add_widget(self.robot_card)
        self.reg(self.robot_card.title, "vs_robot")
        self.reg(self.robot_card.subtitle, "vs_robot_sub")

        self.friend_card = ModeCard(
            DuelIcon(), app.t("vs_friend"), app.t("vs_friend_sub"),
            MAGENTA, lambda: self._choose("friend"),
            size_hint=(0.9, None), height=U(156),
            pos_hint={"center_x": 0.5, "top": 0.50})
        self.friend_card.title.color = rgba(MAGENTA)
        self.body.add_widget(self.friend_card)
        self.reg(self.friend_card.title, "vs_friend")
        self.reg(self.friend_card.subtitle, "vs_friend_sub")

        self.foot = self.T("first_to", size=11, color=MUTED)
        self.foot.pos_hint = {"center_x": 0.5, "y": 0.09}
        self.foot.size_hint = (0.9, None)
        self.foot.height = U(18)
        self.body.add_widget(self.foot)

    def _choose(self, mode):
        self.app.audio.click()
        self.app.set_mode(mode)
        if mode == "robot":
            self.go("difficulty", "left")
        else:
            self.go("lobby", "left")

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        char = self.app.character
        self.avatar.char_id = char["id"]
        set_label(self.who, f"{char['name']}  ·  {self.app.t(char['gender'])}")

"""Six-character roster."""
from __future__ import annotations

from kivy.animation import Animation
from kivy.uix.gridlayout import GridLayout

from config import CHARACTERS
from screens.base import BaseScreen
from ui.avatars import CharacterAvatar
from ui.theme import CYAN, DARK, GOLD, MUTED, WHITE, U, rgba
from ui.widgets import Card, PillButton, label, set_label


class SelectCard(Card):
    def __init__(self, char, on_pick, **kwargs):
        super().__init__(**kwargs)
        self.char = char
        self.on_pick = on_pick
        self.avatar = CharacterAvatar(char_id=char["id"], size_hint=(None, None),
                                      size=(U(112), U(112)))
        self.avatar.pos_hint = {"center_x": 0.5, "top": 0.97}
        self.add_widget(self.avatar)
        self.name_lbl = label(char["name"], size=16, color=WHITE)
        self.name_lbl.pos_hint = {"center_x": 0.5, "top": 0.38}
        self.name_lbl.size_hint = (0.9, None)
        self.name_lbl.height = U(22)
        self.add_widget(self.name_lbl)
        self.tag_lbl = label("", size=9, color=MUTED)
        self.tag_lbl.pos_hint = {"center_x": 0.5, "top": 0.235}
        self.tag_lbl.size_hint = (1, None)
        self.tag_lbl.height = U(16)
        self.tag_lbl.text = char["tag"].upper()
        self.add_widget(self.tag_lbl)
        self.gender_bar = label("", size=9, color=char["accent"])
        self.gender_bar.pos_hint = {"center_x": 0.5, "top": 0.13}
        self.gender_bar.size_hint = (1, None)
        self.gender_bar.height = U(14)
        self.add_widget(self.gender_bar)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self.opacity = 0.85
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self.opacity = 1.0
            if self.collide_point(*touch.pos):
                self.on_pick(self.char)
            return True
        return super().on_touch_up(touch)


class CharacterScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="character", **kwargs)
        self.cards = {}
        self.add_topbar("fighters", back=lambda: self.go("language", "right"))

        self.heading = self.T("choose_fighter", size=20, color=WHITE)
        self.heading.pos_hint = {"center_x": 0.5, "top": 0.935}
        self.heading.size_hint = (0.92, None)
        self.heading.height = U(32)
        self.body.add_widget(self.heading)

        self.sub = label("3 girls · 3 boys · 6 screams", size=10, color=MUTED)
        self.sub.pos_hint = {"center_x": 0.5, "top": 0.892}
        self.sub.size_hint = (0.9, None)
        self.sub.height = U(16)
        self.body.add_widget(self.sub)

        grid = GridLayout(cols=2, spacing=U(9), padding=(0, 0, 0, 0),
                          size_hint=(0.94, 0.61),
                          pos_hint={"center_x": 0.5, "top": 0.862})
        for char in CHARACTERS:
            card = SelectCard(char, self._pick,
                              size_hint=(1, 1),
                              fill=rgba("#0F1B36", 0.72),
                              border_color=rgba("#FFFFFF", 0.08))
            grid.add_widget(card)
            self.cards[char["id"]] = card
        self.body.add_widget(grid)

        self.confirm = PillButton(text="", size=(U(310), U(58)),
                                  bg_color=rgba(CYAN), text_color=rgba(DARK),
                                  font_size=U(16), radius=18)
        self.confirm.pos_hint = {"center_x": 0.5, "y": 0.095}
        self.confirm.bind(on_release=self._confirm)
        self.body.add_widget(self.confirm)

        self.preview = PillButton(text=app.t("preview_voice"),
                                  size=(U(180), U(30)),
                                  bg_color=rgba("#FFFFFF", 0.05),
                                  text_color=rgba(MUTED),
                                  border_color=rgba("#FFFFFF", 0.10),
                                  font_size=U(10), radius=10)
        self.preview.pos_hint = {"center_x": 0.5, "y": 0.045}
        self.preview.bind(on_release=self._preview)
        self.body.add_widget(self.preview)
        self.reg(self.preview, "preview_voice")

    # --------------------------------------------------------------- logic
    def _pick(self, char):
        self.app.audio.click()
        self.app.set_character(char["id"])
        self._refresh_selection()
        self.after(0.05, lambda: self._bounce(self.cards[char["id"]].avatar))

    def _bounce(self, avatar):
        anim = Animation(tilt=5, d=0.12) + Animation(tilt=-4, d=0.12) + \
            Animation(tilt=0, d=0.10)
        anim.start(avatar)

    def _refresh_selection(self):
        selected = self.app.character_id
        for cid, card in self.cards.items():
            on = cid == selected
            card.glow = 1.0 if on else 0.0
            card.border_color = rgba(CYAN, 0.8) if on else rgba("#FFFFFF", 0.08)
            card.fill = rgba("#16305C", 0.92) if on else rgba("#0F1B36", 0.72)
            card.avatar.glow = 1.0 if on else 0.0
            card.avatar.mood = "win" if on else "idle"
            card.gender_bar.text = self.app.t(card.char["gender"]).upper()
        char = self.app.character
        set_label(self.confirm, f"{self.app.t('fight')}  ·  {char['name']}")

    def _confirm(self, *a):
        self.app.audio.click()
        self.go("mode", "left")

    def _preview(self, *a):
        self.app.audio.click()
        self.app.audio.scream(self.app.character_id)

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._refresh_selection()
        for card in self.cards.values():
            card.gender_bar.text = self.app.t(card.char["gender"]).upper()

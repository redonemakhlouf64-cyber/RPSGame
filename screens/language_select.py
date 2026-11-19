"""Language picker."""
from __future__ import annotations

from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView

from logic.i18n import LANGUAGES
from screens.base import BaseScreen
from ui.theme import CYAN, DARK, MAGENTA, MUTED, WHITE, U, rgba
from ui.widgets import CatIcon, PillButton, label, set_label


class LanguageScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="language", **kwargs)
        self.rows = {}
        self.add_topbar("language", back=lambda: self.go("splash", "right"))

        self.title = self.T("choose_language", size=19, color=WHITE)
        self.title.pos_hint = {"center_x": 0.5, "top": 0.90}
        self.title.size_hint = (0.9, None)
        self.title.height = U(36)
        self.body.add_widget(self.title)

        scroll = ScrollView(size_hint=(0.9, 0.76), pos_hint={"center_x": 0.5, "y": 0.055},
                            do_scroll_x=False, bar_width=U(2),
                            bar_color=rgba(CYAN, 0.5))
        grid = GridLayout(cols=1, spacing=U(7), size_hint_y=None,
                          padding=(0, U(4), 0, U(10)))
        grid.bind(minimum_height=grid.setter("height"))
        row_h = U(52)
        for code, native, english, badge in LANGUAGES:
            btn = PillButton(
                text=f"{badge}    {native}",
                size=(U(370), row_h), font_size=U(15),
                bg_color=rgba("#FFFFFF", 0.05),
                text_color=rgba(WHITE),
                border_color=rgba("#FFFFFF", 0.08),
                radius=14)
            btn.size_hint = (1, None)
            btn.text = f"{badge}    {native}   ·   {english}" if code != "cat" else \
                f"CAT    {native}   ·   {english}"
            btn.bind(on_release=lambda inst, c=code: self._pick(c))
            grid.add_widget(btn)
            self.rows[code] = btn
            if code == "cat":
                cat = CatIcon(size_hint=(None, None), size=(U(30), U(30)))
                cat.pos_hint = {"right": 0.97, "center_y": 0.5}
                cat.opacity = 0.95
                btn.add_widget(cat)
        scroll.add_widget(grid)
        self.body.add_widget(scroll)
        self._mark()

    def _mark(self):
        current = self.app.lang
        for code, btn in self.rows.items():
            if code == current:
                btn.bg_color = rgba(CYAN, 0.16)
                btn.text_color = rgba(CYAN)
                btn.border_color = rgba(CYAN, 0.65)
            else:
                btn.bg_color = rgba("#FFFFFF", 0.05)
                btn.text_color = rgba(WHITE)
                btn.border_color = rgba("#FFFFFF", 0.08)

    def _pick(self, code):
        self.app.audio.click()
        self.app.set_language(code)
        self.app.store.set("first_run", False)
        self.app.toast(self.app.t("language_saved"))
        self._mark()
        self.go("character", "left")

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._mark()

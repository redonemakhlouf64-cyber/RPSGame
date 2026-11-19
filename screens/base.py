"""Shared screen scaffold, localization plumbing and dialogs."""
from __future__ import annotations

from kivy.clock import Clock
from kivy.graphics import Color as GColor, Line, RoundedRectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import Screen

from ui.theme import CYAN, DARK, MAGENTA, MUTED, WHITE, U, rgba
from ui.widgets import (Card, GradientBG, PillButton, Text, TopBar, label,
                        set_label)


class BaseScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._tr = []
        self._events = []
        self.bg = GradientBG(size_hint=(1, 1))
        self.add_widget(self.bg)
        self.body = FloatLayout(size_hint=(1, 1))
        self.add_widget(self.body)
        self.topbar = None

    # ------------------------------------------------------------ helpers
    def T(self, key, size=14, color=WHITE, **kwargs):
        lbl = label(self.app.t(key), size=size, color=color, **kwargs)
        self._tr.append((lbl, key))
        return lbl

    def reg(self, widget, key):
        self._tr.append((widget, key))
        return widget

    def refresh_texts(self):
        for widget, key in list(self._tr):
            try:
                set_label(widget, self.app.t(key))
            except Exception:
                pass

    def add_topbar(self, title_key="", back=None):
        self.topbar = TopBar(title=self.app.t(title_key), back=back)
        self.topbar.pos_hint = {"x": 0, "top": 1}
        self.body.add_widget(self.topbar)
        if title_key:
            self._tr.append((self.topbar.title, title_key))
        return self.topbar

    def after(self, delay, fn):
        ev = Clock.schedule_once(lambda dt: fn(), delay)
        self._events.append(ev)
        return ev

    def cancel_events(self):
        for ev in self._events:
            try:
                ev.cancel()
            except Exception:
                pass
        self._events = []

    def on_pre_enter(self, *args):
        self.refresh_texts()
        # A screen that was laid out while hidden can keep a stale canvas on
        # some GL drivers; repaint the custom art once it becomes visible.
        for delay in (0.05, 0.40, 1.20, 2.40, 4.00):
            self.after(delay, self._repaint_art)

    def _repaint_art(self):
        def walk(widget):
            module = type(widget).__module__ or ""
            if module.startswith(("ui.", "screens.")):
                for name in ("_redraw", "_draw", "_sync"):
                    fn = getattr(widget, name, None)
                    if callable(fn):
                        try:
                            fn()
                        except Exception:
                            pass
                        break
            for child in list(widget.children):
                walk(child)

        walk(self)

    def on_leave(self, *args):
        self.cancel_events()

    def go(self, name, direction="left"):
        self.app.go(name, direction)


def confirm_dialog(app, title, subtitle, on_yes, on_no=None,
                   yes_key="yes", no_key="no"):
    """A clean neon confirm modal (used by gameplay exit)."""
    view = ModalView(size_hint=(0.86, None), height=U(220),
                     background_color=(0, 0, 0, 0), background="",
                     auto_dismiss=False)
    card = FloatLayout(size_hint=(1, 1))
    with card.canvas.before:
        GColor(*rgba("#0C172E", 0.98))
        _bg = RoundedRectangle(radius=[U(20)])
        GColor(*rgba(CYAN, 0.35))
        _ln = Line(width=max(1.0, U(1.3)))
    card.bind(pos=lambda w, v: (
        setattr(_bg, "pos", v), setattr(_bg, "size", w.size),
        setattr(_ln, "rounded_rectangle", (v[0], v[1], w.width, w.height, U(20)))))
    t = label(title, size=17, color=WHITE)
    t.pos_hint = {"center_x": 0.5, "top": 0.93}
    t.size_hint = (0.9, None)
    t.height = U(30)
    card.add_widget(t)
    s = label(subtitle, size=12, color=MUTED)
    s.pos_hint = {"center_x": 0.5, "top": 0.68}
    s.size_hint = (0.88, None)
    s.height = U(40)
    s.text_size = (U(300), None)
    card.add_widget(s)

    def close_yes(*a):
        view.dismiss()
        if on_yes:
            on_yes()

    def close_no(*a):
        view.dismiss()
        if on_no:
            on_no()

    yes = PillButton(text=app.t(yes_key), size=(U(120), U(46)),
                     bg_color=rgba(MAGENTA), text_color=rgba(WHITE),
                     font_size=U(14), radius=14)
    yes.pos_hint = {"center_x": 0.28, "y": 0.10}
    yes.bind(on_release=close_yes)
    no = PillButton(text=app.t(no_key), size=(U(120), U(46)),
                    bg_color=rgba("#FFFFFF", 0.10), text_color=rgba(WHITE),
                    border_color=rgba("#FFFFFF", 0.16),
                    font_size=U(14), radius=14)
    no.pos_hint = {"center_x": 0.72, "y": 0.10}
    no.bind(on_release=close_no)
    card.add_widget(yes)
    card.add_widget(no)
    view.add_widget(card)
    view.open()
    return view

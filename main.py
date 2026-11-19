"""RPS Arena 3D -- entry point.

Usage:
    python main.py                 play
    python main.py --headless-test logic/network/audio test suite
    python main.py --screenshot-test [--shots DIR]  (Xvfb QA)
"""
from __future__ import annotations

import os
import sys
import traceback

from config import APP_NAME, APP_VERSION, CHARACTERS, CHARACTERS_BY_ID  # noqa: F401

HEADLESS = "--headless-test" in sys.argv
SHOTS = "--screenshot-test" in sys.argv

if os.environ.get("RPS_DEBUG"):
    import faulthandler
    faulthandler.dump_traceback_later(120, exit=True)

if HEADLESS:
    from logic.self_test import run_headless

    sys.exit(0 if run_headless() else 1)

# ------------------------------------------------------------------ Kivy prep
from kivy.config import Config

if "RPS_WINDOWED" in os.environ or SHOTS:
    Config.set("graphics", "width", "432")
    Config.set("graphics", "height", "768")
    Config.set("graphics", "resizable", "1")
    if SHOTS:
        # software GL (Xvfb) is much faster without MSAA
        Config.set("graphics", "multisamples", "0")
else:
    Config.set("graphics", "width", "432")
    Config.set("graphics", "height", "768")
    Config.set("graphics", "resizable", "1")

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import SlideTransition, ScreenManager
from kivy.app import App

from logic.audio import init_audio
from logic.i18n import LANGUAGES, language_label, t as translate
from logic import network, storage
from screens.bluetooth_lobby import LobbyScreen
from screens.character_select import CharacterScreen
from screens.difficulty_select import DifficultyScreen
from screens.gameplay import GameplayScreen
from screens.language_select import LanguageScreen
from screens.mode_select import ModeScreen
from screens.result import ResultScreen
from screens.splash import SplashScreen
from ui.theme import CYAN, DARK, U, rgba
from ui.widgets import Toast


class PortraitStage(FloatLayout):
    pass


class RPSApp(App):
    """Application shell + routing + persistent player state."""

    def build(self):
        self.title = APP_NAME
        Window.clearcolor = (0.02, 0.03, 0.06, 1)
        try:
            Window.softinput_mode = "below_target"
        except Exception:
            pass
        android_runtime = bool(os.environ.get("TERMUX_VERSION") or
                               os.environ.get("ANDROID_ARGUMENT") or
                               os.environ.get("P4A_BOOTSTRAP"))
        if not SHOTS and android_runtime and not os.environ.get("RPS_WINDOWED"):
            try:
                Window.fullscreen = "auto"
            except Exception:
                pass
        try:
            network.request_portrait()
        except Exception:
            pass
        try:
            network.request_storage_permissions()
        except Exception:
            pass

        self.store = storage.STORE
        self.lang = str(self.store.get("lang", "en"))
        self.character_id = str(self.store.get("character", "amara"))
        if self.character_id not in CHARACTERS_BY_ID:
            self.character_id = "amara"
        self.difficulty = str(self.store.get("difficulty", "medium"))
        self.mode = "robot"
        self.link = None
        self.net_role = None
        self.transport = "wifi"
        self.peer_hello = {}
        self.last_result = {}

        self.audio = init_audio(self.store)
        self.audio.preload()

        self.root = FloatLayout()
        from kivy.graphics import Color as GColor, Rectangle
        with self.root.canvas.before:
            self._bgc = GColor(0.015, 0.02, 0.04, 1)
            self._bgr = Rectangle(pos=self.root.pos, size=self.root.size)
        self.root.bind(pos=self._sync_root_bg, size=self._sync_root_bg)

        self.stage = PortraitStage(size_hint=(None, None))
        self.stage.aspect = 9 / 16.0
        self.root.add_widget(self.stage)

        self.sm = ScreenManager(transition=SlideTransition(duration=0.22))
        self.stage.add_widget(self.sm)

        self.screens = {}
        for cls in (SplashScreen, LanguageScreen, CharacterScreen, ModeScreen,
                    DifficultyScreen, LobbyScreen, GameplayScreen, ResultScreen):
            scr = cls(self)
            self.screens[scr.name] = scr
            self.sm.add_widget(scr)
        self.splash = self.screens["splash"]
        self.gameplay = self.screens["gameplay"]
        self.result = self.screens["result"]
        self.lobby = self.screens["lobby"]

        self.toastw = Toast()
        self.stage.add_widget(self.toastw)

        self.sm.current = "splash"
        self.root.bind(size=self._layout_stage, pos=self._layout_stage)
        Window.bind(on_keyboard=self._on_keyboard)
        Clock.schedule_once(self._layout_stage, 0)
        Clock.schedule_once(self._layout_stage, 0.15)
        if SHOTS:
            Clock.schedule_once(self._run_screenshot_test, 0.8)
        return self.root

    # ------------------------------------------------------------- helpers
    def _sync_root_bg(self, *a):
        try:
            self._bgr.pos = self.root.pos
            self._bgr.size = self.root.size
        except Exception:
            pass

    def _layout_stage(self, *a):
        try:
            w = max(1.0, Window.width)
            h = max(1.0, Window.height)
            aspect = 9 / 16.0
            if h <= 0:
                return
            if w / h > aspect:
                sh = h
                sw = h * aspect
            else:
                sw = w
                sh = w / aspect
            self.stage.size = (sw, sh)
            self.stage.pos = ((w - sw) / 2.0, (h - sh) / 2.0)
            self.toastw.width = sw * 0.87
            self.toastw.height = U(46)
            self.toastw.pos = (self.stage.x + (sw - self.toastw.width) / 2,
                               self.stage.y + sh * 0.905)
        except Exception:
            pass

    def tr(self, key):
        return translate(self.lang, key)

    def t(self, key):
        return translate(self.lang, key)

    @property
    def character(self):
        return CHARACTERS_BY_ID.get(self.character_id, CHARACTERS[0])

    def language_native(self):
        return language_label(self.lang)

    def set_language(self, code):
        valid = {c for c, *_ in LANGUAGES}
        self.lang = code if code in valid else "en"
        self.store.set("lang", self.lang)

    def set_character(self, char_id):
        if char_id in CHARACTERS_BY_ID:
            self.character_id = char_id
            self.store.set("character", char_id)

    def set_difficulty(self, level):
        self.difficulty = level
        self.store.set("difficulty", level)

    def set_mode(self, mode):
        self.mode = mode if mode in ("robot", "friend") else "robot"

    def go(self, name, direction="left"):
        if name not in self.screens:
            return
        if self.sm.current == name:
            return
        try:
            self.sm.transition.direction = direction
        except Exception:
            pass
        self.sm.current = name

    def go_home(self):
        self.close_link()
        self.go("splash", "right")

    def toast(self, text):
        try:
            self._layout_stage()
            self.toastw.show_toast(str(text))
        except Exception:
            pass

    # -------------------------------------------------------------- matches
    def start_robot_match(self, level=None):
        if level:
            self.set_difficulty(level)
        self.set_mode("robot")
        self.close_link()
        self.gameplay.prepare_robot(self.difficulty)
        self.go("gameplay", "left")

    def start_friend_match(self):
        self.set_mode("friend")
        self.gameplay.prepare_friend()
        self.go("gameplay", "left")

    def show_result(self, data):
        self.last_result = dict(data)
        self.result.set_data(data)
        self.go("result", "left")

    # ------------------------------------------------------------- network
    def close_link(self):
        link = self.link
        self.link = None
        if link:
            try:
                link.on_message = None
                link.on_close = None
                link.close()
            except Exception:
                pass

    def dispatch_net(self, msg):
        scr = self.sm.current_screen
        if hasattr(scr, "handle_net_message"):
            try:
                scr.handle_net_message(msg)
            except Exception:
                traceback.print_exc()

    def dispatch_close(self):
        scr = self.sm.current_screen
        if hasattr(scr, "on_peer_left"):
            try:
                scr.on_peer_left()
            except Exception:
                traceback.print_exc()
        else:
            self.toast(self.tr("disconnected"))
            self.close_link()

    # --------------------------------------------------------------- system
    def _on_keyboard(self, window, key, scancode=None, codepoint=None, modifier=None):
        if key == 27:  # escape / Android back
            name = self.sm.current
            if name == "gameplay":
                self.screens["gameplay"]._exit()
            elif name == "lobby":
                self.screens["lobby"]._back()
            elif name == "result":
                self.close_link()
                self.go("splash", "right")
            elif name == "splash":
                return False
            else:
                self.go("splash", "right")
            return True
        return False

    def on_stop(self):
        self.close_link()

    def on_pause(self):
        return True

    def on_resume(self):
        pass

    # ------------------------------------------------------ screenshot mode
    def _run_screenshot_test(self, dt):
        shots_dir = os.environ.get("RPS_SHOTS", os.path.join(os.getcwd(), "shots"))
        try:
            os.makedirs(shots_dir, exist_ok=True)
        except Exception:
            pass
        plan = [
            ("01_splash", None, 5.0),
            ("02_language", ("go", ("language", "left")), 3.0),
            ("03_character", ("go", ("character", "left")), 3.0),
            ("04_mode", ("go", ("mode", "left")), 3.0),
            ("05_difficulty", ("go", ("difficulty", "left")), 3.0),
            ("06_gameplay", ("robot", "strong"), 2.4),
            ("07_countdown", ("choose", "paper"), 2.0),
            ("08_reveal", ("wait", 2.1), 1.2),
            ("09_result", ("result", None), 8.0),
        ]
        steps = []

        def do_step(i):
            if i >= len(plan):
                Clock.schedule_once(lambda dt: self.stop(), 0.2)
                return
            name, action, delay = plan[i]
            try:
                if action and action[0] == "go":
                    self.go(*action[1])
                elif action and action[0] == "robot":
                    self.start_robot_match(action[1])
                elif action and action[0] == "choose":
                    self.gameplay._choose_player(action[1])
                elif action and action[0] == "wait":
                    pass
                elif action and action[0] == "result":
                    self.show_result({
                        "mode": "robot",
                        "difficulty": "strong",
                        "player_char": self.character_id,
                        "opponent_char": "robot",
                        "opponent_is_robot": True,
                        "player_score": 3,
                        "opponent_score": 1,
                        "player_won": True,
                        "rounds": [],
                    })
                    self.sm.current = "result"
            except Exception:
                traceback.print_exc()

            def snap(_dt, nm=name):
                path = os.path.join(shots_dir, nm + ".png")
                try:
                    Window.screenshot(name=path)
                    print("SHOT", path, flush=True)
                except Exception as exc:
                    print("SHOT-FAIL", name, exc, flush=True)
                Clock.schedule_once(lambda _d: do_step(i + 1), 0.15)

            Clock.schedule_once(snap, delay)

        Clock.schedule_once(lambda dt: do_step(0), 0.2)


if __name__ == "__main__":
    try:
        RPSApp().run()
    except Exception:
        traceback.print_exc()
        sys.exit(1)

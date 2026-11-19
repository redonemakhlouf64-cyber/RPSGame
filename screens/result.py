"""Match result with the three-slap finisher."""
from __future__ import annotations

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color as GColor, Rectangle
from kivy.properties import NumericProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget

from config import CHARACTERS_BY_ID
from logic import network
from screens.base import BaseScreen
from ui.avatars import CharacterAvatar
from ui.hand_3d import Hand3D
from ui.theme import CYAN, DARK, GOLD, MAGENTA, MUTED, RED, WHITE, U, canvas_draw, rgba
from ui.widgets import (Card, Confetti, PillButton, RobotIcon, label, set_label)
from screens.gameplay import ROBOT_CHAR


class Flash(Widget):
    alpha = NumericProperty(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._sync, size=self._sync, alpha=self._sync)
        self._sync()

    @canvas_draw
    def _sync(self, *a):
        self.canvas.clear()
        GColor(1, 1, 1, max(0.0, min(0.6, self.alpha)))
        Rectangle(pos=self.pos, size=self.size)


class ResultScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="result", **kwargs)
        self.data = {}
        self._saved = False
        self._slap_events = []
        self._slap_index = 0
        self._rematch_started = False
        self._sent_req = False
        self._seq_active = False
        self.base_x = 0
        self.base_victim_x = 0

        self.confetti = Confetti(size_hint=(1, 1))
        self.body.add_widget(self.confetti)

        self.flash = Flash(size_hint=(1, 1))
        self.body.add_widget(self.flash)

        self.title = label("", size=30, color=WHITE)
        self.title.pos_hint = {"center_x": 0.5, "top": 0.972}
        self.title.size_hint = (0.94, None)
        self.title.height = U(44)
        self.body.add_widget(self.title)

        self.score = label("", size=17, color=GOLD)
        self.score.pos_hint = {"center_x": 0.5, "center_y": 0.893}
        self.score.size_hint = (0.6, None)
        self.score.height = U(24)
        self.body.add_widget(self.score)

        # winner strip -------------------------------------------------------
        self.winner_av_box = FloatLayout(size_hint=(None, None),
                                         size=(U(46), U(46)))
        self.winner_av_box.pos_hint = {"x": 0.11, "top": 0.852}
        self.body.add_widget(self.winner_av_box)
        self.winner_av = CharacterAvatar(char_id=app.character_id,
                                         size_hint=(None, None),
                                         size=(U(46), U(46)))
        self.winner_av.pos_hint = {"x": 0, "y": 0}
        self.winner_av_box.add_widget(self.winner_av)
        self.winner_robot = RobotIcon(size_hint=(None, None), size=(U(46), U(46)))
        self.winner_robot.pos_hint = {"x": 0, "y": 0}
        self.winner_av_box.add_widget(self.winner_robot)
        self.winner_name = label("", size=13, color=WHITE)
        self.winner_name.pos_hint = {"x": 0.23, "center_y": 0.833}
        self.winner_name.size_hint = (0.62, None)
        self.winner_name.height = U(22)
        self.winner_name.halign = "left"
        self.winner_name.text_size = (U(280), None)
        self.body.add_widget(self.winner_name)
        self.crown = label("WINNER", size=8, color=GOLD)
        self.crown.pos_hint = {"right": 0.92, "center_y": 0.833}
        self.crown.size_hint = (None, None)
        self.crown.size = (U(160), U(16))
        self.crown.halign = "right"
        self.crown.text_size = (U(160), None)
        self.body.add_widget(self.crown)

        # slap stage ---------------------------------------------------------
        self.stage = Card(size_hint=(0.92, None), height=U(236),
                          pos_hint={"center_x": 0.5, "top": 0.788},
                          fill=rgba("#0D1933", 0.86),
                          border_color=rgba(MAGENTA, 0.25))
        self.body.add_widget(self.stage)
        self.stage_prompt = label("", size=10, color=MUTED)
        self.stage_prompt.pos_hint = {"center_x": 0.5, "top": 0.96}
        self.stage_prompt.size_hint = (0.8, None)
        self.stage_prompt.height = U(18)
        self.stage.add_widget(self.stage_prompt)

        self.victim_box = FloatLayout(size_hint=(None, None),
                                      size=(U(168), U(168)))
        self.victim_box.pos_hint = {"center_x": 0.56, "center_y": 0.50}
        self.stage.add_widget(self.victim_box)
        self.victim_av = CharacterAvatar(char_id=app.character_id,
                                         size_hint=(None, None),
                                         size=(U(168), U(168)))
        self.victim_av.pos_hint = {"x": 0, "y": 0}
        self.victim_box.add_widget(self.victim_av)
        self.victim_robot = RobotIcon(size_hint=(None, None), size=(U(168), U(168)))
        self.victim_robot.pos_hint = {"x": 0, "y": 0}
        self.victim_box.add_widget(self.victim_robot)

        self.hand = Hand3D(gesture="paper", side="right", reveal=1.0, rot=-30,
                           size_hint=(None, None), size=(U(126), U(130)))
        self.stage.add_widget(self.hand)
        self.slap_lbl = label(app.t("slap"), size=26, color=GOLD)
        self.slap_lbl.pos_hint = {"center_x": 0.55, "center_y": 0.64}
        self.slap_lbl.opacity = 0.0
        self.reg(self.slap_lbl, "slap")
        self.stage.add_widget(self.slap_lbl)

        self.slap_count = label("", size=9, color=MUTED)
        self.slap_count.pos_hint = {"x": 0.06, "y": 0.06}
        self.slap_count.size_hint = (0.35, None)
        self.slap_count.height = U(16)
        self.slap_count.halign = "left"
        self.slap_count.text_size = (U(120), None)
        self.stage.add_widget(self.slap_count)

        # buttons ------------------------------------------------------------
        self.again = PillButton(text=app.t("play_again"),
                                size=(U(210), U(54)),
                                bg_color=rgba(CYAN), text_color=rgba(DARK),
                                font_size=U(15), radius=17)
        self.again.pos_hint = {"center_x": 0.5, "y": 0.125}
        self.again.bind(on_release=lambda *a: self._play_again())
        self.body.add_widget(self.again)
        self.reg(self.again, "play_again")
        self.home_btn = PillButton(text=app.t("home"),
                                   size=(U(210), U(42)),
                                   bg_color=rgba("#FFFFFF", 0.06),
                                   text_color=rgba(MUTED),
                                   border_color=rgba("#FFFFFF", 0.12),
                                   font_size=U(12), radius=13)
        self.home_btn.pos_hint = {"center_x": 0.5, "y": 0.052}
        self.home_btn.bind(on_release=lambda *a: self._home())
        self.body.add_widget(self.home_btn)
        self.reg(self.home_btn, "home")

        self.status = label("", size=9, color=CYAN)
        self.status.pos_hint = {"center_x": 0.5, "y": 0.192}
        self.status.size_hint = (0.9, None)
        self.status.height = U(16)
        self.body.add_widget(self.status)

        self.bind(size=self._layout_stage, pos=self._layout_stage)

    # ------------------------------------------------------------- lifecycle
    def set_data(self, data):
        self.data = dict(data or {})
        self._saved = False
        self._rematch_started = False
        self._sent_req = False

    def _layout_stage(self, *a):
        if not self.stage or self.stage.width < 10:
            return
        self.base_x = self.stage.x
        self.base_victim_x = self.victim_box.x
        if not self._seq_active:
            self.hand.pos = (self.stage.x - self.hand.width * 0.45,
                             self.stage.y + self.stage.height * 0.28)
            self.hand.rot = -32

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._apply_data()
        self._layout_stage()
        self.after(0.15, self._layout_stage)
        self._schedule_slaps()
        if not self._saved:
            self._save_history()
            self._saved = True

    def on_leave(self, *args):
        self._cancel_slaps()
        self.confetti.stop()
        self._seq_active = False
        super().on_leave(*args)

    def _cancel_slaps(self):
        for ev in self._slap_events:
            try:
                ev.cancel()
            except Exception:
                pass
        self._slap_events = []
        try:
            Animation.cancel_all(self.hand)
            Animation.cancel_all(self.victim_av)
        except Exception:
            pass

    def after_slap(self, delay, fn):
        ev = Clock.schedule_once(lambda dt: fn(), delay)
        self._slap_events.append(ev)
        return ev

    # ---------------------------------------------------------------- data
    def _apply_data(self):
        d = self.data
        pchar = CHARACTERS_BY_ID.get(d.get("player_char"), CHARACTERS_BY_ID["amara"])
        robot = bool(d.get("opponent_is_robot"))
        ochar = ROBOT_CHAR if robot else CHARACTERS_BY_ID.get(
            d.get("opponent_char"), CHARACTERS_BY_ID["kenji"])
        won = bool(d.get("player_won"))
        ps = d.get("player_score", 0)
        os_ = d.get("opponent_score", 0)

        set_label(self.title, self.app.t("you_win" if won else "you_lose"))
        self.title.color = rgba(CYAN if won else MAGENTA)
        self.score.text = f"{ps} : {os_}"
        winner = pchar if won else ochar
        self.winner_av.opacity = 0 if (not won and robot) else 1
        self.winner_robot.opacity = 1 if (not won and robot) else 0
        if not won and robot:
            self.winner_robot.size = self.winner_av_box.size
        else:
            self.winner_av.char_id = winner.get("id", "amara")
            self.winner_av.mood = "win"
            self.winner_av.glow = 1.0
        set_label(self.winner_name, f"{winner.get('name', 'PLAYER')}  ·  "
                                    f"{'YOU' if won else 'RIVAL'}")
        set_label(self.crown, self.app.t("match_win" if won else "match_lose"))
        self.crown.color = rgba(GOLD if won else MUTED)

        # victim (the loser takes the slaps)
        victim = ochar if won else pchar
        victim_robot = won and robot
        self.victim_av.opacity = 0 if victim_robot else 1
        self.victim_robot.opacity = 1 if victim_robot else 0
        if victim_robot:
            self.victim_robot.size = self.victim_box.size
        else:
            self.victim_av.char_id = victim.get("id", "amara")
            self.victim_av.mood = "lose"
            self.victim_av.glow = 0.0
        self.victim_char = victim.get("id", "amara")
        self.victim_is_robot = victim_robot

        # winner's hand delivers the slaps
        attacker = winner
        self.hand.set_character(attacker if not (not won and robot) else ROBOT_CHAR)
        self.hand.gesture = "paper"
        self.hand.side = "right"
        self.hand.reveal = 1.0
        self.stage_prompt.text = ("3 SLAPS" if won else "OUCH")
        set_label(self.slap_count, "")
        self.flash.alpha = 0.0
        self.slap_lbl.opacity = 0.0
        if won:
            self.confetti.start(48)
        else:
            self.confetti.stop()

    def _save_history(self):
        d = self.data
        if not d:
            return
        try:
            self.app.store.add_match(
                mode=d.get("mode", "robot"),
                difficulty=d.get("difficulty", ""),
                player_char=d.get("player_char", ""),
                opponent_char=d.get("opponent_char", ""),
                player_score=d.get("player_score", 0),
                opponent_score=d.get("opponent_score", 0),
                player_won=bool(d.get("player_won")),
                lang=self.app.lang,
            )
        except Exception:
            pass

    # --------------------------------------------------------- slap sequence
    def _schedule_slaps(self):
        self._cancel_slaps()
        self._slap_index = 0
        self._seq_active = True
        self.after_slap(0.75, lambda: self._slap(1))

    def _slap(self, n):
        if n > 3:
            self._seq_active = False
            self.after_slap(0.2, self._after_slaps)
            return
        self._layout_stage()
        start_x = self.stage.x - self.hand.width * 0.45
        start_y = self.stage.y + self.stage.height * (0.22 + 0.04 * (n % 2))
        target_x = self.stage.center_x + self.stage.width * 0.05
        target_y = self.stage.y + self.stage.height * 0.50
        self.hand.pos = (start_x, start_y)
        self.hand.rot = -34
        self.hand.opacity = 1.0
        self.slap_lbl.text = self.app.t("slap")
        self.slap_lbl.opacity = 0.0
        set_label(self.slap_count, f"{n} / 3")

        anim = (Animation(x=target_x, y=target_y, rot=8, d=0.16, t="out_quad"))
        anim.bind(on_complete=lambda *a: self._impact(n))
        anim.start(self.hand)

    def _impact(self, n):
        self.app.audio.smack()
        self.victim_av.mood = "hit"
        self.flash.alpha = 0.45
        Animation(alpha=0.0, d=0.25).start(self.flash)
        self.slap_lbl.opacity = 1.0
        Animation(opacity=0.0, d=0.45).start(self.slap_lbl)
        # victim recoils / shakes
        self.victim_av.tilt = 9
        base_v = self.base_victim_x or self.victim_box.x
        Animation(x=base_v + U(7), d=0.06).start(self.victim_box)
        Animation(x=base_v, d=0.18).start(self.victim_box)
        Animation(tilt=-6, d=0.10).start(self.victim_av)
        Animation(tilt=0, d=0.22).start(self.victim_av)
        # screen-shake the stage
        base = self.base_x or self.stage.x
        Animation(x=base + U(6), d=0.04).start(self.stage)
        Animation(x=base - U(5), d=0.08).start(self.stage)
        Animation(x=base, d=0.08).start(self.stage)
        network.vibrate(55)
        if self.victim_is_robot:
            self.app.audio.play("smack", 0.85)
            self.app.audio.play("scream_robot", 0.9)
        else:
            self.app.audio.scream(self.victim_char)
        if n < 3:
            self.after_slap(0.78, lambda: self._slap(n + 1))
        else:
            self.after_slap(0.80, lambda: self._slap(4))

    def _after_slaps(self):
        self.victim_av.mood = "lose"
        set_label(self.slap_count, "KO")

    # ------------------------------------------------------------- actions
    def _play_again(self):
        self.app.audio.click()
        self._cancel_slaps()
        self.confetti.stop()
        if self.data.get("mode") == "friend":
            if not self.app.link:
                self.app.toast(self.app.t("disconnected"))
                self.app.go("lobby", "left")
                return
            self._sent_req = True
            self._rematch_started = False
            set_label(self.status, self.app.t("rematch_wait"))
            self.app.link.send({"t": "rematch_req"})
        else:
            self.app.start_robot_match(self.app.difficulty)

    def _home(self):
        self.app.audio.click()
        self._cancel_slaps()
        self._seq_active = False
        self.confetti.stop()
        try:
            if self.app.link:
                self.app.link.send({"t": "bye"})
        except Exception:
            pass
        self.app.close_link()
        self.app.go("splash", "right")

    def _start_rematch(self):
        if self._rematch_started:
            return
        self._rematch_started = True
        self._cancel_slaps()
        self._seq_active = False
        self.confetti.stop()
        self.app.start_friend_match()

    # ---------------------------------------------------------------- net
    def handle_net_message(self, msg):
        if not isinstance(msg, dict):
            return
        t = msg.get("t")
        if t == "rematch_req":
            if self.app.net_role == "host":
                try:
                    self.app.link.send({"t": "rematch_go"})
                except Exception:
                    pass
                self._start_rematch()
            else:
                if not self._sent_req:
                    self._sent_req = True
                    try:
                        self.app.link.send({"t": "rematch_req"})
                    except Exception:
                        pass
                set_label(self.status, self.app.t("rematch_wait"))
        elif t == "rematch_go":
            self._start_rematch()
        elif t == "bye":
            self.on_peer_left()

    def on_peer_left(self):
        self.app.toast(self.app.t("disconnected"))
        self.app.close_link()
        self.app.go("lobby", "right")

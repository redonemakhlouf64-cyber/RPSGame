"""The arena: pseudo-3D hands, rounds, robot brain and online duels."""
from __future__ import annotations

import math
import random

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color as GColor, Ellipse, Line
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget

from config import (BEATS, CHARACTERS_BY_ID, GESTURES, TARGET_WINS, TCP_PORT)
from logic.rps_engine import Match, beats
from logic.robot_ai import RobotAI
from screens.base import BaseScreen, confirm_dialog
from ui.avatars import CharacterAvatar
from ui.hand_3d import Hand3D
from ui.theme import CYAN, DARK, GOLD, MAGENTA, MUTED, RED, WHITE, U, canvas_draw, rgba
from ui.widgets import (Card, GlowDot, PillButton, RobotIcon, ScorePips, label,
                        set_label)

ROBOT_CHAR = {
    "id": "robot",
    "name": "ROBOT",
    "gender": "boy",
    "skin": "#B9C7DA",
    "skin_dark": "#7C8CA8",
    "skin_light": "#EAF2FF",
    "hair": "#1A2A44",
    "outfit": "#1D3557",
    "outfit_dark": "#0E1F35",
    "accent": CYAN,
    "tag": "Machine brain",
}


class ArenaFloor(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    @canvas_draw
    def _draw(self, *a):
        self.canvas.clear()
        w, h = self.size
        if w < 4:
            return
        horizon = self.y + h * 0.70
        # haze
        GColor(*rgba(CYAN, 0.05))
        Ellipse(pos=(self.x + w * 0.05, horizon - h * 0.10),
                size=(w * 0.9, h * 0.5))
        # perspective rays
        vx = self.x + w * 0.5
        for i in range(-7, 8):
            tx = vx + i * w * 0.12
            GColor(*rgba(CYAN, 0.06 if i % 2 else 0.10))
            Line(points=[vx, horizon, tx, self.y + h * 0.02],
                 width=max(1.0, U(0.8)))
        # horizontal depth lines
        for i in range(7):
            f = i / 7.0
            y = horizon - (horizon - self.y) * (f ** 1.6)
            GColor(*rgba(CYAN, 0.045 + 0.045 * f))
            Line(points=[self.x + w * 0.03, y, self.x + w * 0.97, y],
                 width=max(1.0, U(0.8)))
        # stage glow
        GColor(*rgba(MAGENTA, 0.07))
        Ellipse(pos=(self.x + w * 0.12, self.y + h * 0.02),
                size=(w * 0.76, h * 0.16))
        GColor(*rgba(CYAN, 0.09))
        Ellipse(pos=(self.x + w * 0.18, self.y + h * 0.045),
                size=(w * 0.64, h * 0.11))


class MoveButton(Card):
    def __init__(self, gesture, label_text, on_pick, side_skin=None, **kwargs):
        super().__init__(**kwargs)
        self.gesture = gesture
        self.on_pick = on_pick
        self.enabled = True
        self.hand = Hand3D(gesture=gesture, side="right", reveal=1.0, rot=0,
                           size_hint=(None, None), size=(U(62), U(72)))
        self.hand.pos_hint = {"center_x": 0.5, "top": 0.93}
        if side_skin:
            self.hand.set_character(side_skin)
        self.add_widget(self.hand)
        self.lbl = label(label_text, size=10, color=WHITE)
        self.lbl.pos_hint = {"center_x": 0.5, "y": 0.05}
        self.lbl.size_hint = (0.92, None)
        self.lbl.height = U(16)
        self.add_widget(self.lbl)
        self.border_color = rgba("#FFFFFF", 0.10)
        self.fill = rgba("#0F1B36", 0.80)

    def set_skin(self, char):
        self.hand.set_character(char)

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.opacity = 1.0 if enabled else 0.42
        self.border_color = rgba(CYAN, 0.22) if enabled else rgba("#FFFFFF", 0.06)

    def on_touch_down(self, touch):
        if not self.enabled:
            return False
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self.glow = 1.0
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self.glow = 0.0
            if self.enabled and self.collide_point(*touch.pos):
                self.on_pick(self.gesture)
            return True
        return super().on_touch_up(touch)


class GameplayScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="gameplay", **kwargs)
        self.match = Match(TARGET_WINS)
        self.ai = RobotAI("medium")
        self.busy = False
        self.local_move = None
        self.remote_move = None
        self._finished = False
        self._countdown = []
        self._opp_char = None

        # ---------------------------------------------------------- top bar
        self.exit_btn = PillButton(text="<", size=(U(36), U(34)),
                                   bg_color=rgba("#FFFFFF", 0.08),
                                   text_color=rgba(WHITE),
                                   border_color=rgba("#FFFFFF", 0.12),
                                   font_size=U(16), radius=12)
        self.exit_btn.pos_hint = {"x": 0.035, "top": 0.962}
        self.exit_btn.bind(on_release=self._exit)
        self.body.add_widget(self.exit_btn)

        self.round_lbl = label("", size=11, color=MUTED)
        self.round_lbl.pos_hint = {"center_x": 0.5, "top": 0.972}
        self.round_lbl.size_hint = (0.5, None)
        self.round_lbl.height = U(20)
        self.body.add_widget(self.round_lbl)

        self.mode_lbl = label("", size=9, color=CYAN)
        self.mode_lbl.pos_hint = {"right": 0.965, "top": 0.972}
        self.mode_lbl.size_hint = (0.4, None)
        self.mode_lbl.height = U(20)
        self.mode_lbl.halign = "right"
        self.mode_lbl.text_size = (U(150), None)
        self.body.add_widget(self.mode_lbl)

        # --------------------------------------------------------- scoreboard
        hud = Card(size_hint=(0.94, None), height=U(66),
                   pos_hint={"center_x": 0.5, "top": 0.947},
                   fill=rgba("#0C1730", 0.86), border_color=rgba(CYAN, 0.16))
        self.body.add_widget(hud)
        self.p_av = CharacterAvatar(char_id=app.character_id,
                                    size_hint=(None, None), size=(U(38), U(38)))
        self.p_av.pos_hint = {"x": 0.035, "center_y": 0.58}
        hud.add_widget(self.p_av)
        self.p_name = label("", size=11, color=WHITE)
        self.p_name.pos_hint = {"x": 0.15, "top": 0.82}
        self.p_name.size_hint = (0.28, None)
        self.p_name.height = U(16)
        self.p_name.halign = "left"
        self.p_name.text_size = (U(100), None)
        hud.add_widget(self.p_name)
        self.p_pips = ScorePips(score=0, target=TARGET_WINS,
                                size_hint=(None, None), size=(U(80), U(14)))
        self.p_pips.pos_hint = {"x": 0.15, "center_y": 0.27}
        hud.add_widget(self.p_pips)

        self.o_av_box = FloatLayout(size_hint=(None, None),
                                    size=(U(38), U(38)))
        self.o_av_box.pos_hint = {"right": 0.965, "center_y": 0.58}
        self.o_av = CharacterAvatar(char_id="kenji",
                                    size_hint=(None, None), size=(U(38), U(38)))
        self.o_av.pos_hint = {"x": 0, "y": 0}
        self.o_av_box.add_widget(self.o_av)
        self.o_robot = RobotIcon(size_hint=(None, None), size=(U(38), U(38)))
        self.o_robot.pos_hint = {"x": 0, "y": 0}
        self.o_av_box.add_widget(self.o_robot)
        hud.add_widget(self.o_av_box)
        self.o_name = label("", size=11, color=WHITE)
        self.o_name.pos_hint = {"right": 0.85, "top": 0.82}
        self.o_name.size_hint = (0.28, None)
        self.o_name.height = U(16)
        self.o_name.halign = "right"
        self.o_name.text_size = (U(100), None)
        hud.add_widget(self.o_name)
        self.o_pips = ScorePips(score=0, target=TARGET_WINS,
                                size_hint=(None, None), size=(U(80), U(14)),
                                tint=rgba(MAGENTA))
        self.o_pips.pos_hint = {"right": 0.85, "center_y": 0.27}
        hud.add_widget(self.o_pips)

        self.score_lbl = label("0 : 0", size=18, color=GOLD)
        self.score_lbl.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        hud.add_widget(self.score_lbl)

        # ------------------------------------------------------------- scene
        self.floor = ArenaFloor(size_hint=(1, 1))
        self.body.add_widget(self.floor)

        self.p_hand = Hand3D(side="left", gesture="rock", reveal=0.0, rot=-10,
                             size_hint=(None, None), size=(U(184), U(190)))
        self.p_hand.pos_hint = {"center_x": 0.285, "center_y": 0.525}
        self.body.add_widget(self.p_hand)
        self.o_hand = Hand3D(side="right", gesture="rock", reveal=0.0, rot=10,
                             size_hint=(None, None), size=(U(184), U(190)))
        self.o_hand.pos_hint = {"center_x": 0.715, "center_y": 0.525}
        self.body.add_widget(self.o_hand)

        self.p_gesture_lbl = label("", size=12, color=CYAN)
        self.p_gesture_lbl.pos_hint = {"center_x": 0.285, "center_y": 0.385}
        self.body.add_widget(self.p_gesture_lbl)
        self.o_gesture_lbl = label("", size=12, color=MAGENTA)
        self.o_gesture_lbl.pos_hint = {"center_x": 0.715, "center_y": 0.385}
        self.body.add_widget(self.o_gesture_lbl)

        self.banner = label("", size=30, color=WHITE)
        self.banner.pos_hint = {"center_x": 0.5, "center_y": 0.655}
        self.banner.size_hint = (0.94, None)
        self.banner.height = U(46)
        self.body.add_widget(self.banner)

        self.vs = label("VS", size=13, color=CYAN)
        self.vs.pos_hint = {"center_x": 0.5, "center_y": 0.50}
        self.vs.opacity = 0.85
        self.body.add_widget(self.vs)

        # ------------------------------------------------------------ picker
        self.status = self.T("choose_move", size=11, color=MUTED)
        self.status.pos_hint = {"center_x": 0.5, "top": 0.352}
        self.status.size_hint = (0.9, None)
        self.status.height = U(22)
        self.body.add_widget(self.status)

        grid = GridLayout(cols=3, spacing=U(7), size_hint=(0.94, None),
                          height=U(116),
                          pos_hint={"center_x": 0.5, "y": 0.045})
        self.move_buttons = {}
        for g in GESTURES:
            btn = MoveButton(g, app.t(g), self._choose_player,
                             side_skin=app.character)
            grid.add_widget(btn)
            self.move_buttons[g] = btn
            self._tr.append((btn.lbl, g))
        self.body.add_widget(grid)

        self.friend_chip = label("", size=9, color=CYAN)
        self.friend_chip.pos_hint = {"center_x": 0.5, "y": 0.012}
        self.friend_chip.size_hint = (0.9, None)
        self.friend_chip.height = U(14)
        self.friend_chip.opacity = 0.0
        self.body.add_widget(self.friend_chip)

        self._set_enabled(False)
        self._opp_char = CHARACTERS_BY_ID["kenji"]

    # ------------------------------------------------------------- lifecycle
    def prepare_robot(self, level):
        self.match = Match(TARGET_WINS)
        self.ai = RobotAI(level, seed=random.randint(1, 10 ** 9))
        self._opp_char = ROBOT_CHAR
        char = self.app.character
        self.p_hand.set_character(char)
        self.o_hand.set_character(ROBOT_CHAR)
        for btn in self.move_buttons.values():
            btn.set_skin(char)
        self._setup_opponent_visual(robot=True)
        self._reset_all()

    def prepare_friend(self):
        self.match = Match(TARGET_WINS)
        self._opp_char = CHARACTERS_BY_ID.get(
            (self.app.peer_hello or {}).get("char"), CHARACTERS_BY_ID["kenji"])
        char = self.app.character
        self.p_hand.set_character(char)
        self.o_hand.set_character(self._opp_char)
        for btn in self.move_buttons.values():
            btn.set_skin(char)
        self._setup_opponent_visual(robot=False)
        self._reset_all()
        self.friend_chip.opacity = 1.0
        set_label(self.friend_chip,
                  f"{self.app.t('connected_to')} · "
                  f"{'Bluetooth' if self.app.transport == 'bluetooth' else 'Wi-Fi'}")
        link = self.app.link
        if link:
            link.on_message = lambda msg: Clock.schedule_once(
                lambda dt: self.app.dispatch_net(msg), 0)
            link.on_close = lambda: Clock.schedule_once(
                lambda dt: self.app.dispatch_close(), 0)

    def _setup_opponent_visual(self, robot):
        is_robot = robot
        self.o_av.opacity = 0 if is_robot else 1
        self.o_robot.opacity = 1 if is_robot else 0
        if not is_robot:
            self.o_av.char_id = self._opp_char["id"]
        self.o_robot.size = self.o_av_box.size

    def _reset_all(self):
        self._finished = False
        self.busy = False
        self.local_move = None
        self.remote_move = None
        self.p_hand.gesture = "rock"
        self.o_hand.gesture = "rock"
        self.p_hand.reveal = 0.0
        self.o_hand.reveal = 0.0
        self.p_hand.glow = 0.0
        self.o_hand.glow = 0.0
        self.p_hand.rot = -10
        self.o_hand.rot = 10
        self.p_gesture_lbl.text = ""
        self.o_gesture_lbl.text = ""
        self.p_av.char_id = self.app.character_id
        self.p_av.glow = 0.0
        self.o_av.glow = 0.0
        self.p_av.mood = "idle"
        self.o_av.mood = "idle"
        self._update_hud()
        self._set_enabled(True)
        set_label(self.status, self.app.t("choose_move"))
        set_label(self.banner, f"{self.app.t('round')} 1")
        self.banner.color = rgba(WHITE)
        if self.app.mode == "robot":
            set_label(self.mode_lbl, self.app.t(self.app.difficulty))
        else:
            set_label(self.mode_lbl, self.app.t("vs_friend"))
        if self.friend_chip:
            self.friend_chip.opacity = 1.0 if self.app.mode == "friend" else 0.0

    def _update_hud(self, scores=None):
        if scores:
            self.match.scores = [scores[0], scores[1]]
        self.p_pips.score = self.match.scores[0]
        self.o_pips.score = self.match.scores[1]
        self.score_lbl.text = f"{self.match.scores[0]} : {self.match.scores[1]}"
        char = self.app.character
        set_label(self.p_name, char["name"])
        if self.app.mode == "robot":
            set_label(self.o_name, "ROBOT")
        else:
            set_label(self.o_name, self._opp_char.get("name", "RIVAL"))
        set_label(self.round_lbl,
                  f"{self.app.t('round')} {len(self.match.rounds) + 1}")

    def _set_enabled(self, enabled):
        for btn in self.move_buttons.values():
            btn.set_enabled(enabled)

    def on_leave(self, *args):
        self._cancel_countdown()
        super().on_leave(*args)

    def _cancel_countdown(self):
        for ev in self._countdown:
            try:
                ev.cancel()
            except Exception:
                pass
        self._countdown = []

    # -------------------------------------------------------------- choosing
    def _choose_player(self, gesture):
        if self.busy:
            return
        if self.app.mode == "friend" and not self.app.link:
            self.app.toast(self.app.t("disconnected"))
            return
        self.app.audio.click()
        self.busy = True
        self.local_move = gesture
        self.p_hand.gesture = gesture
        self._set_enabled(False)
        if self.app.mode == "robot":
            set_label(self.status, self.app.t("robot_thinking"))
            self._start_countdown()
        else:
            set_label(self.status, self.app.t("waiting_move"))
            self.app.link.send({"t": "move", "g": gesture,
                                "round": len(self.match.rounds) + 1})
            self._maybe_host_resolve()

    def _start_countdown(self):
        self.banner.color = rgba(GOLD)
        steps = ["3", "2", "1", "GO!"]
        for i, txt in enumerate(steps):
            ev = Clock.schedule_once(lambda dt, s=txt: self._count_tick(s),
                                     0.12 + i * 0.46)
            self._countdown.append(ev)
        ev = Clock.schedule_once(self._robot_reveal, 0.12 + len(steps) * 0.46)
        self._countdown.append(ev)

    def _count_tick(self, txt):
        if not self.busy:
            return
        set_label(self.banner, txt)
        self.banner.color = rgba(GOLD if txt != "GO!" else CYAN)
        self.app.audio.tick()
        # hands rise a little as tension builds
        if txt in ("2", "1"):
            target = 0.55 if txt == "2" else 0.75
            Animation(reveal=target, rot=(-4 if self.p_hand.side == "left" else 4),
                      d=0.30, t="out_quad").start(self.p_hand)
            Animation(reveal=target, rot=(4 if self.o_hand.side == "right" else -4),
                      d=0.30, t="out_quad").start(self.o_hand)

    def _robot_reveal(self, dt):
        if not self.busy:
            return
        player = self.local_move or "rock"
        opp = self.ai.next_move()
        self.ai.update(player, opp)
        w = beats(player, opp)
        result = 0 if w is None else (1 if w == player else 2)
        if result == 1:
            self.match.scores[0] += 1
        elif result == 2:
            self.match.scores[1] += 1
        self.match.rounds.append({"player": player, "opponent": opp,
                                  "winner": result})
        over = (self.match.scores[0] >= TARGET_WINS or
                self.match.scores[1] >= TARGET_WINS)
        if over:
            self.match.over = True
            self.match.match_winner = 1 if self.match.scores[0] >= TARGET_WINS else 2
        self._play_reveal(player, opp, result, over)

    # ---------------------------------------------------------- net protocol
    def handle_net_message(self, msg):
        if not isinstance(msg, dict):
            return
        t = msg.get("t")
        if t == "move" and self.app.mode == "friend":
            g = msg.get("g")
            if g in GESTURES and not self.busy:
                self.remote_move = g
                self._maybe_host_resolve()
        elif t == "round" and self.app.mode == "friend":
            self._apply_remote_round(msg)
        elif t == "bye":
            self.on_peer_left()
        # rematch messages are handled by the result screen

    def _maybe_host_resolve(self):
        if self.app.net_role != "host" or self.busy:
            return
        if not self.local_move or not self.remote_move:
            return
        p = self.local_move
        o = self.remote_move
        info = self.match.add_round(p, o)
        winner = None
        if self.match.over:
            winner = "host" if self.match.match_winner == 1 else "client"
        try:
            self.app.link.send({
                "t": "round",
                "p": p,
                "o": o,
                "scores": list(self.match.scores),
                "over": self.match.over,
                "winner": winner,
            })
        except Exception:
            pass
        self._play_reveal(p, o, info["result"], info["over"],
                          scores=info["scores"])

    def _apply_remote_round(self, msg):
        p_host = msg.get("p")
        p_client = msg.get("o")
        scores = msg.get("scores") or [0, 0]
        if p_host not in GESTURES or p_client not in GESTURES:
            return
        self.match.scores = [int(scores[1]), int(scores[0])]
        over = bool(msg.get("over"))
        self.match.over = over
        winner = msg.get("winner")
        if over:
            self.match.match_winner = 1 if winner == "client" else 2
        # Client's own move is the host's opponent move.
        w = beats(p_client, p_host)
        result = 0 if w is None else (1 if w == p_client else 2)
        self._play_reveal(p_client, p_host, result, over, scores=self.match.scores)

    def on_peer_left(self):
        if self.app.mode != "friend":
            return
        self._cancel_countdown()
        self.busy = True
        self.app.toast(self.app.t("disconnected"))
        self.app.close_link()
        self.app.go("lobby", "right")

    # -------------------------------------------------------------- reveal
    def _play_reveal(self, player, opponent, result, over=False, scores=None):
        self.busy = True
        self._cancel_countdown()
        self._set_enabled(False)
        self.p_hand.gesture = player
        self.o_hand.gesture = opponent
        self.p_hand.glow = 0.0
        self.o_hand.glow = 0.0
        self.app.audio.whoosh()
        Animation(reveal=1.0, rot=-6, d=0.20, t="out_back").start(self.p_hand)
        Animation(reveal=1.0, rot=6, d=0.20, t="out_back").start(self.o_hand)
        set_label(self.p_gesture_lbl, self.app.t(player))
        set_label(self.o_gesture_lbl, self.app.t(opponent))
        if result == 1:
            set_label(self.banner, f"{self.app.t('you')} +1")
            self.banner.color = rgba(CYAN)
            self.p_hand.glow = 1.0
            self.p_av.mood = "win"
            self.o_av.mood = "lose"
        elif result == 2:
            set_label(self.banner, f"{self.app.t('opponent')} +1")
            self.banner.color = rgba(MAGENTA)
            self.o_hand.glow = 1.0
            self.o_av.mood = "win"
            self.p_av.mood = "lose"
        else:
            set_label(self.banner, self.app.t("draw"))
            self.banner.color = rgba(GOLD)
            self.p_av.mood = "idle"
            self.o_av.mood = "idle"
        if scores is not None:
            self.match.scores = [scores[0], scores[1]]
        self._update_hud()
        if over:
            self._finished = True
            ev = Clock.schedule_once(lambda dt: self._finish(), 1.55)
            self._countdown.append(ev)
        else:
            ev = Clock.schedule_once(lambda dt: self._reset_round(), 1.75)
            self._countdown.append(ev)

    def _reset_round(self):
        if self._finished:
            return
        self.busy = False
        self.local_move = None
        self.remote_move = None
        self.p_hand.glow = 0.0
        self.o_hand.glow = 0.0
        Animation(reveal=0.0, rot=-10, d=0.25).start(self.p_hand)
        Animation(reveal=0.0, rot=10, d=0.25).start(self.o_hand)
        self.p_gesture_lbl.text = ""
        self.o_gesture_lbl.text = ""
        set_label(self.banner, f"{self.app.t('round')} {len(self.match.rounds) + 1}")
        self.banner.color = rgba(WHITE)
        self.p_av.mood = "idle"
        self.o_av.mood = "idle"
        self._update_hud()
        if self.app.mode == "friend" and not self.app.link:
            return
        self._set_enabled(True)
        set_label(self.status, self.app.t("choose_move"))

    def _finish(self):
        won = self.match.match_winner == 1
        data = {
            "mode": self.app.mode,
            "difficulty": self.app.difficulty,
            "player_char": self.app.character_id,
            "opponent_char": (self._opp_char or {}).get("id", "kenji"),
            "opponent_is_robot": self.app.mode == "robot",
            "player_score": self.match.scores[0],
            "opponent_score": self.match.scores[1],
            "player_won": won,
            "rounds": list(self.match.rounds),
        }
        self.app.show_result(data)

    # ---------------------------------------------------------------- exit
    def _exit(self):
        self.app.audio.click()
        confirm_dialog(
            self.app,
            self.app.t("exit_confirm"),
            self.app.t("exit_sub"),
            on_yes=self._leave_match,
            yes_key="yes", no_key="no")

    def _leave_match(self):
        self._cancel_countdown()
        self.busy = True
        try:
            if self.app.link:
                self.app.link.send({"t": "bye"})
        except Exception:
            pass
        self.app.close_link()
        self.app.go("splash", "right")

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._update_hud()
        if self.app.mode == "friend":
            self._set_enabled(self.app.link is not None)
            if not self.app.link:
                set_label(self.status, self.app.t("disconnected"))
            self.app.link and self.app.link.send(
                {"t": "ready", "round": len(self.match.rounds) + 1})
        else:
            self._set_enabled(not self.busy)

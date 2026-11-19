"""Bluetooth / Wi-Fi lobby: host, discover and join."""
from __future__ import annotations

import re

from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from config import APP_VERSION, TCP_PORT
from logic import network
from screens.base import BaseScreen
from ui.theme import CYAN, DARK, GREEN, MAGENTA, MUTED, WHITE, U, rgba
from ui.widgets import (Card, GlowDot, PillButton, Spinner, label, set_label)


class LobbyScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="lobby", **kwargs)
        self._role = None
        self._host = None
        self._responder = None
        self._bt_stop = None
        self._bt_started = False
        self._started = False
        self._join_mode = False
        self._scan_rows = []
        self._scanning = False
        self._timeout_ev = None
        self._bt_permissions_asked = False

        self.add_topbar("lobby", back=self._back)
        self.sub = self.T("lobby_sub", size=10, color=MUTED)
        self.sub.pos_hint = {"center_x": 0.5, "top": 0.922}
        self.sub.size_hint = (0.9, None)
        self.sub.height = U(18)
        self.body.add_widget(self.sub)

        # status card -------------------------------------------------------
        self.status_card = Card(size_hint=(0.9, None), height=U(62),
                                pos_hint={"center_x": 0.5, "top": 0.885},
                                fill=rgba("#0E1B35", 0.82),
                                border_color=rgba(CYAN, 0.22))
        self.body.add_widget(self.status_card)
        self.dot = GlowDot(size_hint=(None, None), size=(U(12), U(12)),
                           tint=rgba(GREEN))
        self.dot.pos_hint = {"x": 0.045, "center_y": 0.68}
        self.status_card.add_widget(self.dot)
        self.status_lbl = label("", size=11, color=WHITE)
        self.status_lbl.pos_hint = {"x": 0.13, "top": 0.86}
        self.status_lbl.size_hint = (0.64, None)
        self.status_lbl.height = U(20)
        self.status_lbl.halign = "left"
        self.status_lbl.text_size = (U(250), None)
        self.status_card.add_widget(self.status_lbl)
        self.transport_lbl = label("", size=9, color=MUTED)
        self.transport_lbl.pos_hint = {"x": 0.13, "top": 0.48}
        self.transport_lbl.size_hint = (0.64, None)
        self.transport_lbl.height = U(16)
        self.transport_lbl.halign = "left"
        self.transport_lbl.text_size = (U(250), None)
        self.status_card.add_widget(self.transport_lbl)
        self.perm_btn = PillButton(text=app.t("permission"),
                                   size=(U(140), U(26)),
                                   bg_color=rgba(MAGENTA, 0.20),
                                   text_color=rgba(MAGENTA),
                                   border_color=rgba(MAGENTA, 0.45),
                                   font_size=U(8), radius=8)
        self.perm_btn.pos_hint = {"right": 0.97, "center_y": 0.5}
        self.perm_btn.bind(on_release=self._ask_bt)
        self.reg(self.perm_btn, "permission")
        self.status_card.add_widget(self.perm_btn)

        # host / join switch ------------------------------------------------
        self.host_btn = PillButton(text=app.t("host"), size=(U(170), U(48)),
                                   bg_color=rgba(CYAN), text_color=rgba(DARK),
                                   font_size=U(13), radius=14)
        self.host_btn.pos_hint = {"center_x": 0.27, "top": 0.80}
        self.host_btn.bind(on_release=lambda *a: self._show_panel(False))
        self.body.add_widget(self.host_btn)
        self.reg(self.host_btn, "host")
        self.join_btn = PillButton(text=app.t("join"), size=(U(170), U(48)),
                                   bg_color=rgba("#FFFFFF", 0.08),
                                   text_color=rgba(WHITE),
                                   border_color=rgba("#FFFFFF", 0.14),
                                   font_size=U(13), radius=14)
        self.join_btn.pos_hint = {"center_x": 0.73, "top": 0.80}
        self.join_btn.bind(on_release=lambda *a: self._show_panel(True))
        self.body.add_widget(self.join_btn)
        self.reg(self.join_btn, "join")

        self.panel_area = FloatLayout(size_hint=(1, 1))
        self.body.add_widget(self.panel_area)

        # ------------------------------------------------------------ host
        self.host_panel = FloatLayout(size_hint=(1, 1))
        self.panel_area.add_widget(self.host_panel)
        host_card = Card(size_hint=(0.9, None), height=U(250),
                         pos_hint={"center_x": 0.5, "top": 0.70},
                         fill=rgba("#0C1730", 0.78),
                         border_color=rgba(CYAN, 0.18))
        self.host_panel.add_widget(host_card)
        self.host_spinner = Spinner(active=True, size_hint=(None, None),
                                    size=(U(46), U(46)))
        self.host_spinner.pos_hint = {"center_x": 0.5, "top": 0.87}
        host_card.add_widget(self.host_spinner)
        self.host_wait = self.T("host_wait", size=12, color=WHITE)
        self.host_wait.pos_hint = {"center_x": 0.5, "top": 0.76}
        self.host_wait.size_hint = (0.86, None)
        self.host_wait.height = U(38)
        self.host_wait.text_size = (U(320), None)
        host_card.add_widget(self.host_wait)
        self.ip_lbl = label("", size=22, color=CYAN)
        self.ip_lbl.pos_hint = {"center_x": 0.5, "top": 0.56}
        self.ip_lbl.size_hint = (0.9, None)
        self.ip_lbl.height = U(28)
        host_card.add_widget(self.ip_lbl)
        self.ip_sub = label("", size=9, color=MUTED)
        self.ip_sub.pos_hint = {"center_x": 0.5, "top": 0.45}
        self.ip_sub.size_hint = (0.9, None)
        self.ip_sub.height = U(16)
        host_card.add_widget(self.ip_sub)
        self.start_host_btn = PillButton(text=app.t("host"),
                                         size=(U(176), U(44)),
                                         bg_color=rgba(CYAN), text_color=rgba(DARK),
                                         font_size=U(13), radius=13)
        self.start_host_btn.pos_hint = {"center_x": 0.5, "top": 0.39}
        self.start_host_btn.bind(on_release=lambda *a: self.start_host())
        host_card.add_widget(self.start_host_btn)
        self.reg(self.start_host_btn, "host")
        self.cancel_host = PillButton(text=app.t("cancel"),
                                      size=(U(150), U(36)),
                                      bg_color=rgba("#FFFFFF", 0.07),
                                      text_color=rgba(MUTED),
                                      border_color=rgba("#FFFFFF", 0.12),
                                      font_size=U(11), radius=12)
        self.cancel_host.pos_hint = {"center_x": 0.5, "y": 0.04}
        self.cancel_host.bind(on_release=lambda *a: self._stop_all())
        host_card.add_widget(self.cancel_host)
        self.reg(self.cancel_host, "cancel")

        # ------------------------------------------------------------ join
        self.join_panel = FloatLayout(size_hint=(1, 1))
        join_card = Card(size_hint=(0.9, 0.60), pos_hint={"center_x": 0.5, "top": 0.70},
                         fill=rgba("#0C1730", 0.78),
                         border_color=rgba(MAGENTA, 0.20))
        self.join_panel.add_widget(join_card)

        self.scan_btn = PillButton(text=app.t("scan"), size=(U(140), U(40)),
                                   bg_color=rgba(MAGENTA), text_color=rgba(WHITE),
                                   font_size=U(12), radius=12)
        self.scan_btn.pos_hint = {"x": 0.05, "top": 0.93}
        self.scan_btn.bind(on_release=lambda *a: self._scan())
        join_card.add_widget(self.scan_btn)
        self.reg(self.scan_btn, "scan")
        self.scan_spinner = Spinner(active=False, size_hint=(None, None),
                                    size=(U(30), U(30)), tint=rgba(MAGENTA))
        self.scan_spinner.pos_hint = {"x": 0.46, "top": 0.91}
        join_card.add_widget(self.scan_spinner)
        self.scan_status = label("", size=9, color=MUTED)
        self.scan_status.pos_hint = {"x": 0.58, "top": 0.91}
        self.scan_status.size_hint = (0.38, None)
        self.scan_status.height = U(20)
        self.scan_status.halign = "left"
        self.scan_status.text_size = (U(160), None)
        join_card.add_widget(self.scan_status)

        self.results_scroll = ScrollView(size_hint=(1, None), height=U(170),
                                         pos_hint={"x": 0, "top": 0.83},
                                         do_scroll_x=False, bar_width=U(2))
        self.results_grid = GridLayout(cols=1, spacing=U(6), size_hint_y=None,
                                       padding=(U(10), 0, U(10), 0))
        self.results_grid.bind(minimum_height=self.results_grid.setter("height"))
        self.results_scroll.add_widget(self.results_grid)
        join_card.add_widget(self.results_scroll)
        self.no_games = label(app.t("not_found"), size=9, color=MUTED)
        self.no_games.pos_hint = {"center_x": 0.5, "top": 0.55}
        self.no_games.size_hint = (0.86, None)
        self.no_games.height = U(50)
        self.no_games.text_size = (U(300), None)
        join_card.add_widget(self.no_games)
        self.reg(self.no_games, "not_found")

        # manual connect row (inside join card)
        self.ip_input = TextInput(
            text="", multiline=False, size_hint=(None, None),
            size=(U(190), U(40)), pos_hint={"x": 0.05, "y": 0.08},
            font_size=U(13), background_color=rgba("#FFFFFF", 0.06),
            foreground_color=rgba(WHITE), cursor_color=rgba(CYAN),
            hint_text="192.168.1.10", hint_text_color=rgba(MUTED, 0.7),
            padding=[U(10), U(10)])
        join_card.add_widget(self.ip_input)
        self.connect_btn = PillButton(text=app.t("connect"),
                                      size=(U(120), U(40)),
                                      bg_color=rgba(CYAN), text_color=rgba(DARK),
                                      font_size=U(11), radius=12)
        self.connect_btn.pos_hint = {"right": 0.95, "y": 0.08}
        self.connect_btn.bind(on_release=lambda *a: self._manual_connect())
        join_card.add_widget(self.connect_btn)
        self.reg(self.connect_btn, "connect")

        self.bt_hint = label(app.t("bt_scan_hint"), size=8, color=MUTED)
        self.bt_hint.pos_hint = {"center_x": 0.5, "top": 0.23}
        self.bt_hint.size_hint = (0.9, None)
        self.bt_hint.height = U(18)
        self.bt_hint.opacity = 0.8
        join_card.add_widget(self.bt_hint)
        self.reg(self.bt_hint, "bt_scan_hint")

        self.panel_area.remove_widget(self.join_panel)
        self._show_panel(False)

    # ------------------------------------------------------------ lifecycle
    def _show_panel(self, join: bool):
        if join and (self._host is not None or self.app.link is not None):
            self._stop_all()
        self._join_mode = join
        self.app.audio.click()
        if join:
            if self.host_panel in self.panel_area.children:
                self.panel_area.remove_widget(self.host_panel)
            if self.join_panel not in self.panel_area.children:
                self.panel_area.add_widget(self.join_panel)
            self.host_btn.bg_color = rgba("#FFFFFF", 0.08)
            self.host_btn.text_color = rgba(WHITE)
            self.join_btn.bg_color = rgba(MAGENTA)
            self.join_btn.text_color = rgba(WHITE)
        else:
            if self.join_panel in self.panel_area.children:
                self.panel_area.remove_widget(self.join_panel)
            if self.host_panel not in self.panel_area.children:
                self.panel_area.add_widget(self.host_panel)
            self.join_btn.bg_color = rgba("#FFFFFF", 0.08)
            self.join_btn.text_color = rgba(WHITE)
            self.host_btn.bg_color = rgba(CYAN)
            self.host_btn.text_color = rgba(DARK)

    def _refresh_status(self):
        bt = network.bt_available()
        try:
            act = network.get_activity()
        except Exception:
            act = None
        if bt:
            set_label(self.status_lbl, self.app.t("bt_ready"))
            self.dot.tint = rgba(GREEN)
        else:
            set_label(self.status_lbl, self.app.t("wifi_ready"))
            self.dot.tint = rgba(CYAN)
        set_label(self.transport_lbl, self.app.t("lobby_sub"))
        if act is None:
            self.perm_btn.opacity = 0
            self.perm_btn.disabled = True
        else:
            self.perm_btn.opacity = 1
            self.perm_btn.disabled = False

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._started = False
        self._role = None
        self._refresh_status()
        self._reset_host()
        self._reset_join()
        self._show_panel(self._join_mode)
        if self._join_mode:
            self._scan()

    def on_leave(self, *args):
        # Hand-off to gameplay keeps the link, everything else tears down.
        if not self._started:
            self._close_all()
        else:
            self._stop_listeners()
        super().on_leave(*args)

    def _back(self):
        self.app.audio.click()
        self._close_all()
        self.go("mode", "right")

    # --------------------------------------------------------------- host
    def _reset_host(self):
        set_label(self.host_wait, self.app.t("lobby_sub"))
        self.host_spinner.active = False
        self.ip_lbl.text = ""
        self.ip_sub.text = ""
        self.start_host_btn.opacity = 1
        self.start_host_btn.disabled = False
        self.cancel_host.opacity = 0
        self.cancel_host.disabled = True
        self.status_card.glow = 0.0

    def start_host(self):
        if self._host is not None:
            return
        self.app.audio.click()
        self._close_all()
        self._started = False
        self._role = "host"
        set_label(self.host_wait, self.app.t("host_wait"))
        self.start_host_btn.opacity = 0
        self.start_host_btn.disabled = True
        self.cancel_host.opacity = 1
        self.cancel_host.disabled = False
        self.host_spinner.active = True
        self.ip_lbl.text = f"{network.get_local_ip()}:{TCP_PORT}"
        self.ip_sub.text = ("TCP + Bluetooth listening"
                            if network.bt_available() else "Wi-Fi / hotspot listening")
        self.status_card.glow = 0.7
        self._host = network.TcpHost(TCP_PORT)
        self._host.start(self._on_link, self._on_host_error)
        self._responder = network.DiscoveryResponder(
            name=f"{network.device_label()} RPS")
        self._responder.start()
        # Try the native RFCOMM listener too; TCP remains the safety net.
        if network.bt_available():
            try:
                self._bt_stop = network.bt_host(self._on_link, self._on_bt_error)
                self._bt_started = True
            except Exception:
                self._bt_stop = None

    def _stop_all(self):
        self._close_all()
        self._reset_host()
        self._reset_join()
        self.status_card.glow = 0.0

    def _on_host_error(self, exc):
        Clock.schedule_once(lambda dt: self._toast(
            f"{self.app.t('host_error')}{exc}"), 0)

    def _on_bt_error(self, exc):
        pass

    def _stop_listeners(self):
        for obj in (self._host, self._responder):
            try:
                if obj:
                    obj.stop()
            except Exception:
                pass
        self._host = None
        self._responder = None
        if self._bt_stop:
            try:
                self._bt_stop()
            except Exception:
                pass
        self._bt_stop = None
        self._bt_started = False

    def _close_all(self):
        self._stop_listeners()
        if self._timeout_ev:
            try:
                self._timeout_ev.cancel()
            except Exception:
                pass
            self._timeout_ev = None
        try:
            if self.app.link:
                self.app.link.close()
        except Exception:
            pass
        self.app.link = None
        self._role = None

    # --------------------------------------------------------------- join
    def _reset_join(self):
        self._clear_results()
        self.scan_spinner.active = False
        self.scan_status.text = ""
        self.no_games.opacity = 1
        self.scan_btn.disabled = False
        set_label(self.no_games, self.app.t("not_found"))
        set_label(self.scan_btn, self.app.t("scan"))

    def _clear_results(self):
        for row in list(self.results_grid.children):
            self.results_grid.remove_widget(row)

    def _scan(self):
        if self._scanning:
            return
        self.app.audio.click()
        self._scanning = True
        self.scan_btn.disabled = True
        self.scan_spinner.active = True
        set_label(self.scan_status, self.app.t("scanning"))
        self.scan_status.color = rgba(CYAN)
        self._clear_results()

        def work():
            games = network.discover_games(2.4)
            paired = network.bt_paired_devices() if network.bt_available() else []
            Clock.schedule_once(lambda dt: self._scan_done(games, paired), 0)

        import threading
        threading.Thread(target=work, daemon=True).start()

    def _scan_done(self, games, paired):
        self._scanning = False
        self.scan_spinner.active = False
        self.scan_btn.disabled = False
        set_label(self.scan_btn, self.app.t("scan"))
        self._clear_results()
        for game in games:
            row = PillButton(
                text=f"{game['name']}   ·   {game['ip']}:{game['port']}",
                size=(U(370), U(42)), font_size=U(10),
                bg_color=rgba(CYAN, 0.10), text_color=rgba(WHITE),
                border_color=rgba(CYAN, 0.30), radius=10)
            row.size_hint = (1, None)
            row.bind(on_release=lambda inst, g=game: self._join_tcp(g["ip"], g["port"]))
            self.results_grid.add_widget(row)
        for dev in paired:
            row = PillButton(
                text=f"BT · {dev['name']}   ·   {dev['address']}",
                size=(U(370), U(42)), font_size=U(10),
                bg_color=rgba(MAGENTA, 0.10), text_color=rgba(WHITE),
                border_color=rgba(MAGENTA, 0.30), radius=10)
            row.size_hint = (1, None)
            row.bind(on_release=lambda inst, d=dev: self._join_bt(d["address"]))
            self.results_grid.add_widget(row)
        self.no_games.opacity = 0 if (games or paired) else 1
        if not games and not paired:
            set_label(self.scan_status, self.app.t("not_found"))
            self.scan_status.color = rgba(MUTED)
        else:
            self.scan_status.text = ""

    def _join_tcp(self, ip, port):
        self.app.audio.click()
        self._role = "client"
        self._clear_results()
        self.no_games.opacity = 1
        set_label(self.no_games, self.app.t("waiting"))
        self._mode_indicator()
        network.join_tcp(ip, port, self._on_link,
                         lambda exc: Clock.schedule_once(
                             lambda dt: self._join_failed(exc), 0))

    def _join_bt(self, address):
        self.app.audio.click()
        self._role = "client"
        self._clear_results()
        self.no_games.opacity = 1
        set_label(self.no_games, self.app.t("waiting"))
        self._mode_indicator()
        network.bt_join(address, self._on_link,
                        lambda exc: Clock.schedule_once(
                            lambda dt: self._join_failed(exc), 0))

    def _manual_connect(self):
        raw = (self.ip_input.text or "").strip()
        if not raw:
            self._toast(self.app.t("invalid_ip"))
            return
        match = re.match(r"^(\d{1,3}(?:\.\d{1,3}){3})(?::(\d+))?$", raw)
        if not match:
            self._toast(self.app.t("invalid_ip"))
            return
        ip = match.group(1)
        port = int(match.group(2) or TCP_PORT)
        if any(int(p) > 255 for p in ip.split(".")):
            self._toast(self.app.t("invalid_ip"))
            return
        self._join_tcp(ip, port)

    def _join_failed(self, exc):
        self.host_spinner.active = False
        self.scan_spinner.active = False
        self.scan_btn.disabled = False
        self._toast(f"{self.app.t('join_error')}{exc}")
        set_label(self.no_games, self.app.t("not_found"))
        self.no_games.opacity = 1

    def _mode_indicator(self):
        set_label(self.scan_status, self.app.t("waiting"))
        self.scan_status.color = rgba(CYAN)
        self.scan_spinner.active = True
        self.scan_btn.disabled = True

    # ---------------------------------------------------------- handshake
    def _on_link(self, link):
        if self._started or self.app.link is not None:
            try:
                link.close()
            except Exception:
                pass
            return
        Clock.schedule_once(lambda dt: self._attach(link), 0)

    def _attach(self, link):
        self._stop_listeners()
        self.app.link = link
        self.app.net_role = self._role or "host"
        self.app.transport = link.transport
        self._started = False
        self.host_spinner.active = True
        self.scan_spinner.active = False
        self.scan_btn.disabled = False
        set_label(self.host_wait, self.app.t("waiting"))
        self.ip_lbl.text = self.app.t("connected_to")
        self.ip_sub.text = "Bluetooth" if link.transport == "bluetooth" else "Wi-Fi / TCP"
        self.status_card.glow = 1.0
        set_label(self.status_lbl, self.app.t("waiting"))
        set_label(self.scan_status, self.app.t("waiting"))
        self.dot.tint = rgba(GREEN)
        link.on_message = lambda msg: Clock.schedule_once(
            lambda dt: self._on_message(msg), 0)
        link.on_close = lambda: Clock.schedule_once(lambda dt: self._on_close(), 0)
        link.send({
            "t": "hello",
            "name": network.device_label(),
            "char": self.app.character_id,
            "lang": self.app.lang,
            "ver": APP_VERSION,
        })
        if self._timeout_ev:
            try:
                self._timeout_ev.cancel()
            except Exception:
                pass
        self._timeout_ev = Clock.schedule_once(self._handshake_timeout, 9.0)

    def _on_message(self, msg):
        if not isinstance(msg, dict):
            return
        if msg.get("t") == "hello":
            self.app.peer_hello = msg
            self._start_match()
        elif msg.get("t") == "bye":
            self._peer_gone()

    def _start_match(self):
        if self._started:
            return
        self._started = True
        if self._timeout_ev:
            try:
                self._timeout_ev.cancel()
            except Exception:
                pass
            self._timeout_ev = None
        self.app.peer_hello = self.app.peer_hello or {}
        self.app.audio.win()
        self._toast(self.app.t("connected_to"))
        self.app.start_friend_match()

    def _handshake_timeout(self, dt):
        if self._started:
            return
        self._toast(self.app.t("disconnected"))
        self._close_all()
        self._reset_host()
        self._reset_join()

    def _on_close(self):
        if self._started:
            return
        self.host_spinner.active = False
        self._toast(self.app.t("disconnected"))
        self.app.link = None
        self.status_card.glow = 0.0
        self._reset_host()
        self._reset_join()

    def _peer_gone(self):
        if self.app.link:
            self.app.link.close()
        self.app.link = None
        self._toast(self.app.t("disconnected"))
        self.go("mode", "right")

    def _ask_bt(self, *a):
        self.app.audio.click()
        self._bt_permissions_asked = True
        wanted = network.request_bt_permissions()
        if wanted:
            self._toast("Allow Bluetooth in the Android dialog")
        else:
            self._toast(self.app.t("bt_unavailable"))
        self.after(1.0, self._refresh_status)

    def _toast(self, text):
        self.app.toast(text)

    def _toast_key(self, key):
        self.app.toast(self.app.t(key))

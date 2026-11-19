"""Headless validation: rules, AI, storage, audio assets and networking.

Run:  python main.py --headless-test
"""
from __future__ import annotations

import json
import os
import random
import socket
import sys
import threading
import time
import traceback
import wave

from config import (ASSETS_DIR, BEATS, CHARACTERS, GESTURES, HISTORY_FILE,
                    SETTINGS_FILE, TARGET_WINS)
from logic import assets_gen, i18n
from logic.robot_ai import RobotAI
from logic.rps_engine import Match, beats, counter_for, round_result


class Report:
    def __init__(self):
        self.pass_count = 0
        self.fail_count = 0
        self.warnings = []

    def ok(self, name, cond, detail=""):
        if cond:
            self.pass_count += 1
            print(f"  [PASS] {name}")
        else:
            self.fail_count += 1
            print(f"  [FAIL] {name}  {detail}")

    def warn(self, msg):
        self.warnings.append(msg)
        print(f"  [WARN] {msg}")


def test_syntax(rep: Report):
    print("\n[1/7] Syntax check")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = []
    files = 0
    for dirpath, _dirs, names in os.walk(root):
        if any(part in dirpath for part in ("__pycache__", "/assets", "/shots")):
            continue
        for name in names:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            files += 1
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    compile(fh.read(), path, "exec")
            except Exception as exc:
                bad.append((path, exc))
    rep.ok(f"compiled {files} python files", not bad,
           "; ".join(f"{p}: {e}" for p, e in bad[:3]))


def test_engine(rep: Report):
    print("\n[2/7] RPS engine")
    rep.ok("rock beats scissors", beats("rock", "scissors") == "rock")
    rep.ok("paper beats rock", beats("paper", "rock") == "paper")
    rep.ok("scissors beats paper", beats("scissors", "paper") == "scissors")
    rep.ok("draws detected", beats("rock", "rock") is None)
    rep.ok("round_result maps to 1/2/0",
           round_result("rock", "scissors") == 1 and
           round_result("rock", "paper") == 2 and
           round_result("paper", "paper") == 0)
    m = Match(3)
    for _ in range(3):
        info = m.add_round("rock", "scissors")
    rep.ok("first to 3 ends match",
           m.over and m.match_winner == 1 and m.scores == [3, 0], str(m.scores))
    m2 = Match(3)
    results = [m2.add_round(*p) for p in
               (("rock", "paper"), ("paper", "scissors"), ("scissors", "rock"))]
    rep.ok("opponent can win a match", m2.over and m2.match_winner == 2)
    for c in GESTURES:
        rep.ok(f"counter_for({c})", beats(counter_for(c), c) == counter_for(c))


def _simulate(level, policy, rounds=4000, seed=7):
    ai = RobotAI(level, seed=seed)
    hist = []
    wins = losses = draws = 0
    rng = random.Random(seed + 1)
    for _ in range(rounds):
        player = policy(hist, ai.ai_moves, rng)
        bot = ai.next_move(hist)
        w = beats(player, bot)
        if w is None:
            draws += 1
        elif w == player:
            wins += 1
        else:
            losses += 1
        hist.append(player)
        ai.update(player, bot)
    decided = max(1, wins + losses)
    return wins / decided


def test_ai(rep: Report):
    print("\n[3/7] Robot brains")

    def p_random(hist, ai_moves, rng):
        return rng.choice(GESTURES)

    def p_copy(hist, ai_moves, rng):
        return hist[-1] if hist else rng.choice(GESTURES)

    def p_counter_ai(hist, ai_moves, rng):
        return counter_for(ai_moves[-1]) if ai_moves else rng.choice(GESTURES)

    def p_freq(hist, ai_moves, rng):
        if len(hist) < 3:
            return rng.choice(GESTURES)
        counts = {g: hist.count(g) for g in GESTURES}
        predict = max(GESTURES, key=lambda g: counts[g])
        return counter_for(predict)

    rates = {}
    for level in ("beginner", "medium", "strong", "very_strong"):
        rates[level] = _simulate(level, p_random, rounds=2500)
        rep.ok(f"{level} never crashes / valid rate",
               0.0 <= rates[level] <= 1.0, str(rates[level]))
    print("    AI win-rate vs random:", {k: round(v, 3) for k, v in rates.items()})

    vs_copy = _simulate("very_strong", p_copy)
    vs_counter_ai = _simulate("very_strong", p_counter_ai)
    vs_freq = _simulate("very_strong", p_freq)
    print(f"    very_strong vs copy-last (player win rate): {vs_copy:.3f}")
    print(f"    very_strong vs counter-bot (player win rate): {vs_counter_ai:.3f}")
    print(f"    very_strong vs frequency-counter (player win rate): {vs_freq:.3f}")
    rep.ok("very_strong punishes copy-last player", vs_copy < 0.15, f"{vs_copy:.3f}")
    rep.ok("very_strong adapts to counter-bot", vs_counter_ai < 0.35,
           f"{vs_counter_ai:.3f}")
    rep.ok("very_strong exploits frequency patterns", vs_freq < 0.18,
           f"{vs_freq:.3f}")
    medium_vs_copy = _simulate("medium", p_copy)
    rep.ok("very_strong is harder than medium", medium_vs_copy > vs_copy + 0.05,
           f"medium {medium_vs_copy:.3f} vs very {vs_copy:.3f}")


def test_audio(rep: Report):
    print("\n[4/7] Procedural assets")
    made = assets_gen.ensure_all()
    missing = []
    tiny = []
    hashes = set()
    for name in assets_gen.SOUND_FILES:
        path = assets_gen.sound_path(name)
        if not os.path.exists(path):
            missing.append(name)
            continue
        if os.path.getsize(path) < 1500:
            tiny.append(name)
        if name.startswith("scream_"):
            with open(path, "rb") as fh:
                hashes.add(hash(fh.read()))
    rep.ok("all sound files generated", not missing, str(missing))
    rep.ok("sound files contain audio", not tiny, str(tiny))
    rep.ok("six character screams (+robot) are unique", len(hashes) >= 7,
           str(len(hashes)))
    try:
        with wave.open(assets_gen.sound_path("scream_amara"), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
        rep.ok("scream is a valid 22 kHz wav", rate == 22050 and frames > 10000,
               f"{rate}Hz {frames} frames")
    except Exception as exc:
        rep.ok("scream wav readable", False, str(exc))
    rep.ok("asset manifest written",
           os.path.exists(os.path.join(ASSETS_DIR, "manifest.json")))
    print(f"    assets: {ASSETS_DIR}")


def test_storage(rep: Report):
    print("\n[5/7] Persistence")
    from logic.storage import Store
    st = Store()
    before = st.settings
    st.set("_selftest_probe", 123)
    st2 = Store()
    rep.ok("settings round-trip to disk", st2.get("_selftest_probe") == 123)
    st.set_many(before)
    rep.ok("settings file exists", os.path.exists(SETTINGS_FILE))
    rep.ok("history file path accessible", os.path.isdir(os.path.dirname(HISTORY_FILE)))


def test_i18n(rep: Report):
    print("\n[6/7] Languages")
    keys = ("start", "choose_fighter", "rock", "paper", "scissors",
            "you_win", "you_lose", "play_again", "home", "host", "join",
            "scan", "connected_to", "waiting", "draw")
    bad = []
    for code, native, english, badge in i18n.LANGUAGES:
        for key in keys:
            if not i18n.t(code, key):
                bad.append((code, key))
    rep.ok(f"{len(i18n.LANGUAGES)} languages resolve core strings", not bad, str(bad[:5]))
    rep.ok("cat language is a real joke language",
           "MEOW" in i18n.t("cat", "start").upper())
    rep.ok("unknown key falls back gracefully", i18n.t("en", "no_such_key") == "no_such_key")


def test_network(rep: Report):
    print("\n[7/7] Multiplayer transport")
    from logic import network

    # free port
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    results = {}
    host_link_ready = threading.Event()
    client_link_ready = threading.Event()
    close_seen = threading.Event()
    host_msg = threading.Event()
    client_msg = threading.Event()
    host = network.TcpHost(port)

    def on_host_link(link):
        results["host_link"] = link
        link.on_message = lambda m: (results.__setitem__("host_got", m), host_msg.set())
        link.on_close = lambda: close_seen.set()
        host_link_ready.set()

    host.start(on_host_link, lambda e: results.__setitem__("host_err", e))

    def on_client_link(link):
        results["client_link"] = link
        link.on_message = lambda m: (results.__setitem__("client_got", m), client_msg.set())
        client_link_ready.set()

    time.sleep(0.15)
    network.join_tcp("127.0.0.1", port, on_client_link,
                     lambda e: results.__setitem__("client_err", e))
    ok_connect = host_link_ready.wait(4) and client_link_ready.wait(4)
    rep.ok("host/client TCP handshake", ok_connect, str(results.get("host_err") or results.get("client_err")))
    if ok_connect:
        hello = {"t": "hello", "char": "amara", "scores": [0, 0]}
        results["client_link"].send(hello)
        got = host_msg.wait(3)
        rep.ok("messages travel client -> host", got and
               results.get("host_got", {}).get("char") == "amara")
        results["host_link"].send({"t": "round", "p": "rock", "o": "scissors",
                                   "scores": [1, 0]})
        got2 = client_msg.wait(3)
        rep.ok("messages travel host -> client", got2 and
               results.get("client_got", {}).get("p") == "rock")
        results["client_link"].close()
        rep.ok("disconnect is detected", close_seen.wait(3))
    host.stop()

    # discovery
    udp = 38999
    responder = network.DiscoveryResponder(port=udp, game_port=port, name="Test Room")
    responder.start()
    time.sleep(0.15)
    found = network.discover_games(timeout=1.0, port=udp)
    responder.stop()
    rep.ok("UDP room discovery responds", any(g.get("name") == "Test Room" for g in found),
           str(found))
    if not found:
        rep.warn("UDP broadcast blocked on this device; manual IP join still works")


def run_headless() -> bool:
    print("=" * 60)
    print(" RPS ARENA 3D -- headless self test")
    print("=" * 60)
    rep = Report()
    for fn in (test_syntax, test_engine, test_ai, test_audio, test_storage,
               test_i18n, test_network):
        try:
            fn(rep)
        except Exception:
            rep.fail_count += 1
            print(f"  [FAIL] {fn.__name__} crashed")
            traceback.print_exc()
    print("\n" + "=" * 60)
    print(f" RESULT: {rep.pass_count} passed, {rep.fail_count} failed, "
          f"{len(rep.warnings)} warnings")
    print("=" * 60)
    if rep.fail_count == 0:
        print("ALL SYSTEMS GO. Launch the game with:  python main.py")
    return rep.fail_count == 0

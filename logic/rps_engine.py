"""Rock / Paper / Scissors rules and match scoring."""
from __future__ import annotations

from config import BEATS, GESTURES, TARGET_WINS


def beats(a: str, b: str) -> str | None:
    """Return 'a' if a beats b, 'b' if b beats a, None on a draw."""
    if a not in GESTURES or b not in GESTURES:
        return None
    if a == b:
        return None
    return a if BEATS[a] == b else b


def counter_for(gesture: str) -> str:
    """The gesture that defeats ``gesture``."""
    for g in GESTURES:
        if BEATS[g] == gesture:
            return g
    return "rock"


def round_result(player: str, opponent: str) -> int:
    """1 = player wins round, 2 = opponent wins, 0 = draw."""
    w = beats(player, opponent)
    if w is None:
        return 0
    return 1 if w == player else 2


class Match:
    """First to ``target`` wins -- the UI calls it best of 3 / first to 3."""

    def __init__(self, target: int = TARGET_WINS):
        self.target = target
        self.scores = [0, 0]
        self.rounds = []
        self.over = False
        self.match_winner = 0  # 1 player, 2 opponent

    def reset(self):
        self.scores = [0, 0]
        self.rounds = []
        self.over = False
        self.match_winner = 0

    def add_round(self, player: str, opponent: str) -> dict:
        result = round_result(player, opponent)
        if result == 1:
            self.scores[0] += 1
        elif result == 2:
            self.scores[1] += 1
        self.rounds.append({
            "round": len(self.rounds) + 1,
            "player": player,
            "opponent": opponent,
            "winner": result,
        })
        if self.scores[0] >= self.target or self.scores[1] >= self.target:
            self.over = True
            self.match_winner = 1 if self.scores[0] >= self.target else 2
        return {
            "result": result,
            "scores": tuple(self.scores),
            "over": self.over,
            "match_winner": self.match_winner,
            "round": len(self.rounds),
        }


class MatchState:
    """Lightweight helper used by the network layer to sync scores."""

    def __init__(self):
        self.player_score = 0
        self.opponent_score = 0
        self.round = 1

    def apply(self, player_score, opponent_score, round_no=None):
        self.player_score = int(player_score)
        self.opponent_score = int(opponent_score)
        if round_no is not None:
            self.round = int(round_no)

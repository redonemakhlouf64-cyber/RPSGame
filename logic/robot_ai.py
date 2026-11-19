"""Four robot brains, from harmless to terrifyingly good."""
from __future__ import annotations

import random
from collections import defaultdict

from config import BEATS, GESTURES
from logic.rps_engine import counter_for

LEVELS = ("beginner", "medium", "strong", "very_strong")


class RobotAI:
    def __init__(self, level: str = "beginner", seed=None):
        self.level = level if level in LEVELS else "beginner"
        self.rng = random.Random(seed)
        self.player_history: list[str] = []
        self.ai_moves: list[str] = []
        self._freq = defaultdict(float)

    # ------------------------------------------------------------------ API
    def next_move(self, player_history: list[str] | None = None) -> str:
        hist = list(player_history if player_history is not None else self.player_history)
        if self.level == "beginner" or not hist:
            return self.rng.choice(GESTURES)
        if self.level == "medium":
            return self._medium(hist)
        if self.level == "strong":
            return self._strong(hist)
        return self._very_strong(hist)

    def update(self, player_move: str, ai_move: str):
        self.player_history.append(player_move)
        self.ai_moves.append(ai_move)
        self.player_history = self.player_history[-120:]
        self.ai_moves = self.ai_moves[-120:]

    # -------------------------------------------------------------- brains
    def _medium(self, hist):
        last = hist[-1]
        if self.rng.random() < 0.68:
            return counter_for(last)
        return self.rng.choice(GESTURES)

    def _strong(self, hist):
        n = len(hist)
        votes = {g: 0.0 for g in GESTURES}
        # Pattern lengths 3 -> 1, longer context weighted heavier.
        for order, weight in ((3, 1.8), (2, 1.1), (1, 0.55)):
            if n < order:
                continue
            ctx = tuple(hist[-order:])
            local = {g: 0.0 for g in GESTURES}
            total = 0.0
            for i in range(order, n):
                if tuple(hist[i - order:i]) == ctx:
                    recency = 0.9 ** (n - i)
                    local[hist[i]] += recency
                    total += recency
            if total > 0:
                for g in GESTURES:
                    votes[g] += weight * (local[g] / total)
        # Global preference, recency weighted.
        for i, m in enumerate(hist[-24:]):
            votes[m] += 0.06 * (0.92 ** (min(24, n) - 1 - i))
        predicted = max(GESTURES, key=lambda g: votes[g])
        if self.rng.random() < 0.84:
            return counter_for(predicted)
        return self.rng.choice([g for g in GESTURES if g != counter_for(predicted)])

    def _distribution(self, hist):
        """Estimate the player's next-move distribution."""
        n = len(hist)
        probs = {g: 0.035 for g in GESTURES}

        # 1) recency weighted global frequency
        window = hist[-48:]
        total_w = 0.0
        for i, m in enumerate(window):
            w = 0.935 ** (len(window) - 1 - i)
            probs[m] += 0.42 * w
            total_w += w
        if total_w:
            for g in GESTURES:
                probs[g] += 0.0

        # 2) suffix n-gram models, longer contexts are more informative
        for order, weight in ((1, 0.45), (2, 0.8), (3, 1.25), (4, 1.7), (5, 2.1)):
            if n < order:
                continue
            ctx = tuple(hist[-order:])
            local = {g: 0.0 for g in GESTURES}
            total = 0.0
            for i in range(order, n):
                if tuple(hist[i - order:i]) == ctx:
                    recency = 0.88 ** (n - i)
                    local[hist[i]] += recency
                    total += recency
            if total > 0:
                for g in GESTURES:
                    probs[g] += weight * (local[g] / total)

        # 3) conditional response to our previous move (exploits loops)
        if self.ai_moves and n >= 2:
            last_ai = self.ai_moves[-1]
            local = {g: 0.0 for g in GESTURES}
            total = 0.0
            for i in range(1, min(len(hist), len(self.ai_moves) + 1)):
                if self.ai_moves[i - 1] == last_ai:
                    recency = 0.85 ** (n - i)
                    local[hist[i]] += recency
                    total += recency
            if total > 0:
                for g in GESTURES:
                    probs[g] += 0.9 * (local[g] / total)

        # 4) humans rarely play the same gesture a third time
        if n >= 2 and hist[-1] == hist[-2]:
            probs[hist[-1]] *= 0.30
        # 5) mild anti-meta: if the player always counters our last move
        if self.ai_moves:
            last_ai = self.ai_moves[-1]
            anti = 0
            hits = 0
            for i, mv in enumerate(hist):
                if i > 0 and i - 1 < len(self.ai_moves) and self.ai_moves[i - 1] == last_ai:
                    hits += 1
                    if BEATS[mv] == self.ai_moves[i - 1]:
                        anti += 1
            if hits >= 3 and anti / hits > 0.55:
                probs[counter_for(last_ai)] += 0.7

        # normalize
        s = sum(probs.values()) or 1.0
        return {g: probs[g] / s for g in GESTURES}

    def _very_strong(self, hist):
        n = len(hist)
        if n < 2:
            return self.rng.choice(GESTURES)
        probs = self._distribution(hist)
        # Expected value of each candidate against the estimated distribution.
        utility = {}
        for move in GESTURES:
            win_p = probs[BEATS[move]]     # they play what we beat
            loss_p = probs[counter_for(move)]  # they play what beats us
            draw_p = probs[move]
            utility[move] = win_p - loss_p + 0.03 * draw_p
        best = max(utility.values())
        top = [m for m in GESTURES if utility[m] >= best - 1e-9]
        # Break ties with the most likely counter, then a dash of chaos.
        if self.rng.random() < 0.04:
            return self.rng.choice(GESTURES)
        if self.rng.random() < 0.72:
            predicted = max(GESTURES, key=lambda g: probs[g])
            countered = counter_for(predicted)
            if countered in top:
                return countered
        return self.rng.choice(top)

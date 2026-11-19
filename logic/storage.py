"""Crash-proof JSON persistence for settings and match history."""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, List

from config import HISTORY_FILE, SETTINGS_FILE

_LOCK = threading.RLock()

DEFAULT_SETTINGS: Dict[str, Any] = {
    "lang": "en",
    "character": "amara",
    "difficulty": "medium",
    "sound": True,
    "first_run": True,
}


def _read_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return fallback


def _write_json(path, data):
    try:
        tmp = str(path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


class Store:
    def __init__(self):
        self._settings = dict(DEFAULT_SETTINGS)
        self._settings.update(_read_json(SETTINGS_FILE, {}))
        history = _read_json(HISTORY_FILE, [])
        self._history: List[dict] = history if isinstance(history, list) else []

    # ------------------------------------------------------------- settings
    @property
    def settings(self) -> dict:
        return dict(self._settings)

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def set(self, key, value):
        with _LOCK:
            self._settings[key] = value
            _write_json(SETTINGS_FILE, self._settings)
        return value

    def set_many(self, values: dict):
        with _LOCK:
            self._settings.update(values)
            _write_json(SETTINGS_FILE, self._settings)

    # -------------------------------------------------------------- history
    @property
    def history(self) -> list:
        with _LOCK:
            return list(self._history)

    def add_match(self, *, mode, difficulty, player_char, opponent_char,
                  player_score, opponent_score, player_won, lang):
        entry = {
            "ts": int(time.time()),
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "mode": mode,
            "difficulty": difficulty,
            "player": player_char,
            "opponent": opponent_char,
            "score": f"{player_score}-{opponent_score}",
            "result": "win" if player_won else "loss",
            "lang": lang,
        }
        with _LOCK:
            self._history.append(entry)
            self._history = self._history[-200:]
            _write_json(HISTORY_FILE, self._history)
        return entry

    def stats(self) -> dict:
        with _LOCK:
            hist = list(self._history)
        wins = sum(1 for e in hist if e.get("result") == "win")
        return {"matches": len(hist), "wins": wins, "losses": len(hist) - wins}


STORE = Store()

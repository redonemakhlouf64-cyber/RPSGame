"""Central configuration for RPS Arena 3D."""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "RPS Arena 3D"
APP_VERSION = "1.0.0"
TARGET_WINS = 3
TARGET_WINS_LABEL = 3

GESTURES = ("rock", "paper", "scissors")
BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
LOSES_TO = {v: k for k, v in BEATS.items()}

# ----------------------------------------------------------------------------
# Storage -- everything the player owns lives in the shared Downloads folder.
# If shared storage is not accessible (permission not granted yet) we silently
# fall back to a private app folder so the game never crashes on first run.
# ----------------------------------------------------------------------------
_HOME = Path(os.path.expanduser("~"))
_SHARED = _HOME / "storage" / "downloads" / "RPSGame"
_PRIVATE = _HOME / ".rps_arena"


def _pick_base() -> Path:
    for candidate in (_SHARED, _PRIVATE):
        try:
            (candidate / "assets").mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return candidate
        except Exception:
            continue
    # last resort: next to the code
    base = Path(__file__).resolve().parent / "userdata"
    (base / "assets").mkdir(parents=True, exist_ok=True)
    return base


BASE_DIR = _pick_base()
ASSETS_DIR = BASE_DIR / "assets"
SOUND_DIR = ASSETS_DIR / "sounds"
SETTINGS_FILE = BASE_DIR / "settings.json"
HISTORY_FILE = BASE_DIR / "history.json"
for _d in (BASE_DIR, ASSETS_DIR, SOUND_DIR):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

# ----------------------------------------------------------------------------
# Networking
# ----------------------------------------------------------------------------
TCP_PORT = 37221
DISCOVERY_PORT = 37220
DISCOVERY_MAGIC = "RPSARENA3D"
BT_SERVICE_NAME = "RPSArena3D"
BT_SERVICE_UUID = "7d8ea8b2-3f3c-4f37-9a5e-52d5d1b7c001"

# ----------------------------------------------------------------------------
# Resolution / look
# ----------------------------------------------------------------------------
DESIGN_W = 432
DESIGN_H = 768

# ----------------------------------------------------------------------------
# Characters -- 3 girls, 3 boys, three ethnicities, unique hair + screams.
# ----------------------------------------------------------------------------
CHARACTERS = [
    {
        "id": "amara",
        "name": "Amara",
        "gender": "girl",
        "ethnicity": "Black",
        "skin": "#6E4228",
        "skin_dark": "#4B2A18",
        "skin_light": "#8C5838",
        "hair": "#171116",
        "hair_hi": "#3A2A34",
        "style": "afro",
        "outfit": "#8E5BFF",
        "outfit_dark": "#5B34B8",
        "accent": "#D8C2FF",
        "scream": 515,
        "tag": "Afro queen",
        "eyes": "#3A2318",
    },
    {
        "id": "kenji",
        "name": "Kenji",
        "gender": "boy",
        "ethnicity": "Asian",
        "skin": "#EFC39A",
        "skin_dark": "#C89468",
        "skin_light": "#FFDCB8",
        "hair": "#101018",
        "hair_hi": "#2A2A40",
        "style": "spiky",
        "outfit": "#2E86DE",
        "outfit_dark": "#16548F",
        "accent": "#9DDCFF",
        "scream": 640,
        "tag": "Street ninja",
        "eyes": "#20140E",
    },
    {
        "id": "sofia",
        "name": "Sofia",
        "gender": "girl",
        "ethnicity": "White",
        "skin": "#F7D5BF",
        "skin_dark": "#D8A98D",
        "skin_light": "#FFE9DA",
        "hair": "#E7BE55",
        "hair_hi": "#FFE49A",
        "style": "ponytail",
        "outfit": "#FF5C9E",
        "outfit_dark": "#B72E67",
        "accent": "#FFC8DF",
        "scream": 720,
        "tag": "Pop princess",
        "eyes": "#3B6E8F",
    },
    {
        "id": "malik",
        "name": "Malik",
        "gender": "boy",
        "ethnicity": "Black",
        "skin": "#7C4B2C",
        "skin_dark": "#58301A",
        "skin_light": "#9B6440",
        "hair": "#14100D",
        "hair_hi": "#33261C",
        "style": "fade",
        "outfit": "#E74C3C",
        "outfit_dark": "#9E2B20",
        "accent": "#FFB4A6",
        "scream": 425,
        "tag": "Drum machine",
        "eyes": "#2A170E",
    },
    {
        "id": "mei",
        "name": "Mei",
        "gender": "girl",
        "ethnicity": "Asian",
        "skin": "#F6D4B4",
        "skin_dark": "#D3A47F",
        "skin_light": "#FFE7D0",
        "hair": "#191722",
        "hair_hi": "#3B3550",
        "style": "buns",
        "outfit": "#12CBC4",
        "outfit_dark": "#0A8F89",
        "accent": "#94F8F3",
        "scream": 780,
        "tag": "Neon gamer",
        "eyes": "#241A1A",
    },
    {
        "id": "lucas",
        "name": "Lucas",
        "gender": "boy",
        "ethnicity": "White",
        "skin": "#F2C8A4",
        "skin_dark": "#CFA078",
        "skin_light": "#FFE2C8",
        "hair": "#C75B24",
        "hair_hi": "#F08B4D",
        "style": "curly",
        "outfit": "#27AE60",
        "outfit_dark": "#166B3A",
        "accent": "#A8F0C1",
        "scream": 470,
        "tag": "Freckle storm",
        "eyes": "#356B3A",
        "freckles": True,
    },
]

CHARACTERS_BY_ID = {c["id"]: c for c in CHARACTERS}

DIFFICULTIES = ("beginner", "medium", "strong", "very_strong")

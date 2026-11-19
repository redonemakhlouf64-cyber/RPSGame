# RPS Arena 3D

A portrait-mode rock–paper–scissors arena for Android/Termux with pseudo-3D
hands, six animated characters, four robot brains, local multiplayer, and
16 UI languages (including Cat).

## Run the game (Termux)

Kivy needs an X server on Termux. Install the **Termux:X11** app, then:

```bash
# in Termux
termux-x11 :0 &
DISPLAY=:0 python ~/RPSGame/main.py
```

If you already run an X server (Xvfb, VNC, etc.), just point `DISPLAY` at it.

## Logic self-test (no display or audio needed)

```bash
cd ~/RPSGame
python main.py --headless-test
```

Expected result: `35 passed, 0 failed, 0 warnings`.

## Controls

- Tap cards/buttons to choose a character, language, mode and difficulty.
- During a round tap **Rock**, **Paper**, or **Scissors**.
- First to 3 round wins takes the match.
- The winner automatically slaps the loser three times.
- Result screen: **Play Again** or **Home**.

## Modes

- **VS Robot** — Beginner, Medium, Strong, Very Strong (Markov + frequency AI).
- **VS Friend** — Bluetooth RFCOMM when available, otherwise TCP over the
  same Wi-Fi/hotspot. Both are shown as “Bluetooth / Wi-Fi duel”.

## Saved data

`~/storage/downloads/RPSGame/` contains:

- `settings.json` — language, character, difficulty, sound.
- `history.json` — match history and win/loss counts.
- `assets/sounds/` — generated WAV effects and per-character screams.

If shared storage is unavailable, the game silently uses `~/.rps_arena`.

## Build an APK

```bash
~/build_apk.sh
```

The script prepares the Termux toolchain and writes
`~/storage/downloads/RPSGame.apk` on success. Building Python-for-Android
natively on aarch64 Termux requires the local SDK/NDK shims that the script
sets up; the standard, most reliable route is still an x86_64 Linux host
(or WSL / GitHub Actions) with Buildozer.

### GitHub Actions (recommended)

This repository includes `.github/workflows/build.yml`. Every push to `main`
builds the APK on Ubuntu and uploads it as the `RPSGame-apk` artifact.

```bash
gh workflow run build.yml
gh run watch
gh run download <run-id> -n RPSGame-apk -D ~/storage/downloads/
```

## Project layout

```
RPSGame/
├── main.py
├── config.py
├── logic/      rps_engine, robot_ai, network, audio, assets_gen, i18n, storage
├── ui/         theme, widgets, avatars, hand_3d
└── screens/    splash, language, character, mode, difficulty, lobby,
                gameplay, result
```
